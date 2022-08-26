__all__ = 'generate_plan', 'execute_plan'

import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum, auto
from logging import getLogger
from os import remove
from typing import List, Literal, Optional, Set
from zipfile import ZipFile

from commons.task_typing import (Artifact, CodeLanguage, CompareChecker,
                                 CompileSource, CompileSourceCpp,
                                 CompileSourceGit, CompileSourceVerilog,
                                 CompileTask, CompileTaskPlan, DirectChecker,
                                 FileUrl, JudgePlan, JudgeTask, JudgeTaskPlan,
                                 RunArgs, SpjChecker, Testpoint,
                                 TestpointGroup, UserCode)

from scheduler2.config import (default_check_limits, default_compile_limits,
                               default_run_limits, problem_config_filename,
                               s3_buckets, working_dir)
from scheduler2.problem_typing import Group, ProblemConfig, Spj
from scheduler2.problem_typing import Testpoint as ConfigTestpoint
from scheduler2.s3 import download, sign_url_get, upload_obj

logger = getLogger(__name__)


class InvalidProblemException (Exception): pass


class ParseContext:
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
        return f's3://{key}'


async def load_config (ctx: ParseContext):
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


async def parse_spj (ctx: ParseContext):
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
hpp_main_template_vlog = '%d.v'
hpp_src_filename = 'src.hpp'
hpp_src_filename_vlog = 'answer.v'

async def parse_compile (ctx: ParseContext) -> Optional[CompileTaskPlan]:
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
    src_filename = hpp_src_filename_vlog if ctx.cfg.Verilog \
        else hpp_src_filename
    task.supplementary_files.append(UserCode(src_filename))

    has_main = hpp_main_filename in ctx.zip.namelist()
    if has_main:
        task.source = CompileSourceCpp(ctx.cons_url(hpp_main_filename))
        return task
    ctx.compile_type = 'hpp-per-testpoint'
    task.source = None
    task.artifact = False
    return task


async def generate_dependents (plan: List[JudgeTaskPlan]) -> List[JudgeTaskPlan]:
    for i, deps in enumerate(map(lambda x: x.dependencies, plan)):
        for dep in deps:
            plan[dep].dependents.append(i)
    return plan

infile_name_template = '%d.in'
answer_name_template = '%d.ans'
answer_name_template_alt = '%d.out'

async def parse_testpoints (ctx: ParseContext) -> List[JudgeTaskPlan]:
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

        def ans () -> Optional[FileUrl]:
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
            main_template = hpp_main_template_vlog if ctx.cfg.Verilog \
                else hpp_main_template
            task = deepcopy(ctx.plan.compile)
            task.source = CompileSourceCpp(ctx.cons_url(main_template % id))
            testpoint.input = task
        return testpoint

    testpoints = list(map(parse_testpoint, ctx.cfg.Details))
    testpoints_map = dict(map(lambda tp: (tp.id, tp), testpoints))
    if ctx.compile_type == 'hpp-per-testpoint':
        ctx.plan.compile = None

    if any(x.DiskLimit is not None and x.DiskLimit > 0 for x in ctx.cfg.Details):
        if ctx.compile_type == 'hpp-per-testpoint':
            msg = 'Per-testpoint compilation is incompatible with persistence testing'
            raise InvalidProblemException(msg)
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

async def parse_groups (ctx: ParseContext) -> List[TestpointGroup]:
    return [TestpointGroup(
        name=conf.GroupName if conf.GroupName is not None \
            else group_name_template % (i + 1),
        testpoints=[str(x) for x in conf.TestPoints],
        score=float(conf.GroupScore),
    ) for i, conf in enumerate(ctx.cfg.Groups)]


async def upload_files (ctx: ParseContext):
    for file in ctx.files_to_upload:
        with ctx.zip.open(file, 'rb') as f:
            await upload_obj(s3_buckets.problems, ctx.cons_key(file), f)


async def compile_spj (ctx: ParseContext):
    raise NotImplementedError()


async def generate_plan (problem_id: str) -> JudgePlan:
    zip_filename = f'{problem_id}.zip'
    zip_path = working_dir / zip_filename
    try:
        await download(s3_buckets.problems, zip_filename, zip_path)
        with ZipFile(zip_path) as zip:
            ctx = ParseContext(problem_id, zip)
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


class InvalidCodeException (Exception): pass


class UrlType (Enum):
    CODE = auto()
    ARTIFACT = auto()

@dataclass
class JudgeTaskRecord:
    task: JudgeTask
    plan: JudgeTaskPlan

@dataclass
class ExecutionContext:
    plan: JudgePlan
    lang: CodeLanguage
    code: str
    compile: Optional[CompileTask] = None
    judge: Optional[List[JudgeTaskRecord]] = None
    compile_artifact: Optional[Artifact] = None

    def cons_url (self, type: UrlType, filename: str):
        raise NotImplementedError()


