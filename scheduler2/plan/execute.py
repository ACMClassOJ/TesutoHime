__all__ = 'execute_plan', 'get_partial_result'

import json
from asyncio import (FIRST_COMPLETED, CancelledError, Task, create_task, sleep,
                     wait)
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from logging import getLogger
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from typing_extensions import Literal, TypeAlias, TypeGuard, overload

from commons.task_typing import (Artifact, CodeLanguage, CompareChecker,
                                 CompileResult, CompileSource,
                                 CompileSourceCpp, CompileSourceGit,
                                 CompileSourceVerilog, CompileTask,
                                 CompileTaskPlan, DirectChecker,
                                 GroupJudgeResult, Input, JudgePlan,
                                 JudgeResult, JudgeTask, JudgeTaskPlan,
                                 ProblemJudgeResult, QuizProblem,
                                 ResourceUsage, ResultType, SourceLocation,
                                 SpjChecker, StatusUpdate,
                                 StatusUpdateProgress, StatusUpdateStarted,
                                 Testpoint, TestpointGroup,
                                 TestpointJudgeResult, UserCode)
from commons.util import format_exc
from scheduler2.config import s3_buckets
from scheduler2.dispatch import TaskInfo, run_task
from scheduler2.plan.util import (InvalidCodeException,
                                  InvalidProblemException, sign_url)
from scheduler2.s3 import (copy_file, read_file, remove_file, sign_url_get,
                           sign_url_put)
from scheduler2.util import update_status

logger = getLogger(__name__)


# typing shim for Python 3.7
try:
    Task[None]
except TypeError:
    class _Task:
        def __getitem__(self, _): return Any
    Task = _Task()  # type: ignore


class UrlType(Enum):
    CODE = auto()
    ARTIFACT = auto()

class DependencyNotSatisfied(str):
    def __str__(self) -> str:
        return 'DependencyNotSatisfied'

@dataclass
class JudgeTaskRecord:
    task: JudgeTask[Input]
    plan: JudgeTaskPlan
    result: Optional[JudgeResult] = None

@dataclass
class ExecutionContext:
    plan: JudgePlan
    id: str
    problem_id: str
    lang: CodeLanguage
    code: SourceLocation
    rate_limit_group: str
    compile: Optional[CompileTask] = None
    compile_message: Optional[str] = None
    judge: Optional[List[JudgeTaskRecord]] = None
    code_key: Optional[str] = None
    compile_artifact: Optional[Artifact] = None
    files_to_clean: Set[Tuple[str, str]] = field(default_factory=lambda: set())
    results: Dict[str, TestpointJudgeResult] = field(default_factory=lambda: {})

    def file_url(self, type: UrlType, filename: str):
        key = f'{self.id}/{filename}'
        if type == UrlType.CODE:
            if self.code_key is not None \
            and self.code_key != key:
                msg = 'Trying to use user code as different files'
                raise InvalidProblemException(msg)
            self.code_key = key

            return sign_url_get(s3_buckets.artifacts, key)
        elif type == UrlType.ARTIFACT:
            if self.compile_artifact is not None:
                raise InvalidProblemException('Duplicate compile artifact')
            bucket = s3_buckets.artifacts
            self.files_to_clean.add((bucket, key))
            self.compile_artifact = Artifact(sign_url_get(bucket, key))
            return sign_url_put(bucket, key)
        else:
            raise Exception(f'Invalid url type {type}')

    def dependencies_satisfied(self, rec: JudgeTaskRecord) -> TypeGuard[bool]:
        def dependency_satisfied(testpoint: Testpoint) -> bool:
            dep = testpoint.dependent_on
            return dep is None or isinstance(dep, DependencyNotSatisfied) \
                or any(dep == tp.id for tp in rec.task.testpoints)
        return all(map(dependency_satisfied, rec.task.testpoints))


raw_code_filename = 'code'
cpp_main_filename = 'main.cpp'
python_main_filename = 'main.py'
verilog_main_filename = 'main.v'
artifact_filename = 'main'

