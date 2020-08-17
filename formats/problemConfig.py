class ProblemConfig:
    def __init__(self,
                 configVersion: int,
                 ID: str,
                 language:str,
                 SPJ:str,
                 timeLimit:int,
                 memoryLimit:int,
                 compileTimeLimit:int,
                 diskLimit:int
                 ):
        self.version = configVersion
        self.ID = ID
        self.language=language  # e.g. cmake,c++14,c++20,submitAnswer...
        self.SPJ=SPJ
        self.timeLimit=timeLimit
        self.memoryLimit=memoryLimit
        self.compileTimeLimit=compileTimeLimit
        self.diskLimit=diskLimit
        
