__all__ = 'generate_plan', 'execute_plan', 'get_partial_result'

import json
from copy import deepcopy
from dataclasses import dataclass, field
from logging import getLogger
from os import remove
from typing import List, Optional, Set
from zipfile import ZipFile

from commons.task_typing import (Artifact, CompareChecker, CompileSourceCpp,
                                 CompileSourceVerilog, CompileTask,
                                 CompileTaskPlan, DirectChecker, FileUrl,
                                 JudgePlan, JudgeTask, JudgeTaskPlan,
                                 QuizOption, QuizProblem, ResourceUsage,
                                 RunArgs, SpjChecker, Testpoint,
                                 TestpointGroup, UserCode)
from commons.util import Literal, format_exc
from scheduler2.config import (default_check_limits, default_compile_limits,
                               default_run_limits, problem_config_filename,
                               quiz_filename, s3_buckets, working_dir)
from scheduler2.dispatch import TaskInfo, run_task
from scheduler2.plan.util import InvalidProblemException, sign_url, url_scheme
from scheduler2.problem_typing import Group, ProblemConfig, Spj
from scheduler2.problem_typing import Testpoint as ConfigTestpoint
from scheduler2.s3 import download, sign_url_put, upload_obj

logger = getLogger(__name__)


@dataclass
class ParseContext:
    problem_id: str
    zip: ZipFile
    cfg: Optional[ProblemConfig] = None

    quiz_problems: Optional[List[QuizProblem]] = None
    testpoint_count: Optional[int] = None
    compile_type: Literal['classic', 'hpp', 'hpp-per-testpoint', 'none'] = None
    check_type: Literal['compare', 'direct', 'spj'] = None
    compile_limits: Optional[ResourceUsage] = None
    compile_supp: Optional[List[str]] = None
    files_to_upload: Set[str] = field(default_factory=lambda: set())
    checker_to_compile: Optional[str] = None
    checker_artifact: Optional[Artifact] = None
    plan: JudgePlan = field(default_factory=lambda: JudgePlan())

    def file_key(self, filename: str):
        return f'{self.problem_id}/{filename}'

    # file URLs inside judge plans has a format of s3://key .
    def file_url(self, filename: str) -> FileUrl:
        self.files_to_upload.add(filename)
        return f'{url_scheme}{self.file_key(filename)}'

    def prefix(self):
        return f'{self.problem_id}/'

    def open(self, filename: str, *args):
        return self.zip.open(f'{self.prefix()}{filename}', *args)

    def namelist(self) -> List[str]:
        return [
            x.replace(self.prefix(), '') for x in
                filter(
                    lambda x: x.startswith(f'{self.prefix()}'),
                    self.zip.namelist(),
                )
        ]


async def load_config(ctx: ParseContext):
    try:
        with ctx.open(problem_config_filename, 'r') as f:
            cfg = json.load(f)
    except Exception as e:
        msg = f'cannot read {problem_config_filename}: {e}'
        raise InvalidProblemException(msg)
    try:
        cfg['Groups'] = [Group(**x) for x in cfg['Groups']]
        cfg['Details'] = [ConfigTestpoint(**x) for x in cfg['Details']]
        if 'Quiz' in cfg and cfg['Quiz']:
            try:
                with ctx.open(quiz_filename, 'r') as f:
                    quiz = json.load(f)
            except Exception as e:
                msg = f'cannot read {problem_config_filename}: {e}'
                raise InvalidProblemException(msg)
            for problem in quiz['problems']:
                problem['options'] = [QuizOption(**x) for x in problem['options']]
            ctx.plan.quiz = [QuizProblem(**x) for x in quiz['problems']]
        ctx.cfg = ProblemConfig(**cfg)
        ctx.testpoint_count = len(ctx.cfg.Details)
    except Exception as e:
        raise InvalidProblemException(str(e))


checker_source_filename = 'spj.cpp'
checker_precompiled_filename = 'spj_bin'
checker_exec_filename = 'checker'

