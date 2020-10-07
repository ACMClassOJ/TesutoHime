from flask import Flask, request
from Judger.config import *
from Judger.judgeManager import judgeManager

isBusy_api = Flask('API')

@isBusy_api.route('/')
def hello():
    return 'This is API.'

@isBusy_api.route('/isBusy', methods = ['POST'])
def isBusy():
    if request.form.get['Server_Secret'] != Web_Server_Secret:
        return '-1'
    elif judgeManager.isJudging():
        return '1'
    else:
        return '0'