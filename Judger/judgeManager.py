from Judger.Judger_Core.config import *
from Judger.JudgerResult import *
from Judger.Judger_Core.Compiler.Compiler import compiler
import subprocess

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
        if not compileResult.compiled:
            judgeResult = JudgerResult(ResultType.CE, 0, 0, 0, [[testcase.ID, ResultType.CE, 0, 0, 0, -1, compileResult.msg] for testcase in problemConfig.Details], problemConfig)
        else:
            Details = []
            for testcase in problemConfig.Details:
                if testcase.Dependency == 0 or Details[testcase.Dependency - 1].result == ResultType.AC:
                    pass
                    #to do: judge
                else:
                    Details.append(DetailResult(testcase.ID, ResultType.SKIPED, 0, 0, 0, -1, 'Skipped.'))
            status = ResultType.AC
            totalTime = 0
            maxMem = 0
            for detail in Details:
                if detail.result != ResultType.AC && status != ResultType.AC:
                    status = detail.result
                totalTime += detail.time
                maxMem = max(maxMem, detail.memory)
            if problemConfig.Scorer == 0:
                score = 0
                for group in problemConfig.Groups:
                    if len(group.TestPoints) == 0:
                        continue
                    minScore = Details[group.TestPoints[0] - 1].score
                    for testPoint in group.TestPoints:
                        minScore = min(minScore, Details[testPoint - 1].score)
                    score += minScore * group.GroupScore
                judgeResult = JudgerResult(status, score, totalTime, maxMem, Details, problemConfig)
            else:
                try:
                    inputString = str(len(Details)) + ' '
                    for detail in Details:
                        inputString += str(detail.score) + ' '
                    inputString += str(len(problemConfig.Groups)) + ' '
                    for group in problemConfig.Groups:
                        inputString += str(len(group.TestPoints)) + ' ' + str(group.GroupScore) + ' '
                        for testPoint in group.TestPoints:
                            inputString += str(testPoint) + ' '
                    process = subprocess.run(dataPath + '/scorer.py', text = True, stdin = inputString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 10000)
                except subprocess.TimeoutExpired:
                    judgeResult = JudgerResult(ResultType.SYSERR, 0, 0, 0, [[testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, 'Scorer timeout.\n'] for testcase in problemConfig.Details], problemConfig)
                else:
                    score = process.stdout.decode()
                    print(process.stderr.decode())
                    judgeResult = JudgerResult(status, score, totalTime, maxMem, Details, problemConfig)
        self.judgingFlag = False
        return judgeResult


judgeManager = JudgeManager()