async def parse_spj(ctx: ParseContext):
    spj = ctx.cfg.SPJ
    type_map = {
        Spj.CLASSIC_COMPARE: ('classic', 'compare'),
        Spj.CLASSIC_SPJ: ('classic', 'spj'),
        Spj.HPP_DIRECT: ('hpp', 'direct'),
        Spj.HPP_COMPARE: ('hpp', 'compare'),
        Spj.HPP_SPJ: ('hpp', 'spj'),
        Spj.NONE_SPJ: ('none', 'spj'),
    }
    if not spj in type_map:
        raise InvalidProblemException(f'Invalid SPJ type {spj}')
    ctx.compile_type, ctx.check_type = type_map[spj]
    if ctx.cfg.Scorer != 0:
        raise InvalidProblemException(f'Scorers are not supported (yet)')

    if ctx.check_type == 'spj':
        # A custom checker is needed for judging, so
        # register the checker executable artifact.
        if checker_precompiled_filename in ctx.namelist():
            ctx.checker_artifact = Artifact(
                ctx.file_url(checker_precompiled_filename))
        elif checker_source_filename in ctx.namelist():
            ctx.checker_artifact = Artifact(
                f'{url_scheme}{ctx.file_key(checker_exec_filename)}')
            ctx.checker_to_compile = ctx.file_url(checker_source_filename)
        else:
            raise InvalidProblemException(f'{checker_source_filename} not found')


hpp_main_filename = 'main.cpp'
hpp_main_template = '{}.cpp'
hpp_main_template_vlog = '{}.v'
hpp_src_filename = 'src.hpp'
hpp_src_filename_vlog = 'answer.v'

async def parse_compile(ctx: ParseContext) -> Optional[CompileTaskPlan]:
    limits = deepcopy(default_compile_limits)
    time_msecs = ctx.cfg.CompileTimeLimit
    if time_msecs is not None:
        limits.time_msecs = time_msecs
    ctx.compile_limits = limits

    supplementary_files = list(map(ctx.file_url, ctx.cfg.SupportedFiles))
    # make a copy here since we may want to append UserCode()
    # into supplementary_files, and there is no user code
    # during SPJ compilation.
    ctx.compile_supp = supplementary_files[:]

    if ctx.compile_type == 'none':
        return None

    task = CompileTaskPlan(
        source=UserCode(),
        supplementary_files=supplementary_files,
        artifact=True,
        limits=limits,
    )
    if ctx.compile_type == 'classic':
        return task
    src_filename = hpp_src_filename_vlog if ctx.cfg.Verilog \
        else hpp_src_filename
    task.supplementary_files.append(UserCode(src_filename))

    has_main = hpp_main_filename in ctx.namelist()
    if has_main:
        task.source = CompileSourceCpp(ctx.file_url(hpp_main_filename))
        return task
    # a seperate compilation is needed per testpoint, and
    # the generated compile task is just a template.
    # the compile task will be set to None in parse_testpoints.
    ctx.compile_type = 'hpp-per-testpoint'
    task.source = None
    task.artifact = False
    return task


# populate dependents from dependencies.
def generate_dependents(plan: List[JudgeTaskPlan]) \
    -> List[JudgeTaskPlan]:
    for i, deps in enumerate(x.dependencies for x in plan):
        for dep in deps:
            plan[dep].dependents.append(i)
    return plan

infile_name_template = '{}.in'
answer_name_template = '{}.ans'
answer_name_template_alt = '{}.out'

