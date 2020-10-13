from flask import Flask, request, Blueprint
from judgeServerManager import JudgeServer_Manager
from judgeServerScheduler import JudgeServer_Scheduler
from utils import *
import json

api = Blueprint('api', __name__, static_folder='static')

@api.route('/')
def Hello():
    return 'This is API For Judge Server, DO NOT VISIT THIS PAGE IN YOUR WEB BROWSER!'

@api.route('/heartBeat', methods=['POST'])
def heartBeat():
    Secret = request.form.get("Server_Secret")
    if Secret == None:
        return '-1'
    if not JudgeServer_Manager.Check_Secret(Secret):
        return '-1'
    JudgeServer_Manager.Flush_Heartbeat(Secret, UnixNano())
    JudgeServer_Scheduler.Check_Queue()
    return '0'

@api.route('/pushResult', methods=['POST'])
def pushResult():
    Secret = request.form.get("Server_Secret")
    if Secret == None:
        return '-1'
    Judge_ID = request.form.get("Judge_ID")
    print(Judge_ID)
    Result = request.form.get("Result")
    print('Arg = ', Judge_ID, 'Result = ', Result)
    JudgeServer_Scheduler.Receive_Judge_Result(Secret, Judge_ID, Result)
    return '0'


