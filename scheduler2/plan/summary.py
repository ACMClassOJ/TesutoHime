from typing import Dict, Optional

from commons.task_typing import (JudgePlan, JudgePlanSummary, SubtaskSummary,
                                 TestpointSummary)


def summarize(plan: JudgePlan) -> Optional[JudgePlanSummary]:
    if plan.quiz is not None:
        return None
    testpoint_map: Dict[str, TestpointSummary] = {}
    for testpoint in (t for task in plan.judge for t in task.task.testpoints):
        limits = testpoint.run.limits if testpoint.run is not None else None
        testpoint_map[testpoint.id] = TestpointSummary(testpoint.id, limits)
    subtasks = []
    for group in plan.score:
        testpoints = [testpoint_map[x] for x in group.testpoints]
        subtasks.append(SubtaskSummary(group.id, group.name, testpoints, group.score))
    return JudgePlanSummary(subtasks)
