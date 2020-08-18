class DataConfig:
    '''
        Used as config for every test point.
        Stored by file server and saved in the directory of the same test point.
        Judge server will parse it.
    '''

    def __init__(self,
                 configVersion: int,
                 ID: str,
                 timeLimit: int,
                 memoryLimit: int,
                 compileTimeLimit: int,
                 diskLimit: int,
                 fullScore: int,
                 judger: str
                 ):
        self.version = configVersion
        self.ID = ID
        self.timeLimit = timeLimit  # ms
        self.memoryLimit = memoryLimit  # kb
        self.compileTimeLimit = compileTimeLimit  # ms
        self.diskLimit = diskLimit  # kb
        self.fullScore = fullScore
        self.judger = judger  # get score by passing or by reading outputs of custom judger


class SubmitRequest:
    '''
        Used as config of every single submit.
        Sent by web server to judge server.
        Judge server will parse it.
    '''

    def __init__(self,
                 ID: str,
                 submitID: str,
                 language: str,
                 SPJ: str,
                 sourceCode: str,
                 auth:bytes):
        self.ID = ID  # Used for get data.zip from file server
        self.submitID = submitID
        # language: e.g. cmake,c++14,c++20,submitAnswer,c++Interactive...
        self.language = language
        self.SPJ = SPJ
        self.sourceCode = sourceCode
        self.auth=auth # as authorization


class TestPointStatus:
    def __init__(self,name:str,status:str,score:int,msg:str,timeUsage:int,memUsage:int,diskUsage:int):
        self.name=name
        self.stat=status
        self.score=score
        self.msg=msg
        self.time=timeUsage
        self.mem=memUsage
        self.disk=diskUsage

class JudgeResponse:
    '''
        Used as response of every single submit.
        Sent by judge server to web server.
        Web server will parse it.
    '''

    def __init__(self,
                 submitID:str,
                 status: str,
                 totalScore: int,
                 pointwiseStatus:list,
                 auth:bytes
                 ):
        self.submitID=submitID
        self.status=status
        self.totalScore=totalScore
        self.pointwiseStatus=pointwiseStatus # list of TestPointStatus
        self.auth=auth
