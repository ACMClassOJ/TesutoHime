__all__ = 'generate_plan',

from copy import deepcopy
import json
from logging import getLogger
from os import remove
from typing import List, Literal, Optional, Set, Tuple
from zipfile import ZipFile

from scheduler2.config import default_check_limits, default_compile_limits, default_run_limits, s3_buckets, working_dir, problem_config_filename, s3_hosts
from commons.task_typing import Artifact, CompareChecker, CompileSourceCpp, CompileTaskPlan, DirectChecker, JudgePlan, JudgeTask, JudgeTaskPlan, ResourceUsage, RunArgs, SpjChecker, Testpoint, TestpointGroup, Url, UserCode
from commons.util import asyncrun
from scheduler2.problem_typing import Spj, Group, ProblemConfig, Testpoint as ConfigTestpoint
from scheduler2.s3 import construct_url, download, upload_obj

logger = getLogger(__name__)


class InvalidProblemException (Exception): pass


class PlanContext:
    problem_id: str
    zip: ZipFile
    cfg: ProblemConfig
    testpoint_count: int
    compile_type: Literal['classic', 'hpp', 'hpp-per-testpoint', 'none']
    check_type: Literal['classic', 'direct', 'checker']
    files_to_upload: Set[str]
    plan: JudgePlan

    def __init__ (self, problem_id, zip):
        self.problem_id = problem_id
        self.zip = zip
        self.testpoint_count = None
        self.cfg = None
        self.compile_type = None
        self.check_type = None
        self.files_to_upload = set()
        self.plan = JudgePlan()

    def cons_key (self, filename):
        return f'{self.problem_id}/{filename}'

    def cons_url (self, filename):
        self.files_to_upload.add(filename)
        key = self.cons_key(filename)
        return construct_url(s3_hosts.internal, s3_buckets.problems, key)


async def load_config (ctx: PlanContext):
    try:
        with ctx.zip.open(problem_config_filename, 'r') as f:
            cfg = json.load(f)
    except BaseException as e:
        msg = f'cannot read {problem_config_filename}: {e}'
        raise InvalidProblemException(msg)
    try:
        cfg['Groups'] = [Group(**x) for x in cfg['Group']]
        cfg['Details'] = [ConfigTestpoint(**x) for x in cfg['Details']]
        ctx.cfg = ProblemConfig(**cfg)
        ctx.testpoint_count = len(ctx.cfg.Details)
    except BaseException as e:
        raise InvalidProblemException(str(e))


async def parse_spj (ctx: PlanContext):
    spj = ctx.cfg.SPJ
    type_map = {
        Spj.CLASSIC_CLASSIC: ('classic', 'classic'),
        Spj.CLASSIC_CHECKER: ('classic', 'checker'),
        Spj.HPP_DIRECT: ('hpp', 'direct'),
        Spj.HPP_CLASSIC: ('hpp', 'classic'),
        Spj.HPP_CHECKER: ('hpp', 'checker'),
        Spj.NONE_CHECKER: ('none', 'checker'),
    }
    if not spj in type_map:
        raise InvalidProblemException(f'Invalid SPJ type {spj}')
    ctx.compile_type, ctx.check_type = type_map[spj]
    if ctx.cfg.Scorer != 0:
        raise InvalidProblemException(f'Scorers are not supported (yet)')


hpp_main_filename = 'main.cpp'
hpp_main_template = '%d.cpp'
hpp_src_filename = 'src.hpp'

async def parse_compile (ctx: PlanContext) -> Optional[CompileTaskPlan]:
    if ctx.compile_type == 'none':
        return None

    supplementary_files = ctx.cfg.SupportedFiles

    limits = deepcopy(default_compile_limits)
    time_msecs = ctx.cfg.CompileTimeLimit
    if time_msecs is not None:
        limits.time_msecs = time_msecs

    task = CompileTaskPlan(
        source=UserCode(),
        supplementary_files=[ctx.cons_url(x) for x in supplementary_files],
        artifact=True,
        limits=limits,
    )
    if ctx.compile_type == 'classic':
        return task
    task.supplementary_files.append(UserCode(hpp_src_filename))

    has_main = hpp_main_filename in ctx.zip.namelist()
    if has_main:
        task.source = CompileSourceCpp(ctx.cons_url(hpp_main_filename))
        return task
    ctx.compile_type = 'hpp-per-testpoint'
    task.source = None
    return task


async def generate_dependents (plan: List[JudgeTaskPlan]) -> List[JudgeTaskPlan]:
    for i, deps in enumerate(map(lambda x: x.dependencies, plan)):
        for dep in deps:
            plan[dep].dependents.append(i)
    return plan

infile_name_template = '%d.in'
answer_name_template = '%d.ans'
answer_name_template_alt = '%d.out'

