from Judger.Judger_Core.Compiler.Compiler import compiler
from Judger.Judger_Core.config import CompilationConfig
class TestCompiler:
    def test(self):
        compiler.CompilerInstance(CompilationConfig(
            sourceCode=open(),
            language="c++",


        ))