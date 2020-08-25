from flask import Flask, request
from judgeServerManager import JudgeServer_Manager
from utils import *


api = Flask('API')

@api.route('/')
def Hello():
    return 'This is API'

@api.route('/heartBeat')
def heartBeat():
    Secret = request.form.get("Server_Secret")
    if Secret == None:
        return '-1'
    if not JudgeServer_Manager.Check_Secret(Secret):
        return '-1'
    JudgeServer_Manager.Flush_Heartbeat(Secret, UnixNano())
    return '0'

@api.route('/pushResult')
def pushResult():
    Secret = request.form.get("Server_Secret")
    if Secret == None:
        return '-1'
    Judge_ID = request.form.get("Judge_ID")
    Result = request.form.get("Result")
    # todo: save result
    return '0'


