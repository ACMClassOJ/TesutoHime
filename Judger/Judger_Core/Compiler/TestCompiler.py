from .Compiler import compiler
from ..config import CompilationConfig
class TestCompiler:
    def test_cpp(self):
        print(compiler.CompileInstance(CompilationConfig(
            sourceCode=open("./Judger/Judger_Core/Compiler/test/test.cpp").read(),
            language="c++",
            compileTimeLimit=10000)).msg)
    def test_git(self):
        result = compiler.CompileInstance(CompilationConfig(
            sourceCode="https://github.com/Anoxiacxy/RISC-V.git",
            language="git",
            compileTimeLimit=30000))
        #print(result.compiled)
        print(result.msg)
        #print(result.programPath)
#TestCompiler().test_cpp()
TestCompiler().test_git()