async def parse_testpoints (ctx: PlanContext) -> List[JudgeTaskPlan]:
    def parse_testpoint (conf: ConfigTestpoint) -> Testpoint:
        id = str(conf.ID)
        infile_name = infile_name_template % id
        infile = Artifact(ctx.cons_url(infile_name))

        run_limits = deepcopy(default_run_limits)
        if conf.TimeLimit is not None: run_limits.time_msecs = conf.TimeLimit
        if conf.MemoryLimit is not None: run_limits.memory_bytes = conf.MemoryLimit
        if conf.DiskLimit is not None: run_limits.file_size_bytes = abs(conf.DiskLimit)
        if conf.FileNumberLimit is not None: run_limits.file_count = conf.FileNumberLimit

        type = 'verilog' if ctx.cfg.Verilog else \
            'valgrind' if conf.ValgrindTestOn else 'elf'
        run = None if ctx.check_type == 'direct' else RunArgs(
            type=type,
            limits=run_limits,
            infile=infile,
            supplementary_files=[],
        )

        def ans () -> Optional[Url]:
            ans_filename = answer_name_template % id
            if ans_filename in ctx.zip.namelist():
                return ctx.cons_url(ans_filename)
            ans_filename_alt = answer_name_template_alt % id
            if ans_filename_alt in ctx.zip.namelist():
                return ctx.cons_url(ans_filename_alt)
            return None
        if ctx.check_type == 'compare':
            check = CompareChecker(True, ans())
            if check.answer is None:
                raise InvalidProblemException(f'Answer file needed')
        elif ctx.check_type == 'direct':
            check = DirectChecker()
        elif ctx.check_type == 'spj':
            check = SpjChecker('checker', None, ans(), [], default_check_limits)

        testpoint = Testpoint(
            id=id,
            dependent_on=None if conf.Dependency == 0 else str(conf.Dependency),
            input=UserCode(), 
            run=run, 
            check=check,
        )
        if ctx.compile_type == 'hpp-per-testpoint':
            source = CompileSourceCpp(ctx.cons_url(hpp_main_template % id))
            task = deepcopy(ctx.plan.compile)
            task.source = source
            testpoint.input = task
        return testpoint

    testpoints = list(map(parse_testpoint, ctx.cfg.Details))
    testpoints_map = dict(map(lambda tp: (tp.id, tp), testpoints))
    if ctx.compile_type == 'hpp-per-testpoint':
        ctx.plan.compile = None

    if any(x.DiskLimit is not None and x.DiskLimit > 0 for x in ctx.cfg.Details):
        plan: List[JudgeTaskPlan] = []
        for testpoint, conf in zip(testpoints, ctx.cfg.Details):
            if len(plan) == 0 or conf.DiskLimit < 0:
                plan.append(JudgeTaskPlan(
                    task=JudgeTask([]),
                    dependencies=[],
                    dependents=[],
                ))
            current_task = plan[-1]
            current_task.task.testpoints.append(testpoint)
            if testpoint.dependent_on is not None:
                msg = f'Invalid dep {conf.Dependency} declared by {conf.ID}'
                if not testpoint.dependent_on in testpoints_map:
                    raise InvalidProblemException(msg)
                dep = testpoints_map[testpoint.dependent_on]
                if all(x is not dep for x in current_task.task.testpoints):
                    for i, group in enumerate(plan):
                        if any(x is dep for x in group.task.testpoints):
                            current_task.dependencies.append(i)
                            break
                    else:
                        raise InvalidProblemException(msg)
        return generate_dependents(plan)

    plan = []
    for testpoint, conf in zip(testpoints, ctx.cfg.Details):
        if testpoint.dependent_on is not None:
            if not testpoint.dependent_on in testpoints_map:
                msg = f'Invalid dep {conf.Dependency} declared by {conf.ID}'
                raise InvalidProblemException(msg)
            dep = testpoints.index(testpoints_map[testpoint.dependent_on])
            dep = [dep]
        else:
            dep = []
        plan.append(JudgeTaskPlan(
            task=JudgeTask([testpoint]),
            dependencies=dep,
            dependents=[],
        ))
    return generate_dependents(plan)


group_name_template = 'Task %d'

async def parse_groups (ctx: PlanContext) -> List[TestpointGroup]:
    return [TestpointGroup(
        name=conf.GroupName if conf.GroupName is not None \
            else group_name_template % (i + 1),
        testpoints=[str(x) for x in conf.TestPoints],
        score=float(conf.GroupScore),
    ) for i, conf in enumerate(ctx.cfg.Groups)]


async def upload_files (ctx: PlanContext):
    for file in ctx.files_to_upload:
        with ctx.zip.open(file, 'rb') as f:
            await upload_obj(s3_buckets.problems, ctx.cons_key(file), f)


async def compile_spj (ctx: PlanContext):
    raise NotImplementedError()


async def generate_plan (problem_id: str) -> JudgePlan:
    zip_filename = f'{problem_id}.zip'
    zip_path = working_dir / zip_filename
    try:
        await download(s3_buckets.problems, zip_filename, zip_path)
        with ZipFile(zip_path) as zip:
            ctx = PlanContext(problem_id, zip)
            await load_config(ctx)
            await parse_spj(ctx)
            ctx.plan.compile = await parse_compile(ctx)
            ctx.plan.judge = await parse_testpoints(ctx)
            ctx.plan.score = await parse_groups(ctx)
            await upload_files(ctx)
            await compile_spj(ctx)
            return ctx.plan
    finally:
        try:
            remove(zip_path)
        except BaseException as e:
            logger.error(f'cannot remove problem zip: {e}')
