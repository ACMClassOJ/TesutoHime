from Judger.Judger_Core.compiler_interface import CompilerInterface
from Judger.Judger_Core.config import CompilationConfig, CompilationResult
import subprocess

class Compiler(CompilerInterface):
    def compile_cpp(self, code : str, timeLimit):
        codeFile = open("compiler/source_code.cpp", "w")
        codeFile.write(code)
        codeFile.close()
        process = subprocess.run(
            ["g++", "compiler/source_code.cpp"], 
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            timeout = timeLimit / 1000)
        if process.returncode != 0:
            return CompilationResult(
                compiled    = False,    
                msg         = process.stderr.decode(),
                programPath = "")
        
        process = subprocess.run(
            ["g++", "compiler/source_code.cpp", "-E"], 
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            timeout = timeLimit / 1000)
        
    def compile_git(self, url, timeLimit):
        
        pass

    def CompileInstance(self, code_config):
        sourceCode  = code_config.sourceCode
        language    = code_config.language
        timeLimit   = code_config.compileTimeLimit
        if language == "c++":
            return self.compile_cpp(sourceCode, timeLimit)
        elif language == "git":
            return self.compile_git(sourceCode, timeLimit)
        else:
            return CompilationResult(
                compiled    = False, 
                msg         = "暂不支持用" + language + "语言提交",
                programPath = "")

compiler = Compiler()