async def get_compile_source(ctx: ExecutionContext, filename: str) \
    -> Union[CompileSource, Artifact]:
    if ctx.lang == CodeLanguage.CPP:
        return CompileSourceCpp(ctx.file_url(UrlType.CODE, filename))
    if ctx.lang == CodeLanguage.GIT:
        url = (await read_file(ctx.code.bucket, ctx.code.key)).strip()
        if url.startswith('/'):
            raise InvalidCodeException('Local clone not allowed')
        return CompileSourceGit(url)
    if ctx.lang == CodeLanguage.PYTHON:
        return Artifact(ctx.file_url(UrlType.CODE, python_main_filename))
    if ctx.lang == CodeLanguage.VERILOG:
        return CompileSourceVerilog(ctx.file_url(UrlType.CODE, filename))
    raise InvalidCodeException('Unknown language')

@overload
async def prepare_compile(ctx: ExecutionContext, plan: CompileTaskPlan) -> Union[CompileTask, Artifact]: pass
@overload
async def prepare_compile(ctx: ExecutionContext, plan: None) -> None: pass
async def prepare_compile(ctx, plan):
    if plan is None:
        return None

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
        source = await get_compile_source(ctx, filename)
        if isinstance(source, Artifact):
            ctx.compile_artifact = source
            return source
        source: CompileSource
    else:
        source = deepcopy(plan.source)
        if isinstance(source, CompileSourceCpp) \
        or isinstance(source, CompileSourceVerilog):
            source.main = sign_url(source.main)
    def map_supplementary_file(file):
        if isinstance(file, UserCode):
            return ctx.file_url(UrlType.CODE, filename)
        else:
            return sign_url(file)
    supplementary_files = [map_supplementary_file(x) for x in
        plan.supplementary_files]

    artifact = Artifact(ctx.file_url(UrlType.ARTIFACT, artifact_filename)) \
        if plan.artifact else None
    limits = deepcopy(plan.limits)
    return CompileTask(source, supplementary_files, artifact, limits)


async def get_judge_task(ctx: ExecutionContext, plan: JudgeTaskPlan) \
    -> JudgeTaskRecord:
    task: JudgeTask[Input] = deepcopy(plan.task)  # type: ignore
    for testpoint in task.testpoints:
        if isinstance(testpoint.input, UserCode):
            if ctx.compile_artifact is None:
                ctx.compile_artifact = Artifact(ctx.file_url(UrlType.CODE,
                    raw_code_filename))
            testpoint.input = ctx.compile_artifact
        elif isinstance(testpoint.input, CompileTaskPlan):
            testpoint.input = await prepare_compile(ctx, testpoint.input)
        elif isinstance(testpoint.input, CompileTask):
            pass
        elif isinstance(testpoint.input, Artifact):
            testpoint.input.url = sign_url(testpoint.input.url)
        else:
            msg = f'Unknown testpoint input type at testpoint {testpoint.id}'
            raise InvalidProblemException(msg)

        if testpoint.run is not None:
            if testpoint.run.type == 'elf':
                if ctx.lang == CodeLanguage.PYTHON:
                    testpoint.run.type = 'python'

            interactor_cfg = testpoint.run.interactor
            if interactor_cfg is not None:
                interactor_exe = interactor_cfg.executable
                if isinstance(interactor_exe, Artifact):
                    interactor_exe.url = sign_url(interactor_exe.url)

            if testpoint.run.infile is not None:
                testpoint.run.infile = sign_url(testpoint.run.infile)
            testpoint.run.supplementary_files = \
                [sign_url(x) for x in testpoint.run.supplementary_files]

        if isinstance(testpoint.check, CompareChecker):
            testpoint.check.answer = sign_url(testpoint.check.answer)
        elif isinstance(testpoint.check, DirectChecker):
            pass
        elif isinstance(testpoint.check, SpjChecker):
            if testpoint.check.answer is not None:
                testpoint.check.answer = sign_url(testpoint.check.answer)
            if not isinstance(testpoint.check.executable, Artifact):
                raise InvalidProblemException('Invalid SPJ')
            testpoint.check.executable.url = \
                sign_url(testpoint.check.executable.url)
            testpoint.check.supplementary_files = \
                [sign_url(x) for x in testpoint.check.supplementary_files]

    return JudgeTaskRecord(task, deepcopy(plan))

