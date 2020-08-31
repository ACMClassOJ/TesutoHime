from typing import List

class ProblemConfig:
    class Group:
        def __init__(self,
                     GroupID: int,  # id 为 1-base
                     GroupName: str,
                     GroupScore,  # int / float
                     TestPoints: List[int]
                     ):
            self.GroupID = GroupID
            self.GroupName = GroupName
            self.GroupScore = GroupScore
            self.TestPoints = TestPoints

    class Detail:
        def __init__(self,
                     ID: int,  # id 为 1-base
                     Dependency: int,  # dependency为依赖测试，当且仅当dependency正常评测，才正常评测当前测试点。
                     TimeLimit: int,  # ms
                     MemoryLimit: int,  # KB
                     DiskLimit: int,  # KB 0表示不进行磁盘测试，无磁盘大小限制
                     ValgrindTestOn: bool,
                     ):
            self.ID = ID
            self.Dependency = Dependency
            self.TimeLimit = TimeLimit
            self.MemoryLimit = MemoryLimit
            self.DiskLimit = DiskLimit
            self.ValgrindTestOn = ValgrindTestOn

    def __init__(self,
                 Groups: list, #[Group]
                 Details: list, #[Detail]
                 CompileTimeLimit: int,  # ms
                 SPJ: int,  # 0/1 default spj, 2 custom spj
                 Scorer: int  # 0 default scorer, 1 custom scorer
                 ):
        self.Groups = Groups
        self.Details = Details
        self.CompileTimeLimit = CompileTimeLimit
        self.SPJ = SPJ
        self.Scorer = Scorer
