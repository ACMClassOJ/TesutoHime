import json
from config import *
import Judger_Data

a = Judger_Data.ProblemConfig(
    [Judger_Data.ProblemConfig.Group(1, '1', 10, [1, 2]), Judger_Data.ProblemConfig.Group(2, '2', 20, [1, 3])],
    [Judger_Data.ProblemConfig.Detail(1, 0, 1000, 1024, 0, False),
     Judger_Data.ProblemConfig.Detail(2, 1, 1000, 1024, 0, False),
     Judger_Data.ProblemConfig.Detail(3, 1, 1000, 1024, 0, False)],
    100, 0, 0)
print(json.dumps(a, indent=4, default=lambda x: x.__dict__))

b, c = Judger_Data.get_data(DataConfig, 1)
print(b)
print(c)
