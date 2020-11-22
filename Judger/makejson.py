# This is a test program.

from JudgerResult import *
from Judger_Data.ProblemConfig import *
from types import SimpleNamespace
import json

def make_result_list(result: JudgerResult):
    total_result = ResultType.AC
    result_list = [0, int(result.Score), result.MemUsed, result.TimeUsed]
    for i in range(0, len(result.Config.Groups)):
        group_list = [result.Config.Groups[i].GroupID, result.Config.Groups[i].GroupName, int(result.Config.Groups[i].GroupScore)]
        group_result = ResultType.AC
        for j in range(0, len(result.Config.Groups[i].TestPoints)):
            testcase = result.Details[result.Config.Groups[i].TestPoints[j] - 1]
            group_list.append([testcase.ID, testcase.result, testcase.memory, testcase.time, testcase.disk, testcase.message])
            if group_result == ResultType.AC and testcase.result != ResultType.AC:
                group_result = testcase.result
        result_list.append(group_list)
        if total_result == ResultType.AC and group_result != ResultType.AC:
            total_result = group_result
    result_list[0] = total_result
    return result_list

def get_json(obj):
  return json.dumps(make_result_list(obj))

problemConfig = ProblemConfig([Group(1, 'basic test', 33.3, [1]), Group(2, 'advanced test', 33.3, [1, 2]), Group(3, 'pressure test', 33.3, [1, 3])], [Detail(1, 0, 1000, 512, 0, False), Detail(2, 1, 1000, 512, 0, False), Detail(3, 1, 1000, 512, 0, False)], 10000, 0, 0)
result = JudgerResult(ResultType.SYSERR._value_, 0, 0, 0, [DetailResult(testcase.ID, ResultType.SYSERR._value_, 0, 0, 0, -1, "Error occurred during fetching data.") for testcase in problemConfig.Details], problemConfig)
jsonResult = get_json(result)
print(jsonResult)
#print("Json = ", jsonResult)
#x = json.loads(jsonResult, object_hook=lambda d: SimpleNamespace(**d))
#print(x.Status._name_)