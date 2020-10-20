from utils import *
import requests
from judgeServerManager import JudgeServer_Manager
from judgeManager import Judge_Manager
from config import JudgeConfig
import json

class JudgeServerScheduler:
    def Heart_Beat(self, Secret) -> bool:
        self.Check_System_Error()

        if not JudgeServer_Manager.Check_Secret(Secret):
            return False
        JudgeServer_Manager.Flush_Heartbeat(Secret, UnixNano())
        return True

    def Check_Queue(self):
        self.Check_System_Error()

        Server = JudgeServer_Manager.Get_Standby_Server(UnixNano() - JudgeConfig.Max_Duration)
        print(Server)
        if Server == None or len(Server) == 0: # no avaliable server
            return
        Record = Judge_Manager.get_pending_judge() # ID, Problem_ID, Code, Language
        if Record == None or len(Record) == 0:
            return
        data = {}
        data['Server_Secret'] = JudgeConfig.Web_Server_Secret
        data['Problem_ID'] = str(Record[1])
        data['Judge_ID'] = str(Record[0])
        data['Lang'] = 'cpp' if int(Record[3]) == 0 else 'git'
        data['Code'] = Record[2]
        for i in range(0, 3):
            re = requests.post(Server[0] + '/judge', data = data).content.decode() # Fixme: check self-signed SSL
            if re == '0':
                Judge_Manager.update_status(int(Record[0]), 1)
                JudgeServer_Manager.Flush_Busy(Server[1], True, int(Record[0]))
                break
        return

    def Start_Judge(self, Problem_ID, User, Code, Lang, Share):
        self.Check_System_Error()

        Judge_Manager.add_judge(Code, User, Problem_ID, Lang, UnixNano(), Share)
        self.Check_Queue()
        return

    """
    [
        Problem_Status, Problem_Score, Mem_Used, Time_Used,
        [GroupID, GroupName, Group_Status, GroupScore, 
            [id, Status, Mem_Used, Time_Used. Disk_Used, Message]*
        ]*
    ]
    
    [9, 0, 0, 0, 
        [1, 'basic test', 33, 
            [1, 9, 0, 0, -1, 'Error occurred during fetching data.']], 
        [2, 'advanced test', 33, 
            [1, 9, 0, 0, -1, 'Error occurred during fetching data.'], 
            [2, 9, 0, 0, -1, 'Error occurred during fetching data.']], 
        [3, 'pressure test', 33, 
            [1, 9, 0, 0, -1, 'Error occurred during fetching data.'], 
            [3, 9, 0, 0, -1, 'Error occurred during fetching data.']]
    ]
    """

    def Receive_Judge_Result(self, Secret: str, Judge_ID: int, Result: str):
        self.Check_System_Error()

        JudgeServer_Manager.Flush_Busy(Secret, False)
        x = json.loads(Result)
        print(x[0])
        Judge_Manager.update_after_judge(Judge_ID, int(x[0]), x[1], Result, x[3], x[2])
        JudgeServer_Manager.Flush_Busy(Secret, False)
        self.Check_Queue()
        return

    def Check_System_Error(self):
        failure = JudgeServer_Manager.Get_Failure_Task()
        if failure == None:
            return
        for x in failure:
            Judge_Manager.update_status(x, 10)
        return


JudgeServer_Scheduler = JudgeServerScheduler()