class ProblemTestPointConfig:
    def __init__(self,
                 inputFile : file_pointer,
                 outputFile : file_pointer,
                 timeLimit : int,
                 memoryLimit : int,
                 diskLimit : int):
        self.inputFile = inputFile  # file pointer = open("filename")
        self.outputFile = outputFile # file pointer   
        self.timeLimit = timeLimit  # ms
        self.memoryLimit = memoryLimit  # kb    
        self.diskLimit = diskLimit  # kb

class ProblemConfig:
    def __init__(self,
                 sourceCode: str,
                 language: str,
                 compileTimeLimit : int,
                 testPoints : list_of_ProblemTestPointConfig,
                 SPJ: str):
        self.sourceCode = sourceCode
        self.language = language
        self.compileTimeLimit = compileTimeLimit  # ms
        self.testPoints = testPoints # list[ ProblemTestPointConfig ]
        self.SPJ = SPJ        

class JudgeCore:
    def __init__(self, problemConfig):
        self.problemConfig = problemConfig
    
    def judge(self) -> list_of_TestPointStatus:
        pass