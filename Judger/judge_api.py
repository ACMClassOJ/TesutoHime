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

judge_api = Flask('API')

@judge_api.route('/')
def hello():
    return 'This is API.'

@judge_api.route('/judge', methods = ['POST'])
def judge():
    Server_Secret, Judge_ID = request.form.get('Server_Secret'), request.form.get('Judge_ID')
    if Web_Server_Secret != Server_Secret:
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
    msg = {'Server_Secret': Server_Secret, 'Judge_ID': Judge_ID}
    msg['Result'] = json.dumps(result, default=lambda o: getattr(o, '__dict__', str(o)))
    #print(msg['Result'])
    while True:
        try:
            re = requests.post(Web_Server + '/pushResult', data = msg).content.decode()
        except:
            re = '-1'
        if re == '0':
            break
        sleep(Judge_Result_Resend_Period / 1000)
    os._exit(0)