from genericpath import exists
from Judger_Core.config import *
from JudgerResult import *
from Judger_Core.Compiler.Compiler import compiler
from Judger_Core.classic_judger import ClassicJudger
from Judger_Data import ProblemConfig, Group, Detail
from Judger_Core.util import log
import multiprocessing
import subprocess
import os.path

class JudgeManager:
    def judge(self,
              problemConfig: ProblemConfig,
              dataPath: str,
              language: str,
              sourceCode: str
              ) -> JudgerResult:
        srcDict = {}

        # begin 2021 2 24 cxy
        if "SupportedFiles" in problemConfig._asdict():
            for fileName in problemConfig.SupportedFiles:
                try:
                    with open(dataPath + '/' + fileName) as f:
                        srcDict[fileName] = f.read()
                except:
                    testPointDetail = DetailResult(1, ResultType.SYSERR, 0, 0, 0, -1, "\"" + fileName + '" not found in data.')            
        # end

        if problemConfig.SPJ != 2 and problemConfig.SPJ != 3:
            if language == 'Verilog':
                srcDict['test.v'] = sourceCode
            else:
                srcDict['main.cpp'] = sourceCode
            compileResult = compiler.CompileInstance(CompilationConfig(srcDict, language, problemConfig.CompileTimeLimit))
        else:
            if language == 'Verilog':
                srcDict['answer.v'] = sourceCode
            else:
                srcDict['src.hpp'] = sourceCode



        if problemConfig.SPJ != 2 and problemConfig.SPJ != 3 and not compileResult.compiled:
            log.error('Compilation Error')
            #print(len(compileResult.msg))
            judgeResult = JudgerResult(ResultType.CE, 0, 0, 0, [DetailResult(1, ResultType.CE, 0, 0, 0, -1, compileResult.msg)], ProblemConfig([Group(1, '', 0, [1])], [1, 0, 0, 0, 0, False], 0, 0, 0))
        else:
            Details = []
            manager = multiprocessing.Manager()
            return_dict = manager.dict()
            for testcase in problemConfig.Details:
                if testcase.Dependency == 0 or Details[testcase.Dependency - 1].result == ResultType.AC:
                    Runnable = True
                    if problemConfig.SPJ == 2 or problemConfig.SPJ == 3:
                        Runnable = False
                        try:
                            if language == 'Verilog':
                                with open(dataPath + '/' + str(testcase.ID) + '.v') as f:
                                    srcDict['test.v'] = f.read()
                            else:
                                with open(dataPath + '/' + str(testcase.ID) + '.cpp') as f:
                                    srcDict['main.cpp'] = f.read()
                        except:
                            try:
                                if language == 'Verilog':
                                    with open(dataPath + '/' + 'test.v') as f:
                                        srcDict['test.v'] = f.read()
                                else:
                                    with open(dataPath + '/' + 'main.cpp') as f:
                                        srcDict['main.cpp'] = f.read()
                            except:
                                testPointDetail = DetailResult(testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, 'No main function found in data.')
                            else:
                                Runnable = True
                        else:
                            Runnable = True
                        if Runnable:
                            #print(srcDict.keys())
                            compileResult = compiler.CompileInstance(CompilationConfig(srcDict, language, problemConfig.CompileTimeLimit))
                            if not compileResult.compiled:
                                log.error('Compilation Error')
                                testPointDetail = DetailResult(testcase.ID, ResultType.CE, 0, 0, 0, -1, compileResult.msg)
                                Runnable = False
                    if Runnable:
                        relatedFile = dataPath + '/' + str(testcase.ID)
                        #testPointDetail, userOutput
                        judgeProcess = multiprocessing.Process(target=ClassicJudger().JudgeInstance, args=(
                            TestPointConfig(
                                'Verilog' if language == 'Verilog' else "C++",
                                compileResult.programPath,
                                None,
                                #'/dev/null' if not os.path.exists(relatedFile + '.in') else relatedFile + '.in',
                                '/dev/null' if not os.path.exists(relatedFile + '.in') else relatedFile + '.in',
                                testcase.TimeLimit,
                                testcase.MemoryLimit,
                                testcase.DiskLimit,
                                -1 if not 'FileNumberLimit' in testcase._asdict() else testcase.FileNumberLimit,
                                testcase.ValgrindTestOn
                            ),
                                return_dict)
                        )
                        log.info("start judging on testcase" + str(testcase.ID))
                        judgeProcess.start()
                        judgeProcess.join()
                        testPointDetail, userOutput = return_dict['testPointDetail'], return_dict['userOutput']
                        testPointDetail.ID = testcase.ID
                        if testPointDetail.result == ResultType.UNKNOWN:
                            if problemConfig.SPJ == 1:
                                try:
                                    subprocess.run(['g++', '-g', '-o', dataPath + '/spj', dataPath + '/spj.cpp', '-Ofast'])
                                    subprocess.run([dataPath + '/spj', relatedFile + '.in', userOutput, relatedFile + '.ans', 'score.log', 'message.log'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 20)
                                    with open('score.log') as f:
                                        testPointDetail.score = float("\n".join(f.readline().splitlines()))
                                    testPointDetail.result = ResultType.WA if testPointDetail.score != 1 else ResultType.AC
                                    with open('message.log') as f:
                                        testPointDetail.message.join(f.readline().splitlines())
                                except Exception as e:
                                    log.error(e)
                                    testPointDetail.score, testPointDetail.message, testPointDetail.result = 0, 'Error occurred while running SPJ.', ResultType.SYSERR
                            elif problemConfig.SPJ == 2:
                                try:
                                    with open(userOutput) as f:
                                        return_list = f.read().splitlines()
                                        testPointDetail.score = float(return_list[0])
                                        testPointDetail.result = ResultType.WA if testPointDetail.score != 1 else ResultType.AC
                                        for i in range(1, len(return_list)):
                                            testPointDetail.message += return_list[i] + '\n'
                                except Exception as e:
                                    log.error(e)
                                    testPointDetail.score, testPointDetail.message, testPointDetail.result = 0, "Something must be wrong with main.cpp.", ResultType.SYSERR
                            else:
                                try:
                                    if os.path.isfile(relatedFile + '.ans'):
                                        runDiff = subprocess.run(['diff', '-q', '-Z', '-B', userOutput , relatedFile + '.ans'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 30)
                                    else:
                                        runDiff = subprocess.run(['diff', '-q', '-Z', '-B', userOutput , relatedFile + '.out'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 30)
                                    #print(runDiff.stderr.decode() + runDiff.stdout.decode())
                                    if runDiff.returncode == 0:
                                        testPointDetail.score, testPointDetail.result = 1.0, ResultType.AC
                                    else:
                                        testPointDetail.score, testPointDetail.result = 0.0, ResultType.WA
                                        #testPointDetail.message += runDiff.stdout.decode() + runDiff.stderr.decode()
                                except Exception as e:
                                    log.error(e)
                                    testPointDetail.score, testPointDetail.message, testPointDetail.result = 0, 'Error occurred while comparing outputs.', ResultType.SYSERR
                        else:
                            testPointDetail.score = 0.
                            if testPointDetail.result == ResultType.TLE :
                                testPointDetail.message = "Time Limit Exceeded\n"
                            elif testPointDetail.result == ResultType.MLE :
                                testPointDetail.message = "Memory Limit Exceeded\n"
                            elif testPointDetail.result == ResultType.RE :
                                testPointDetail.message = "Runtime Error\n"
                            elif testPointDetail.result == ResultType.MEMLEK :
                                testPointDetail.message = "Memory Leak\n"
                    Details.append(testPointDetail)
                else:
                    Details.append(DetailResult(testcase.ID, ResultType.SKIPPED, 0, 0, 0, -1, 'Skipped.'))
            status = ResultType.AC
            totalTime = 0
            maxMem = 0
            for detail in Details:
                if detail.result != ResultType.AC and status == ResultType.AC:
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
                    process = subprocess.run(dataPath + '/scorer.py', stdin = inputString, stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 20)
                except subprocess.TimeoutExpired:
                    judgeResult = JudgerResult(ResultType.SYSERR, 0, 0, 0, [DetailResult(testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, 'Scorer timeout.\n') for testcase in problemConfig.Details], problemConfig)
                else:
                    score = process.stdout.decode()
                    log.info(process.stderr.decode())
                    judgeResult = JudgerResult(status, score, totalTime, maxMem, Details, problemConfig)
        #print("One",judgeResult.Status,judgeResult.TimeUsed,judgeResult.MemUsed)
        for i in judgeResult.Details:
            log.info(str(i.ID) + ' ' + str(i.result) + ' ' + str(i.score) + ' ' + str(i.time) + ' ' + str(i.memory) + ' ' + str(i.disk) + ' ' + str(i.message))
        return judgeResult


judgeManager = JudgeManager()
