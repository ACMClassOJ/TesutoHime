from .compile import NotCompiledException, ensure_input
from task_typing import CheckInput, Checker, TestpointJudgeResult


async def check (input: CheckInput, checker: Checker) -> TestpointJudgeResult:
    # get output file to check
    if input.type != 'run_result':
        try:
            ouf = (await ensure_input(input)).path
        except NotCompiledException as e:
            return TestpointJudgeResult(None, 'compile_error', str(e))
    else:
        ouf = input.output_path
    if ouf is None:
        return TestpointJudgeResult(None, 'system_error', 'Nothing to check')

    # check
    # TODO
    pass
