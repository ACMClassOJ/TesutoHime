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
                 inputFile: str,
                 timeLimit: int,
                 memoryLimit: int,
                 diskLimit: int, # -1 if not need
                 diskClearTag: bool, # true if need clearing
                 valgrindTestOn: bool, # true if need checking memory leak
                 ):
        self.programPath = programPath
        self.userOutputFile = userOutputFile
        self.inputFile = inputFile
        self.timeLimit = timeLimit
        self.memoryLimit = memoryLimit
        self.diskLimit = diskLimit
        self.diskClearTag = diskClearTag
        self.valgrindTestOn = valgrindTestOn

class CompilationResult:
    def __init__(self,
                 compiled: bool,
                 msg: str,
                 programPath: str
                 ):
        self.compiled = compiled
        self.msg = msg
        self.programPath = programPath

