from utils import *
import requests
from judgeServerManager import JudgeServer_Manager
from judgeManager import Judge_Manager
from config import JudgeConfig
import json
from types import SimpleNamespace

class JudgeServerScheduler:
    def Heart_Beat(self, Secret) -> bool:
        self.Check_System_Error()

        if not JudgeServer_Manager.Check_Secret(Secret):
            return False
        JudgeServer_Manager.Flush_Heartbeat(Secret, UnixNano())
        return True

    def Check_Queue(self): # todo: debug
        self.Check_System_Error()

        Server = JudgeServer_Manager.Get_Standby_Server(UnixNano() - JudgeConfig.Max_Duration)
        if Server == None or len(Server) == 0: # no avaliable server
            return
        Record = Judge_Manager.Get_Pending_Judge() # ID, Problem_ID, Code, Language
        if Record == None or len(Record) == 0:
            return
        data = {}
        data['Server_Secret'] = JudgeConfig.Web_Server_Secret
        data['Problem_ID'] = str(Record[1])
        data['Judge_ID'] = str(Record[0])
        data['Lang'] = 'cpp' if int(Record[3]) == 0 else 'git'
        data['Code'] = Record[2]
        for i in range(0, 3):
            re = requests.post(Server[0], data = data).content.decode() # Fixme: check self-signed SSL
            if re == '0':
                Judge_Manager.Update_Status(int(Record[0]), 1)
                JudgeServer_Manager.Flush_Busy(Server[1], True, int(Record[0]))
                break
        return

    def Start_Judge(self, Problem_ID, User, Code, Lang):
        self.Check_System_Error()

        Judge_Manager.Add_Judge(Code, User, Problem_ID, Lang, UnixNano())
        self.Check_Queue()
        return

    def Receive_Judge_Result(self, Secret: str, Judge_ID: int, Result: str):
        self.Check_System_Error()

        JudgeServer_Manager.Flush_Busy(Secret, False)
        x = json.loads(Result, object_hook=lambda d: SimpleNamespace(**d))
        Judge_Manager.Update_After_Judge(Judge_ID, int(x.Status), x.Score, Result, x.TimeUsed, x.MemUsed)
        JudgeServer_Manager.Flush_Busy(Secret, False)
        JudgeServer_Manager
        self.Check_Queue()
        return

    def Check_System_Error(self):
        failure = JudgeServer_Manager.Get_Failure_Task()
        if failure == None:
            return
        for x in failure:
            Judge_Manager.Update_Status(x, 10)
        return


JudgeServer_Scheduler = JudgeServerScheduler()