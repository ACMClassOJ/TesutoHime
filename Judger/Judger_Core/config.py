from util import work_file

outputFilePath = work_file('output.txt')

class CompilationConfig:
    def __init__(self,
                 sourceCode, # str for single code / dict for several files { file_name : source_code }
                 language: str,
                 compileTimeLimit: int,
                 sandboxOn: bool
                 ):
        self.sourceCode = sourceCode
        self.language = language
        self.compileTimeLimit = compileTimeLimit
        self.sandboxOn = sandboxOn

class TestPointConfig:
    def __init__(self,
                 language: str,
                 programPath: str, # when traditional problem
                 userOutputFile, # when uploading problem
                 inputFile: str,
                 timeLimit: int,
                 memoryLimit: int,
                 diskLimit: int, # 0 if not need
                 fileNumberLimit: int, # -1 if not need
                 valgrindTestOn: bool, # true if need checking memory leak
                 ):
        self.language = language
        self.programPath = programPath
        self.userOutputFile = userOutputFile
        self.inputFile = inputFile
        self.timeLimit = timeLimit
        self.memoryLimit = memoryLimit
        self.diskLimit = diskLimit
        self.fileNumberLimit = fileNumberLimit
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