async def get_judge_tasks(ctx: ExecutionContext) -> List[JudgeTaskRecord]:
    return [await get_judge_task(ctx, plan) for plan in ctx.plan.judge]


async def upload_code(ctx: ExecutionContext):
    if ctx.code_key is not None:
        bucket = s3_buckets.artifacts
        logger.debug('uploading user code to %(bucket)s/%(key)s', { 'bucket': bucket, 'key': ctx.code_key }, 'code:upload')
        ctx.files_to_clean.add((bucket, ctx.code_key))
        await copy_file(ctx.code, bucket, ctx.code_key)


async def run_compile_task(ctx: ExecutionContext) -> Optional[CompileResult]:
    if ctx.compile is None or isinstance(ctx.compile, Artifact):
        return None
    async def onprogress(status):
        if isinstance(status, StatusUpdateStarted):
            await update_status(ctx.id, 'compiling')
    msg = f'Compiling code for submission #{ctx.id}'
    task = TaskInfo(ctx.compile, ctx.id, ctx.problem_id, ctx.plan.group, msg)
    return await run_task(task, onprogress, ctx.rate_limit_group)


def skipped_result(name, message = 'Skipped'):
    return TestpointJudgeResult(name, 'skipped', message)

def remove_skipped_testpoints_from_task(ctx: ExecutionContext,
                                        plan: JudgeTaskPlan,
                                        accepted: List[Testpoint],
                                        unaccepted: List[Testpoint]):
    # for all dependent tasks...
    for dependent in plan.dependents:
        assert ctx.judge is not None
        rec = ctx.judge[dependent]
        removed_testpoints: List[Testpoint] = []
        testpoints_removed = True
        while testpoints_removed:
            testpoints_removed = False
            # for all testpoints with dependencies in task...
            for testpoint in rec.task.testpoints:
                if testpoint.dependent_on is not None:
                    # for all testpoints we have just decided to be unaccepted...
                    for tp1 in accepted:
                        # if it is the dependency...
                        if testpoint.dependent_on == tp1.id:
                            testpoint.dependent_on = None
                            break
                    if testpoint.dependent_on is None:
                        continue
                    for tp1 in unaccepted:
                        # if it is the dependency...
                        if testpoint.dependent_on == tp1.id:
                            testpoint.dependent_on = DependencyNotSatisfied()
                            ctx.results[testpoint.id] = \
                                skipped_result(testpoint.id,
                                               f'testpoint {tp1.id} failed')
                            removed_testpoints.append(testpoint)
                            unaccepted.append(testpoint)
                            break
        rec.task.testpoints = list(filter(lambda x: x not in removed_testpoints,
                                          rec.task.testpoints))
        # do it recursively until no testpoints are removed
        if len(removed_testpoints) > 0:
            remove_skipped_testpoints_from_task(ctx, rec.plan, [],
                                                removed_testpoints)

