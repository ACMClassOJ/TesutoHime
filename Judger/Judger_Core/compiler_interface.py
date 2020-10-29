from abc import abstractmethod
from .config import CompilationConfig, CompilationResult

class CompilerInterface:
    @abstractmethod
    def CompileInstance(self, code_config: CompilationConfig) -> CompilationResult: pass
    