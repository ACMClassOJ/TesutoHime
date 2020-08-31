from flask import Flask, request
from Judger.judgeManager import judgeManager
from Judger.config import *
from Judger.Judger_Data import get_data
from Judger.JudgerResult import *

api = Flask('API')

@api.route('/')
def hello():
    return 'This is API.'

@api.route('/judge', methods = ['POST'])
def judge():
    Server_Secret = request.form.get['Server_Secret']
    if Web_Server_Secret != Server_Secret:
        return '-1'
    try:
        problemConfig, dataPath = get_data(DataConfig, request.form.get['Problem_ID'])
    except:
        return '-1'
    try:
        result = judgeManager.judge(problemConfig, dataPath, request.form.get['Lang'], request.form.get['Code'])
    except:
        return '-1'
    return result

@api.route('/isBusy', methods = ['POST'])
def isBusy():
    #to do: verify the Server_Secret