async def run_judge_tasks(ctx: ExecutionContext):
    await update_status(ctx.id, 'judging')
    records = ctx.judge
    assert records is not None
    ready = list(filter(ctx.dependencies_satisfied, records))
    ResType: TypeAlias = Task[Union[
        Tuple[JudgeTaskRecord, Literal[True], JudgeResult],
        Tuple[JudgeTaskRecord, Literal[False], Exception],
    ]]
    tasks_running: List[ResType] = []
    def run(task: JudgeTaskRecord) -> Optional[ResType]:
        if len(task.task.testpoints) == 0:
            return None
        async def onprogress(status: StatusUpdate):
            if isinstance(status, StatusUpdateStarted):
                for testpoint in task.task.testpoints:
                    if not testpoint.id in ctx.results:
                        ctx.results[testpoint.id] = TestpointJudgeResult(
                            testpoint.id, 'judging', 'Judging')
            elif isinstance(status, StatusUpdateProgress):
                assert isinstance(status.result, JudgeResult)
                for testpoint1 in status.result.testpoints:
                    if testpoint1 is not None and (
                        not testpoint1.id in ctx.results
                        or ctx.results[testpoint1.id].result
                            in ('pending', 'judging')):
                        ctx.results[testpoint1.id] = testpoint1
        async def run_with_rec():
            try:
                msg = f'Running test for submission #{ctx.id}'
                taskinfo = TaskInfo(task.task, ctx.id, ctx.problem_id,
                                    ctx.plan.group, msg)
                return (task, True, await run_task(taskinfo, onprogress,
                    ctx.rate_limit_group))
            except CancelledError:
                raise
            except Exception as e:
                return (task, False, e)
        return create_task(run_with_rec())
    while len(ready) > 0 or len(tasks_running) > 0:
        tasks_running.extend(filter(lambda x: x is not None, map(run, ready)))  # type: ignore
        if len(tasks_running) == 0:
            ready = []
            break
        try:
            done, pending = await wait(tasks_running, return_when=FIRST_COMPLETED)
        except CancelledError:
            for task in tasks_running:
                if not task.cancelled():
                    task.cancel()
            raise
        tasks_running = list(pending)
        dependents = set()
        for task in done:
            record, ok, res = await task  # type: Tuple[Any, Any, Any]
            if not ok:
                error = res
                res = JudgeResult([TestpointJudgeResult(
                    id=x.id,
                    result='system_error',
                    message=str(error),
                ) for x in record.plan.task.testpoints])
            record.result = res

            for testpoint in res.testpoints:
                if testpoint is not None:
                    ctx.results[testpoint.id] = testpoint
            for testpoint in record.task.testpoints:
                if not testpoint.id in ctx.results:
                    ctx.results[testpoint.id] = skipped_result(testpoint.id)

            unaccepted_testpoints = []
            accepted_testpoints = []
            for testpoint in record.task.testpoints:
                status = list(filter(lambda x: x.id == testpoint.id,  # type: ignore
                    record.result.testpoints))
                if len(status) == 1 and status[0].result == 'accepted':
                    accepted_testpoints.append(testpoint)
                else:
                    unaccepted_testpoints.append(testpoint)
            remove_skipped_testpoints_from_task(ctx, record.plan,
                                                accepted_testpoints,
                                                unaccepted_testpoints)

            dependents.update(record.plan.dependents)
        dependents = (records[id] for id in dependents)
        ready = list(filter(ctx.dependencies_satisfied, dependents))


def synthesize_results(results: Iterable[ResultType]) -> ResultType:
    results_list = list(results)
    if 'system_error' in results_list:
        return 'system_error'
    if 'bad_problem' in results_list:
        return 'bad_problem'
    for res in results_list:
        if res != 'accepted':
            return res
    return 'accepted'

def synthesize_rusage(rusages: Iterable[ResourceUsage]) -> ResourceUsage:
    rusages = list(filter(lambda x: x is not None, rusages))
    return ResourceUsage(
        time_msecs=sum((x.time_msecs for x in rusages), 0),
        memory_bytes=max((x.memory_bytes for x in rusages), default=-1),
        file_count=max((x.file_count for x in rusages), default=-1),
        file_size_bytes=max((x.file_size_bytes for x in rusages), default=-1),
    )

def aborted_result(name):
    return TestpointJudgeResult(name, 'aborted', 'Aborted')
def pending_result(name):
    return TestpointJudgeResult(name, 'pending', 'Pending')

def synthesize_scores(ctx: ExecutionContext, *, aborted: bool = False,
    in_progress: bool = False) -> ProblemJudgeResult:
    testpoints = ctx.results
    rusage = synthesize_rusage(x.resource_usage for x in  # type: ignore
        filter(lambda x: x is not None and x.resource_usage is not None, testpoints.values()))
    def fallback_result(_):
        raise InvalidProblemException('Loop detected in dependent_on relations')
    if aborted: fallback_result = aborted_result
    if in_progress: fallback_result = pending_result
    def get_group_result(group: TestpointGroup):
        res = [testpoints[x] if x in testpoints else fallback_result(x)
            for x in group.testpoints]
        if aborted:
            res = [x if x.result not in ('judging', 'pending')
                else aborted_result(x.id) for x in res]
        result = synthesize_results(x.result for x in res)
        score = min(x.score for x in res) * group.score
        return GroupJudgeResult(group.id, group.name, result, res, score)
    groups = list(map(get_group_result, ctx.plan.score))
    score = sum(x.score for x in groups)
    result = synthesize_results(x.result for x in groups)
    message = ctx.compile_message if ctx.compile_message != '' else None
    if aborted:
        result = 'aborted'
        score = 0.0
    if in_progress:
        result = 'judging'
        score = 0.0
    return ProblemJudgeResult(result, message, score, rusage, groups)


