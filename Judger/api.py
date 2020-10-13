from flask import Flask, request
import requests
import json
from Judger.judgeManager import judgeManager
from Judger.JudgerResult import *
from Judger.config import *
from Judger.Judger_Data import get_data
from types import SimpleNamespace
from time import sleep
import os

api = Flask('API')

@api.route('/')
def hello():
    return 'This is API.'

def make_result_list(result: JudgerResult):
    total_result = ResultType.AC
    result_list = [0, int(result.Score), result.MemUsed, result.TimeUsed]
    for i in range(0, len(result.Config.Groups)):
        group_list = [result.Config.Groups[i].GroupID, result.Config.Groups[i].GroupName, int(result.Config.Groups[i].GroupScore)]
        group_result = ResultType.AC
        for j in range(0, len(result.Config.Groups[i].TestPoints)):
            testcase = result.Details[result.Config.Groups[i].TestPoints[j] - 1]
            group_list.append([testcase.ID, testcase.result, testcase.memory, testcase.time, testcase.disk, testcase.message])
            if group_result == ResultType.AC and testcase.result != ResultType.AC:
                group_result = testcase.result
        result_list.append(group_list)
        if total_result == ResultType.AC and group_result != ResultType.AC:
            total_result = group_result
    result_list[0] = total_result
    return result_list

@api.route('/judge', methods = ['POST'])
def judge():
    Server_Secret, Judge_ID = request.form.get('Server_Secret'), request.form.get('Judge_ID')
    if Master_Server_Secret != Server_Secret:
        return '-1'
    else:
        newpid = os.fork()
        if newpid != 0:
            return '0'
    try:
        problemConfig, dataPath = get_data(DataConfig, request.form.get('Problem_ID'))
        result = judgeManager.judge(problemConfig, dataPath, request.form.get('Lang'), request.form.get('Code'))
    except:
        result = JudgerResult(ResultType.SYSERR, 0, 0, 0, [[testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, "Error occurred during fetching data."] for testcase in problemConfig.Details], problemConfig)
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
    os._exit(0)

@api.route('/isBusy', methods = ['POST'])
def isBusy():
    if request.form.get['Server_Secret'] != Web_Server_Secret:
        return '-1'
    elif judgeManager.isJudging():
        return '1'
    else:
        return '0'