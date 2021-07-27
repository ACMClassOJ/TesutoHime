from .Compiler import compiler
from ..config import CompilationConfig
class TestCompiler:
    def test_cpp(self):
        print(compiler.CompileInstance(CompilationConfig(
            sourceCode={"main.cpp" : open("./Judger_Core/Compiler/test/test1.cpp").read()},
            language="c++",
            compileTimeLimit=10000,
            sandboxOn=False)).msg)
    def test_hpp(self):
        print(compiler.CompileInstance(CompilationConfig(
            sourceCode={"main.cpp": open("./Judger_Core/Compiler/test/test2.cpp").read(),
                        "header.hpp": open("./Judger_Core/Compiler/test/header.hpp").read() },
            language="c++",
            compileTimeLimit=10000)).msg)
    def test_git(self):
        result = compiler.CompileInstance(CompilationConfig(
            sourceCode="https://github.com/acrazyczy/aplusb.git",
            language="git",
            compileTimeLimit=30000))
        #print(result.compiled)
        print(result.msg)
        #print(result.programPath)
#TestCompiler().test_hpp()
    def test_verilog(self):
        result = compiler.CompileInstance(CompilationConfig(
            sourceCode={
                "test.v":open("./Judger/Judger_Core/Compiler/test.v").read(),
                "notgate.v":open("./Judger/Judger_Core/Compiler/notgate.v").read()
            },
            language="verilog",
            compileTimeLimit=30000))
        #print(result.compiled)
        print(result.msg)

TestCompiler().test_cpp()