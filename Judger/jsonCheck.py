from Judger.JudgerResult import *
from Judger.Judger_Data.ProblemConfig import *
from types import SimpleNamespace
import json

def get_json(obj):
  return json.dumps(obj, default=lambda o: getattr(o, '__dict__', str(o)))

problemConfig = ProblemConfig([Group(1, 'basic test', 33.3, [1]), Group(2, 'advanced test', 33.3, [1, 2]), Group(3, 'pressure test', 33.3, [1, 3])], [Detail(1, 0, 1000, 512, 0, False), Detail(2, 1, 1000, 512, 0, False), Detail(3, 1, 1000, 512, 0, False)], 10000, 0, 0)
result = JudgerResult(ResultType.SYSERR, 0, 0, 0, [DetailResult(testcase.ID, ResultType.SYSERR, 0, 0, 0, -1, "Error occurred during fetching data.") for testcase in problemConfig.Details], problemConfig)
jsonResult = get_json(result)
#print("Json = ", jsonResult)
x = json.loads(jsonResult, object_hook=lambda d: SimpleNamespace(**d))
print(x.Status._value_)