def sign_url (url: str):
    scheme = 's3://'
    if not url.startswith(scheme):
        raise InvalidProblemException(f'Invalid object url {url}')
    return sign_url_get(s3_buckets.problems, url.replace(scheme, '', 1), {})


raw_code_filename = 'code'
cpp_main_filename = 'main.cpp'
verilog_main_filename = 'main.v'
artifact_filename = 'main'

def get_compile_source (ctx: ExecutionContext, filename: str) -> CompileSource:
    if ctx.lang == CodeLanguage.CPP:
        return CompileSourceCpp(ctx.cons_url(UrlType.CODE, filename))
    if ctx.lang == CodeLanguage.GIT:
        return CompileSourceGit(ctx.code.strip())
    if ctx.lang == CodeLanguage.VERILOG:
        return CompileSourceVerilog(ctx.cons_url(UrlType.CODE, filename))
    raise InvalidCodeException('Unknown language')

def prepare_compile_task (ctx: ExecutionContext, plan: CompileTaskPlan) \
    -> CompileTask:
    if not plan:
        return

    user_codes = list(filter(lambda x: isinstance(x, UserCode), 
        [plan.source] + plan.supplementary_files))
    if len(user_codes) == 0:
        raise InvalidProblemException('Compile task with no user input')
    if len(user_codes) > 1:
        raise InvalidCodeException('Compile task with multiple files as user input')

    fallback_filename = cpp_main_filename if ctx.lang == CodeLanguage.CPP \
        else verilog_main_filename if ctx.lang == CodeLanguage.VERILOG \
        else None
    filename = user_codes[0].filename
    if filename is None: filename = fallback_filename
    if isinstance(plan.source, UserCode):
        source = get_compile_source(ctx, filename)
    else:
        source = deepcopy(plan.source)
        if source.type == 'cpp' or source.type == 'verilog':
            source.main = sign_url(source.main)
    def map_supplementary_file (file):
        if isinstance(file, UserCode):
            return ctx.cons_url(UrlType.CODE, filename)
        else:
            return sign_url(file)
    supplementary_files = [map_supplementary_file(x) for x in
        plan.supplementary_files]

    artifact = Artifact(ctx.cons_url(UrlType.ARTIFACT, artifact_filename)) \
        if plan.artifact else None
    limits = deepcopy(plan.limits)
    ctx.compile = CompileTask(source, supplementary_files, artifact, limits)


def get_judge_task (ctx: ExecutionContext, plan: JudgeTaskPlan) \
    -> JudgeTaskRecord:
    task = deepcopy(plan.task)
    for testpoint in task.testpoints:
        if testpoint.dependent_on is not None:
            if all(x.id != testpoint.dependent_on for x in task.testpoints):
                testpoint.dependent_on = None

        match testpoint.input:
            case UserCode():
                if ctx.compile_artifact is None:
                    ctx.compile_artifact = Artifact(ctx.cons_url(UrlType.CODE,
                        raw_code_filename))
                testpoint.input = ctx.compile_artifact
            case CompileTaskPlan():
                testpoint.input = prepare_compile_task(ctx, testpoint.input)
            case CompileTask():
                pass
            case Artifact():
                testpoint.input.url = sign_url(testpoint.input.url)

        if testpoint.run is not None:
            if testpoint.run.infile is not None:
                testpoint.run.infile = sign_url(testpoint.run.infile)
            testpoint.run.supplementary_files = \
                [sign_url(x) for x in testpoint.run.supplementary_files]

        match testpoint.check:
            case CompareChecker():
                testpoint.check.answer = sign_url(testpoint.check.answer)
            case DirectChecker():
                pass
            case SpjChecker():
                if testpoint.check.answer is not None:
                    testpoint.check.answer = sign_url(testpoint.check.answer)
                if not isinstance(testpoint.check.executable, Artifact):
                    raise InvalidProblemException('Invalid SPJ')
                testpoint.check.executable.url = \
                    sign_url(testpoint.check.executable.url)
                testpoint.check.supplementary_files = \
                    [sign_url(x) for x in testpoint.check.supplementary_files]

    return JudgeTaskRecord(task, plan)

def get_judge_tasks (ctx: ExecutionContext) -> List[JudgeTaskRecord]:
    return [get_judge_task(ctx, plan) for plan in ctx.plan.judge]


async def run_judge_tasks (ctx: ExecutionContext):
    raise NotImplementedError()


async def execute_plan (plan: JudgePlan, lang: CodeLanguage, code: str):
    ctx = ExecutionContext(plan, lang, code)
    ctx.compile = prepare_compile_task(ctx.plan.compile)
    ctx.judge = get_judge_tasks(ctx)
    await run_judge_tasks(ctx)
    # TODO: report back
