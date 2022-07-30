from util import work_file
from Judger_Core.config import *
from JudgerResult import *
from Judger_Core.Compiler.Compiler import compiler
from Judger_Core.classic_judger import ClassicJudger
from Judger_Data import ProblemConfig, Group
from Judger_Core.util import log
import multiprocessing
import subprocess
import os.path
import json, shutil, stat

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
                    with open(os.path.join(dataPath, fileName)) as f:
                        srcDict[fileName] = f.read()
                except:
                    testPointDetail = DetailResult(1, ResultType.SYSERR, 0, 0, 0, -1, "\"" + fileName + '" not found in data.')            
        # end

        # judge part: modified by siriusneo 2022 7.8

        # spj 0 single file with diff
        # spj 1 single file with spj
        # spj 2 hpp without diff
        # spj 3 hpp with diff
        # spj 4 hpp with spj
        # spj 5 output only

        # 0. Judging quiz
        if language == 'quiz':
            log.info("JudgeManager: Judging Quiz")
            with open(dataPath + "/quiz.json") as f:
                right_ans_json = json.load(f)
            student_ans_json = json.loads(sourceCode)
            quiz_correct_cnt = 0
            Details = []
            Groups_Details = []
            for i in right_ans_json["problems"]:
                if i["answer"] == "":
                    quiz_correct_cnt += 1
                    testPointDetail = DetailResult(int(i["id"]), ResultType.AC, 1, 0, 0, 0, "主观题不加判断先记为正确，请等待助教手动给分。")
                    groupPointDetail = Group(int(i["id"]), "", 1, [int(i["id"])])
                elif i["id"] in student_ans_json and i["answer"] == student_ans_json[i["id"]]:
                    quiz_correct_cnt += 1
                    testPointDetail = DetailResult(int(i["id"]), ResultType.AC, 1, 0, 0, 0, "Accepted")
                    groupPointDetail = Group(int(i["id"]), "", 1, [int(i["id"])])
                else:
                    testPointDetail = DetailResult(int(i["id"]), ResultType.WA, 0, 0, 0, 0, "Wrong Answer")
                    groupPointDetail = Group(int(i["id"]), "", 0, [int(i["id"])])
                Details.append(testPointDetail)
                Groups_Details.append(groupPointDetail)
            if quiz_correct_cnt == len(right_ans_json["problems"]):
                judgeResult = JudgerResult(ResultType.AC, quiz_correct_cnt, 0, 0, Details, ProblemConfig(Groups_Details, Details, 0, 0, 0))
            else:
                judgeResult = JudgerResult(ResultType.WA, quiz_correct_cnt, 0, 0, Details, ProblemConfig(Groups_Details, Details, 0, 0, 0))
            return judgeResult

        # 1. Compiling spj: compile only once (Only 1, 4, 5 need)
        spjBinCompiled = True
        if problemConfig.SPJ in [1, 4, 5]:
            if os.path.isfile(dataPath + '/spj_bin'):
                log.info('JudgeManager: binary spj found')
                shutil.copy(dataPath + '/spj_bin', dataPath + '/spj')
                os.chmod(dataPath + '/spj', stat.S_IXUSR)
            else:
                log.info("JudgeManager: compile once for spj")
                try:
                    subprocess.run(
                                    ['g++', '-g', '-o', dataPath + '/spj', dataPath + '/spj.cpp', '-Ofast'] + 
                                    ([] if not "SPJCompiliationOption" in problemConfig._asdict() else problemConfig.SPJCompiliationOption),
                                    check=True 
                                    )
                except Exception as e:
                    log.error(e)
                    spjBinCompiled = False

        # 2. Load Student SRC
        if problemConfig.SPJ == 5:
            with open(outputFilePath, "w") as f:
                f.write(sourceCode)
            userOutput = outputFilePath
        else:
            if problemConfig.SPJ != 2 and problemConfig.SPJ != 3 and problemConfig.SPJ != 4:
                if language == 'Verilog':
                    srcDict['test.v'] = sourceCode
                else:
                    srcDict['main.cpp'] = sourceCode
                compileResult = compiler.CompileInstance(CompilationConfig(srcDict, language, problemConfig.CompileTimeLimit, False))
            else:
                if language == 'Verilog':
                    srcDict['answer.v'] = sourceCode
                else:
                    srcDict['src.hpp'] = sourceCode

        # 3. Judge Part.
        if problemConfig.SPJ != 5 and problemConfig.SPJ != 2 and problemConfig.SPJ != 3 and problemConfig.SPJ != 4 and not compileResult.compiled:
            # Normal Judge (no SPJ): CE
            log.error('1: Compilation Error')
            judgeResult = JudgerResult(ResultType.CE, 0, 0, 0, [DetailResult(1, ResultType.CE, 0, 0, 0, -1, compileResult.msg)], ProblemConfig([Group(1, '', 0, [1])], [1, 0, 0, 0, 0, False], 0, 0, 0))
        elif not spjBinCompiled:
            judgeResult = JudgerResult(ResultType.SYSERR, 0, 0, 0, [DetailResult(1, ResultType.SYSERR, 0, 0, 0, -1, 'Compiling spj.cpp failed.')], ProblemConfig([Group(1, '', 0, [1])], [1, 0, 0, 0, 0, False], 0, 0, 0))
        else:
            # Start Judging...
            Details = []
            manager = multiprocessing.Manager()
            return_dict = manager.dict()

            # For Testcase
            for testcase in problemConfig.Details:
                # 3.1 Testcase Dependency: If has dependency and dependency not AC, Skip.
                if testcase.Dependency != 0 and Details[testcase.Dependency - 1].result != ResultType.AC:
                    Details.append(DetailResult(testcase.ID, ResultType.SKIPPED, 0, 0, 0, -1, 'Skipped.'))
                    continue
                
                # 3.2 Check SPJ 2 3 4 Runnable.
                Runnable = True
                if problemConfig.SPJ == 2 or problemConfig.SPJ == 3 or problemConfig.SPJ == 4:
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
                        compileResult = compiler.CompileInstance(CompilationConfig(srcDict, language, problemConfig.CompileTimeLimit, False))
                        if not compileResult.compiled:
                            log.error('2: Compilation Error')
                            testPointDetail = DetailResult(testcase.ID, ResultType.CE, 0, 0, 0, -1, compileResult.msg)
                            Runnable = False
                
                # 3.3 Start Running
                if Runnable:
                    relatedFile = dataPath + '/' + str(testcase.ID)
                    if problemConfig.SPJ == 5:
                        testPointDetail = DetailResult(testcase.ID, ResultType.UNKNOWN, 0, 0, 0, -1, '')
                    else:
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

                    # If not UNKNOWN, some error must happen.
                    # Otherwise, Start Judging
                    if testPointDetail.result == ResultType.UNKNOWN:
                        # SPJ 1 4 5: Run ./spj
                        if problemConfig.SPJ == 1 or problemConfig.SPJ == 4 or problemConfig.SPJ == 5:
                            log.info('JudgeManager: start spj')
                            try:
                                # upd, I guess that this line can be moved to the top, and excuted once for a judge
                                # subprocess.run(['g++', '-g', '-o', dataPath + '/spj', dataPath + '/spj.cpp', '-Ofast'] + ([] if not "SPJCompiliationOption" in problemConfig._asdict() else problemConfig.SPJCompiliationOption))

                                score_file = work_file('score.log')
                                message_file = work_file('score.log')
                                if os.path.isfile(relatedFile + '.ans'):
                                    subprocess.run(['./spj', relatedFile + '.in', userOutput, relatedFile + '.ans', score_file, message_file], 
                                    timeout = 20, cwd = dataPath, check=True)
                                else:
                                    subprocess.run(['./spj', relatedFile + '.in', userOutput, relatedFile + '.out', score_file, message_file], 
                                    timeout = 20, cwd = dataPath, check=True)
                                with open(score_file) as f:
                                    testPointDetail.score = float("\n".join(f.readline().splitlines()))
                                testPointDetail.result = ResultType.WA if testPointDetail.score != 1 else ResultType.AC
                                with open(message_file) as f:
                                    testPointDetail.message = f.read()
                            except Exception as e:
                                log.error(e)
                                testPointDetail.score, testPointDetail.message, testPointDetail.result = 0, 'Error occurred while running ./spj.', ResultType.SYSERR
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

                # Append current details.
                Details.append(testPointDetail)
                
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
                    score_file = work_file('score.in')
                    with open(score_file, 'w') as f:
                        f.write(inputString)
                    with open(score_file, 'r') as f:
                        process = subprocess.run(['python', 'scorer.py'], stdin = f, stdout = subprocess.PIPE, stderr = subprocess.PIPE, timeout = 20, cwd = dataPath)
                except subprocess.TimeoutExpired:
                    judgeResult = JudgerResult(ResultType.SYSERR, 0, 0, 0, [DetailResult(testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, 'Scorer timeout.\n') for testcase in problemConfig.Details], problemConfig)
                else:
                    score = float(process.stdout.decode())
                    log.info(process.stderr.decode())
                    judgeResult = JudgerResult(status, score, totalTime, maxMem, Details, problemConfig)
        #print("One",judgeResult.Status,judgeResult.TimeUsed,judgeResult.MemUsed)
        for i in judgeResult.Details:
            log.info(str(i.ID) + ' ' + str(i.result) + ' ' + str(i.score) + ' ' + str(i.time) + ' ' + str(i.memory) + ' ' + str(i.disk) + ' ' + str(i.message))
        return judgeResult


judgeManager = JudgeManager()