# TODO: detect loops in dependent_on relations
def parse_testpoint(ctx: ParseContext, conf: ConfigTestpoint) -> Testpoint:
    id = str(conf.ID)
    infile_name = infile_name_template.format(id)
    if infile_name in ctx.namelist():
        infile = ctx.file_url(infile_name)
    else:
        infile = None

    run_limits = deepcopy(default_run_limits)
    if conf.TimeLimit is not None: run_limits.time_msecs = conf.TimeLimit
    if conf.MemoryLimit is not None: run_limits.memory_bytes = conf.MemoryLimit
    if conf.DiskLimit is not None: run_limits.file_size_bytes = abs(conf.DiskLimit)
    if conf.FileNumberLimit is not None: run_limits.file_count = conf.FileNumberLimit

    type = 'verilog' if ctx.cfg.Verilog else \
        'valgrind' if conf.ValgrindTestOn else 'elf'
    run = None if ctx.compile_type == 'none' else RunArgs(
        type=type,
        limits=run_limits,
        infile=infile,
        supplementary_files=[],
    )

    def ans() -> Optional[FileUrl]:
        ans_filename = answer_name_template.format(id)
        if ans_filename in ctx.namelist():
            return ctx.file_url(ans_filename)
        ans_filename_alt = answer_name_template_alt.format(id)
        if ans_filename_alt in ctx.namelist():
            return ctx.file_url(ans_filename_alt)
        return None
    if ctx.check_type == 'compare':
        check = CompareChecker(True, ans())
        if check.answer is None:
            raise InvalidProblemException(f'Answer file needed for testpoint {id}')
    elif ctx.check_type == 'direct':
        check = DirectChecker()
    elif ctx.check_type == 'spj':
        check = SpjChecker(
            format='checker',
            executable=ctx.checker_artifact,
            answer=ans(),
            supplementary_files=[],
            limits=default_check_limits,
        )
    else:
        raise InvalidProblemException(f'Unknown check type {ctx.check_type}')

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
        ctor = CompileSourceVerilog if ctx.cfg.Verilog else CompileSourceCpp
        task.source = ctor(ctx.file_url(main_template.format(id)))
        testpoint.input = task
    return testpoint

async def parse_testpoints(ctx: ParseContext) -> List[JudgeTaskPlan]:
    testpoints = [parse_testpoint(ctx, x) for x in ctx.cfg.Details]
    testpoints_map = dict((tp.id, tp) for tp in testpoints)
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


group_name_template = 'Task {}'

async def parse_groups(ctx: ParseContext) -> List[TestpointGroup]:
    return [TestpointGroup(
        id=str(conf.GroupID),
        name=conf.GroupName if conf.GroupName is not None \
            else group_name_template.format(conf.GroupID),
        testpoints=[str(x) for x in conf.TestPoints],
        score=float(conf.GroupScore),
    ) for conf in ctx.cfg.Groups]


async def upload_files(ctx: ParseContext):
    files_not_found = list(filter(lambda file: not file in ctx.namelist(),
        ctx.files_to_upload))
    if len(files_not_found) > 0:
        raise InvalidProblemException(f'file(s) {files_not_found} not found in problem zip')
    for file in ctx.files_to_upload:
        with ctx.open(file, 'r') as f:
            await upload_obj(s3_buckets.problems, ctx.file_key(file), f)


async def compile_checker(ctx: ParseContext):
    source = ctx.checker_to_compile
    if source is None:
        return
    task = CompileTask(
        source=CompileSourceCpp(sign_url(source)),
        supplementary_files=list(map(sign_url, ctx.compile_supp)),
        artifact=Artifact(sign_url_put(s3_buckets.problems,
            ctx.file_key(checker_exec_filename))),
        limits=ctx.compile_limits,
    )
    msg = f'Compiling SPJ for problem {ctx.problem_id}'
    res = await run_task(TaskInfo(task, None, ctx.problem_id,
                                  ctx.cfg.RunnerGroup, msg))
    if res.result != 'compiled':
        msg = f'Cannot compile checker ({res.result}): {res.message}'
        raise InvalidProblemException(msg)


async def generate_plan(problem_id: str) -> JudgePlan:
    logger.info(f'generating plan for {problem_id}')
    zip_filename = f'{problem_id}.zip'
    zip_path = working_dir / zip_filename
    try:
        await download(s3_buckets.problems, zip_filename, zip_path)
        with ZipFile(zip_path) as zip:
            ctx = ParseContext(problem_id, zip)
            await load_config(ctx)
            ctx.plan.group = ctx.cfg.RunnerGroup
            if ctx.plan.quiz is not None:
                return ctx.plan
            await parse_spj(ctx)
            ctx.plan.compile = await parse_compile(ctx)
            ctx.plan.judge = await parse_testpoints(ctx)
            ctx.plan.score = await parse_groups(ctx)
            await upload_files(ctx)
            await compile_checker(ctx)
            logger.debug(f'generated plan for {problem_id}: {ctx.plan}')
            return ctx.plan
    finally:
        try:
            remove(zip_path)
        except Exception as e:
            logger.error(f'cannot remove problem zip: {format_exc(e)}')
