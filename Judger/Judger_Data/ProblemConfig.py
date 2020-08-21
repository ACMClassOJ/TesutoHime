class ProblemConfig:
	def __init__(self,
		Groups, # : [[GroupID, GroupName, GroupScore, [List of TestPointID]]] id 为 1-base
		Details, # : [[ID, Dependency, TimeLimit, MemoryLimit, DiskLimit, ValgrindTestOn: bool]] 存储每个测试点的3项限制, dependency为依赖测试，当且仅当dependency正常评测，才正常评测当前测试点。id 为 1-base
		CompileTimeLimit : int, # ms
		DiskTestOn: bool,
		SPJ : int, # 0/1 default spj, 2 custom spj
		Scorer : int # 0 default scorer, 1 custom scorer
        ):
		self.Groups = Groups 
		self.Details = Details
		self.CompileTimeLimit = CompileTimeLimit
		self.DiskTestOn = DiskTestOn
		self.SPJ = SPJ
		self.Scorer = Scorer