async def judge_quiz(quiz: List[QuizProblem], answer: Dict[str, str]):
    def ac(id):
        return TestpointJudgeResult(id, 'accepted', 'Accepted', 1.0)
    def wa(id):
        return TestpointJudgeResult(id, 'wrong_answer', 'Wrong Answer')
    correct = dict((x.id, x.type == 'SELECT' and x.answer == answer.get(x.id, None)) for x in quiz)
    testpoints = [ac(id) if correct[id] else wa(id) for id in correct]
    result: Literal['accepted', 'wrong_answer'] = \
        'accepted' if all(correct[id] for id in correct) else 'wrong_answer'
    score = float(len(list(filter(lambda id: correct[id], correct))))
    groups = [GroupJudgeResult('quiz', 'Quiz', result, testpoints, score)]
    return ProblemJudgeResult(result, None, score, groups=groups)

ctx_from_submission: Dict[str, ExecutionContext] = {}

async def execute_plan(plan: JudgePlan, id: str, problem_id: str,
    lang: CodeLanguage, code: SourceLocation, rate_limit_group: str) \
    -> ProblemJudgeResult:
    ctx = ExecutionContext(plan, id, problem_id, lang, code, rate_limit_group)
    ctx_from_submission[id] = ctx
    compiled = False

    if lang == CodeLanguage.QUIZ:
        if plan.quiz is None:
            raise InvalidCodeException('This problem is not a quiz.')
        answer = await read_file(code.bucket, code.key)
        try:
            answer = json.loads(answer)
        except Exception as e:
            raise InvalidCodeException(f'Answer is invalid JSON: {e}')
        return await judge_quiz(plan.quiz, answer)  # type: ignore
    if plan.quiz is not None:
        raise InvalidCodeException('This problem is a quiz. Do not submit code.')

    try:
        ctx.compile = await prepare_compile(ctx, ctx.plan.compile)  # type: ignore
        ctx.judge = await get_judge_tasks(ctx)
        await upload_code(ctx)
        compile_res = await run_compile_task(ctx)
        if compile_res is not None and compile_res.result != 'compiled':
            status: ResultType = \
                'system_error' if compile_res.result == 'system_error' \
                else 'aborted' if compile_res.result == 'aborted' \
                else 'compile_error'
            message = compile_res.message
            if status == 'compile_error':
                prefix = compile_res.result.replace('_', ' ')
                if message != '':
                    message = f'{prefix}: {message}'
                else:
                    message = prefix
            gcc_error = 'runtime error: Program exited with status 1: '
            if message.startswith(gcc_error):
                message = message.replace(gcc_error, '', 1)
            return ProblemJudgeResult(status, message)
        if compile_res is not None:
            ctx.compile_message = compile_res.message
        compiled = True
        await run_judge_tasks(ctx)
        return synthesize_scores(ctx)
    except CancelledError:
        # sleep for a while to allow abort signals to be delivered
        await sleep(1)
        if compiled:
            return synthesize_scores(ctx, aborted=True)
        return ProblemJudgeResult('aborted', message=None)
    finally:
        # perform some cleanup
        del ctx_from_submission[id]
        for bucket, key in ctx.files_to_clean:
            try:
                await remove_file(bucket, key)
            except Exception as e:
                logger.warn('Error clearing object: %(error)s', { 'error': e }, 'plan:execute:cleanup')

async def get_partial_result(submission_id):
    if not submission_id in ctx_from_submission:
        return None
    ctx = ctx_from_submission[submission_id]
    return synthesize_scores(ctx, in_progress=True)
