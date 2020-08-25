from utils import *
import requests
from judgeServerManager import JudgeServer_Manager
from judgeManager import Judge_Manager
from config import JudgeConfig

class JudgeServer_Scheduler:
    def Heart_Beat(self, Secret) -> bool:
        if not JudgeServer_Manager.Check_Secret(Secret):
            return False
        JudgeServer_Manager.Flush_Heartbeat(Secret, UnixNano())
        return True

    def Check_Queue(self):
        Server = JudgeServer_Manager.Get_Standby_Server()
        if Server == None:
            return
        Record = Judge_Manager.Get_Pending_Judge() # ID, Problem_ID, Code, Language
        if Record == None:
            return
        data = {}
        data['Server_Secret'] = JudgeConfig.Web_Server_Secret
        data['Problem_ID'] = str(Record[1])
        data['Judge_ID'] = str(Record[0])
        data['Lang'] = 'C++' if Record[3] == 'cpp' else 'Git'
        data['Code'] = Record[2]
        for i in range(0, 3):
            re = requests.post(Server[0], data = data) # todo: check self-signed SSL
            if re == '0':
                Judge_Manager.Update_Status(int(Record[0]), 'JU')
                JudgeServer_Manager.Flush_Busy(Server[1], True)
                break
        return

    def Start_Judge(self, Problem_ID, User, Code, Lang):
        Judge_Manager.Add_Judge(Code, User, Problem_ID, Lang, UnixNano())
        self.Check_Queue()
        return

    def Receive_Judge_Result(self, Secret: str, Judge_ID: int, Result: str):
        JudgeServer_Manager.Flush_Busy(Secret, False)
        # todo: read result and store it into Judge Database
        return
