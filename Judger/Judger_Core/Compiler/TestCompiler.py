from .Compiler import compiler
from ..config import CompilationConfig
class TestCompiler:
    def test_cpp(self):
        print(compiler.CompileInstance(CompilationConfig(
            sourceCode={"main.cpp" : open("./Judger/Judger_Core/Compiler/test/test1.cpp").read()},
            language="c++",
            compileTimeLimit=10000)).msg)
    def test_hpp(self):
        print(compiler.CompileInstance(CompilationConfig(
            sourceCode={"main.cpp": open("./Judger/Judger_Core/Compiler/test/test2.cpp").read(),
                        "header.hpp": open("./Judger/Judger_Core/Compiler/test/header.hpp").read() },
            language="c++",
            compileTimeLimit=10000)).msg)
    def test_git(self):
        result = compiler.CompileInstance(CompilationConfig(
            sourceCode="https://github.com/acrazyczy/RISC-V-Simulator.git",
            language="git",
            compileTimeLimit=30000))
        #print(result.compiled)
        print(result.msg)
        #print(result.programPath)
#TestCompiler().test_hpp()
TestCompiler().test_git()