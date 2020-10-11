from flask import Flask, request
import json
from Judger.judgeManager import judgeManager
from Judger.config import *
from Judger.Judger_Data import get_data

judge_api = Flask('API')

@judge_api.route('/')
def hello():
    return 'This is API.'

@judge_api.route('/judge', methods = ['POST'])
def judge():
    Server_Secret = request.form.get('Server_Secret')
    if Web_Server_Secret != Server_Secret:
        return '-1'
    try:
        problemConfig, dataPath = get_data(DataConfig, request.form.get('Problem_ID'))
    except:
        return '-2'
    try:
        result = judgeManager.judge(problemConfig, dataPath, request.form.get('Lang'), request.form.get('Code'))
    except Exception as e:
        print(e)
        return '-3'
    return json.loads(json.dumps(result, default=lambda o: getattr(o, '__dict__', str(o))))