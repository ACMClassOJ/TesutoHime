from Judger_Core import config as conf
from abc import abstractmethod

class CompilerInterface:
    @abstractmethod
    def CompileInstance(self, code_config : conf.CompilationConfig) -> conf.CompilationResult: pass
    