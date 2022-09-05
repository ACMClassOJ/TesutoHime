from utils import *
import requests
from judgeServerManager import JudgeServer_Manager
from judgeManager import Judge_Manager
from config import JudgeConfig
import json
import redis_lock

class JudgeServerScheduler:
    def __init__(self):
        scheduler_lock = redis_lock.Lock(redis_connect(), RedisConfig.prefix + 'scheduler.lock')
        scheduler_lock.reset()

    def Heart_Beat(self, Secret) -> bool:
        self.Check_System_Error()

        if not JudgeServer_Manager.Check_Secret(Secret):
            return False
        JudgeServer_Manager.Flush_Heartbeat(Secret, unix_nano())
        return True

    def Check_Queue(self):
        self.Check_System_Error()

        scheduler_lock = redis_lock.Lock(redis_connect(), RedisConfig.prefix + 'scheduler.lock')
        scheduler_lock.acquire()

        Server = JudgeServer_Manager.Get_Standby_Server(unix_nano() - JudgeConfig.Max_Duration)
        # print(Server)
        if Server == None or len(Server) == 0: # no avaliable server
            scheduler_lock.release()
            return
        Record = Judge_Manager.get_pending_judge() # ID, Problem_ID, Code, Language
        if Record == None or len(Record) == 0:
            scheduler_lock.release()
            return
        data = {}
        data['Server_Secret'] = JudgeConfig.Web_Server_Secret
        data['Problem_ID'] = str(Record[1])
        data['Judge_ID'] = str(Record[0])
        lang_digit = int(Record[3])
        if lang_digit == 0:
            data['Lang'] = 'cpp'
        elif lang_digit == 1:
            data['Lang'] = 'git'
        elif lang_digit == 2:
            data['Lang'] = 'Verilog'
        elif lang_digit == 3:
            data['Lang'] = 'quiz'
        data['Code'] = Record[2]
        try:
            re = requests.post(Server[0] + '/judge', data = data, timeout = 5).content.decode()
            if re == '0':
                Judge_Manager.update_status(int(Record[0]), 1)
                JudgeServer_Manager.Flush_Busy(Server[1], True, int(Record[0]))
        except requests.exceptions.RequestException:
            pass
        scheduler_lock.release()
        return

    def Start_Judge(self, Problem_ID, User, Code, Lang, Share):
        self.Check_System_Error()

        id = Judge_Manager.add_judge(Code, User, Problem_ID, Lang, unix_nano(), Share)
        self.Check_Queue()
        return id

    def Start_Targeted_Judge(self, Problem_ID, User, Code, Lang, Share, Server_Friendly_Name):
        self.Check_System_Error()

        scheduler_lock = redis_lock.Lock(redis_connect(), RedisConfig.prefix + 'scheduler.lock')
        scheduler_lock.acquire()

        Server = JudgeServer_Manager.Get_Server_By_Friendly_Name(unix_nano() - JudgeConfig.Max_Duration, Server_Friendly_Name)

        if Server == None or len(Server) == 0:
            scheduler_lock.release()
            return -1
        
        Judge_Manager.add_judge(Code, User, Problem_ID, Lang, unix_nano(), Share)
        judge_id = Judge_Manager.max_id() # get max_id immediately
        judge_record = Judge_Manager.query_judge(judge_id)

        if not (judge_record['User'] == User and judge_record['Problem_ID'] == Problem_ID and 
                judge_record['Code'] == Code and judge_record['Lang'] == Lang and judge_record['Share'] == Share):
            Judge_Manager.delete_judge(judge_id)
            return -2
        
        data = {}
        data['Server_Secret'] = JudgeConfig.Web_Server_Secret
        data['Problem_ID'] = Problem_ID
        data['Judge_ID'] = judge_id
        lang_digit = Lang
        if lang_digit == 0:
            data['Lang'] = 'cpp'
        elif lang_digit == 1:
            data['Lang'] = 'git'
        elif lang_digit == 2:
            data['Lang'] = 'Verilog'
        elif lang_digit == 3:
            data['Lang'] = 'quiz'
        data['Code'] = Code
        try:
            re = requests.post(Server[0] + '/judge', data = data, timeout = 5).content.decode()
            if re == '0':
                Judge_Manager.update_status(judge_id, 1)
                JudgeServer_Manager.Flush_Busy(Server[1], True, judge_id)
        except requests.exceptions.RequestException:
            pass
        
        scheduler_lock.release()
        return 0


    def ReJudge(self, Judge_ID):
        self.Check_System_Error()

        Judge_Manager.update_status(Judge_ID, 0)
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
        # print(x[0])
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
