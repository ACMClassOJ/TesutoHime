class CompilationConfig:
    def __init__(self,
                 sourceCode: str,
                 language: str,
                 compileTimeLimit: int
                 ):
        self.sourceCode = sourceCode
        self.language = language
        self.compileTimeLimit = compileTimeLimit

class TestPointConfig:
    def __init__(self,
                 programPath: str, # when traditional problem
                 userOutputFile, # when uploading problem
                 inputFile,
                 outputFile,
                 timeLimit: int,
                 memoryLimit: int,
                 diskLimit: int, # -1 if not need
                 diskClearTag: bool, # true if need clearing
                 SPJ: str # path of executable file
                 ):
        self.programPath = programPath
        self.userOutputFile = userOutputFile
        self.inputFile = inputFile
        self.outputFile = outputFile
        self.timeLimit = timeLimit
        self.memoryLimit = memoryLimit
        self.diskLimit = diskLimit
        self.diskClearTag = diskClearTag
        self.SPJ = SPJ

class CompilationResult:
    def __init__(self,
                 compiled: bool,
                 msg: str,
                 programPath: str
                 ):
        self.compiled = compiled
        self.msg = msg
        self.programPath = programPath

class JudgeTestPointResult:
    def __init__(self,
                 status : str,
                 score  : int,
                 msg    : str,
                 timeUsage : int,
                 memUsage  : int,
                 diskUsage : int
                 ):
        self.stat   = status    # Accepted / Wrong Anaswe / Compile Error / Skip / ...
        self.score  = score    # 
        self.msg    = msg        # meg offered by spj
        self.time   = timeUsage # ms
        self.mem    = memUsage   # kb
        self.disk   = diskUsage # kb

