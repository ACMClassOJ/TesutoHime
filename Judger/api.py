from flask import Flask, request
import requests
import json
from judgeManager import judgeManager
from JudgerResult import *
from config import *
from Judger_Data import get_data, ProblemConfig
from types import SimpleNamespace
from time import sleep
import os

api = Flask('API')

@api.route('/')
def hello():
    return 'This is API.'

@api.route('/ping')
def ping():
    return '0'

def make_result_list(result: JudgerResult):
    result_list = [result.Status._value_, int(result.Score), result.MemUsed / 1024, result.TimeUsed]
    for i in range(0, len(result.Config.Groups)):
        group, minScore = result.Config.Groups[i], 0
        if len(group.TestPoints) != 0:
            minScore = result.Details[group.TestPoints[0] - 1].score
            for testPoint in group.TestPoints:
                minScore = min(minScore, result.Details[testPoint - 1].score)
        group_list = [result.Config.Groups[i].GroupID, result.Config.Groups[i].GroupName, 0, int(result.Config.Groups[i].GroupScore * minScore)]
        group_result = ResultType.AC
        for j in range(0, len(result.Config.Groups[i].TestPoints)):
            testcase = result.Details[result.Config.Groups[i].TestPoints[j] - 1]
            group_list.append([testcase.ID, testcase.result._value_, testcase.memory / 1024, testcase.time, testcase.disk, testcase.message])
            if group_result == ResultType.AC and testcase.result != ResultType.AC:
                group_result = testcase.result
        group_list[2] = group_result._value_
        result_list.append(group_list)
    return result_list

# guaranteed that only single judge will be invoked at the same time
@api.route('/judge', methods = ['POST'])
def judge():
    Server_Secret, Judge_ID = request.form.get('Server_Secret'), request.form.get('Judge_ID')
    if Master_Server_Secret != Server_Secret:
        return '-1'
    else:
        newpid = os.fork()
        if newpid == 0:
            return '0'
    judgepid = os.fork()
    if judgepid == 0:
        open(busyFlag, 'w').close()
        try:
            problemConfig, dataPath = get_data(DataConfig, request.form.get('Problem_ID'))
        except Exception as e:
            result = JudgerResult(ResultType.SYSERR, 0, 0, 0, [DetailResult(0, ResultType.SYSERR, 0, 0, 0, -1, "Error occurred during fetching data: " + str(e))], ProblemConfig([], [], 0, 0, 0))
            timestampFile = DataConfig.cache_dir + '/' + request.form.get('Problem_ID') + '.timestamp'
            if os.path.exists(timestampFile):
                os.remove(timestampFile)
        else:
            try:
                result = judgeManager.judge(problemConfig, dataPath, request.form.get('Lang'), request.form.get('Code'))
            except Exception as e:
                print(e)
                result = JudgerResult(ResultType.SYSERR, 0, 0, 0, [DetailResult(testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, "Error occurred during judging.") for testcase in problemConfig.Details], problemConfig)
        #print(result.Status)
        resultlist = make_result_list(result)
        msg = {'Server_Secret': My_Web_Server_Secret, 'Judge_ID': Judge_ID}
        msg['Result'] = json.dumps(resultlist)
        while True:
            try:
                re = requests.post(Web_Server + '/pushResult', data = msg).content.decode()
            except:
                re = '-1'
            if re == '0':
                break
            sleep(Judge_Result_Resend_Period / 1000)
        os.remove(busyFlag)
        return '0'
    os.waitpid(newpid, 0)
    os.waitpid(judgepid, 0)
    return '0'

@api.route('/isBusy', methods = ['POST'])
def isBusy():
    if request.form.get('Server_Secret') != Master_Server_Secret:
        return '-1'
    elif os.path.exists(busyFlag):
        return '1'
    else:
        return '0'
