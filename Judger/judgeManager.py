from Judger.Judger_Core.config import *
from Judger.JudgerResult import *
from Judger.Judger_Core.Compiler.Compiler import compiler
from Judger.Judger_Core.classic_judger import ClassicJudger
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
        compileResult = compiler.CompileInstance(CompilationConfig(sourceCode, language, problemConfig.CompileTimeLimit))
        if not compileResult.compiled:
            judgeResult = JudgerResult(ResultType.CE._value_, 0, 0, 0, [DetailResult(testcase.ID, ResultType.CE._value_, 0, 0, 0, -1, compileResult.msg) for testcase in problemConfig.Details], problemConfig)
        else:
            Details = []
            for testcase in problemConfig.Details:
                if testcase.Dependency == 0 or Details[testcase.Dependency - 1].result == ResultType.AC._value_:
                    relatedFile = dataPath + '/' + str(testcase.ID)
                    testPointDetail, userOutput = ClassicJudger().JudgeInstance(
                        TestPointConfig(
                            compileResult.programPath,
                            None,
                            relatedFile + '.in',
                            testcase.TimeLimit,
                            testcase.MemoryLimit,
                            testcase.DiskLimit,
                            testcase.Dependency == 0,
                            testcase.ValgrindTestOn
                        )
                    )
                    testPointDetail.ID = testcase.ID
                    if testPointDetail.result == ResultType.UNKNOWN._value_:
                        if problemConfig.SPJ == 1:
                            subprocess.run([dataPath + '/spj', relatedFile + '.in', userOutput, relatedFile + '.ans', 'score.log', 'message.log'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 10)
                            with open('score.log') as f:
                                testPointDetail.score = float("\n".join(f.readline().splitlines()))
                            testPointDetail.result = ResultType.WA._value_ if testPointDetail.score == 0 else ResultType.AC._value_
                            with open('message.log') as f:
                                testPointDetail.message += f.readline().splitlines()
                        else:
                            runDiff = subprocess.run(['diff', '-Z', '-B', userOutput , relatedFile + '.ans'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 10)
                            if runDiff.returncode == 0:
                                testPointDetail.score, testPointDetail.result = 1.0, ResultType.AC._value_
                            else:
                                testPointDetail.score, testPointDetail.result = 0.0, ResultType.WA._value_
                                #testPointDetail.message += runDiff.stdout.decode() + runDiff.stderr.decode()
                    else:
                        testPointDetail.score = 0.
                        if testPointDetail.result == ResultType.TLE._value_ :
                            testPointDetail.message = "Time Limit Exceeded\n"
                        elif testPointDetail.result == ResultType.MLE._value_ :
                            testPointDetail.message = "Memory Limit Exceeded\n"
                        elif testPointDetail.result == ResultType.RE._value_ :
                            testPointDetail.message = "Runtime Error\n"
                        else:
                            testPointDetail.message = "Memory Leak\n"
                    testPointDetail.ID = testcase.ID
                    Details.append(testPointDetail)
                else:
                    Details.append(DetailResult(testcase.ID, ResultType.SKIPPED._value_, 0, 0, 0, -1, 'Skipped.'))
            status = ResultType.AC._value_
            totalTime = 0
            maxMem = 0
            for detail in Details:
                if detail.result != ResultType.AC._value_ and status == ResultType.AC._value_:
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
                    process = subprocess.run(dataPath + '/scorer.py', stdin = inputString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 10)
                except subprocess.TimeoutExpired:
                    judgeResult = JudgerResult(ResultType.SYSERR._value_, 0, 0, 0, [[testcase.ID, ResultType.SYSERR._value_, 0, 0, 0, -1, 'Scorer timeout.\n'] for testcase in problemConfig.Details], problemConfig)
                else:
                    score = process.stdout.decode()
                    print(process.stderr.decode())
                    judgeResult = JudgerResult(status, score, totalTime, maxMem, Details, problemConfig)
        #print("One",judgeResult.Status,judgeResult.TimeUsed,judgeResult.MemUsed)
        #for i in judgeResult.Details:
        #    print(i.ID,i.result,i.score,i.time,i.memory,i.disk,i.message)
        return judgeResult


judgeManager = JudgeManager()