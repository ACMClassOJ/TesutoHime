from Judger.Judger_Core.config import *
from Judger.JudgerResult import *
from Judger.Judger_Core.Compiler.Compiler import compiler

class JudgeManager:
    def __init__(self):
        self.judgingFlag = False

    def isJudging(self) -> bool:
        return self.judgingFlag

    def judge(self,
              problemConfig: ProblemConfig,
              dataPath: str,
              language: str,
              sourceCode: str
              ) -> JudgerResult:
        self.judgingFlag = True
        compileResult = compiler.CompileInstance(CompilationConfig(sourceCode, language, problemConfig.CompileTimeLimit))
        judgeResult = None
        if not compileResult.compiled:
            judgeResult = JudgerResult(ResultType.CE, 0, 0, 0, [[testcase.ID, ResultType.CE, 0, 0, 0, -1, compileResult.msg] for testcase in problemConfig.Details], problemConfig)
        else:
            Details = []
            for testcase in problemConfig.Details:
                if testcase.Dependency == 0 || Details[testcase.Dependency - 1].result == ResultType.AC:
                    pass
                    #to do: judge
                else :
                    Details.append(DetailResult(testcase.ID, ResultType.SKIPED, 0, 0, 0, -1, 'Skipped.'))
            status = ResultType.AC
            for detail in Details:
                if detail.result != ResultType.AC:
                    status = detail.result
                    break
        self.judgingFlag = False

judgeManager = JudgeManager()