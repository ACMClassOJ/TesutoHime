class ProblemSubtaskConfig:
    def __init__(self,
                 inputFiles : file_pointers,
                 outputFiles : file_pointers,
                 timeLimit : int,
                 memoryLimit : int,
                 diskLimit : int):
        self.inputFiles = inputFiles  # file pointer = open("filename")
        self.outputFiles = outputFiles # file pointer   
        self.timeLimit = timeLimit  # ms
        self.memoryLimit = memoryLimit  # kb    
        self.diskLimit = diskLimit  # kb        

class ProblemConfig:
    def __init__(self,
                 sourceCode: str,
                 language: str,
                 compileTimeLimit : int,
                 subtasks : list_of_ProblemSubtaskConfig,
                 SPJ: str):
        self.sourceCode = sourceCode
        self.language = language
        self.compileTimeLimit = compileTimeLimit  # ms
        self.subtasks = subtasks # list[ ProblemTestPointConfig ]
        self.SPJ = SPJ        

class JudgeTestPointResult:
    def __init__(self,
                 status : str,
                 score  : int,
                 msg    : str,
                 timeUsage : int,
                 memUsage  : int,
                 diskUsage : int
                 ):
        self.stat   = status    # Accepted / Wrong Answer / Compile Error / Skip / ...
        self.score  = score    # 
        self.msg    = msg        # msg offered by spj
        self.time   = timeUsage # ms
        self.mem    = memUsage   # kb
        self.disk   = diskUsage # kb

class JudgeSubtaskResult:
    def __init__(self,
                 testPoints : list_of_JudgeTestPointResult, 
                 status : str,
                 score  : int
                 ):
        self.testPoints = testPoints #
        self.stat   = status    # Accepted / Wrong Answer / Compile Error / Skipped / ...
        self.score  = score    # 

class JudgeResult:
    def __init__(self,
                 subtasks : list_of_JudgeSubtaskResult
                 ):
        self.subtasks = subtasks 

class JudgerCore:
    def __init__(self, problemConfig):
        self.problemConfig = problemConfig
    
    def judge(self) -> JudgeResult:
        pass