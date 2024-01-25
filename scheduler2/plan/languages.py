from typing import List, Optional

from commons.task_typing import CompileSourceVerilog, CompileTaskPlan, JudgePlan


# A bunch of heuristics; really ugly but there's no other choice.
def languages_accepted(plan: JudgePlan) -> Optional[List[str]]:
    languages = None
    has_compile_or_run = False
    if plan.compile is not None:
        has_compile_or_run = True
    if plan.judge is not None:
        for task in plan.judge:
            for tp in task.task.testpoints:
                # per-testpoint compiling is supported only for C++ and Verilog
                if isinstance(tp.input, CompileTaskPlan):
                    if isinstance(tp.input.source, CompileSourceVerilog):
                        return ['verilog']
                    return ['cpp']
                if tp.run is not None:
                    has_compile_or_run = True
                    if tp.run.type == 'verilog':
                        return ['verilog']
                    if tp.run.type == 'valgrind':
                        # Python and Verilog cannot run Valgrind
                        languages = ['cpp', 'git']
    if not has_compile_or_run:
        # SPJ 5, there is no point specifying a language
        return ['cpp']
    return languages
