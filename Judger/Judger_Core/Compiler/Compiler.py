from ..compiler_interface import CompilerInterface
from ..config import CompilationConfig, CompilationResult
from .compile_util import readonly_handler
from .compile_const import WORK_DIR
from .compile_cpp import compile_cpp
from .compile_git import compile_git
from .compile_verilog import compile_verilog
from ..util import log # cxy 2021 6 28
from config import Performance_Rate
import os
import shutil


class Compiler(CompilerInterface):
    @staticmethod
    def compile_verilog(code, time_limit, sandboxOn):
        log.info("Start Compiling.")
        if type(code) is str:
            code = {"test.v": code}
        result = compile_verilog(code.copy(), time_limit)
        #log.info("Done.")
        return result

    @staticmethod
    def compile_cpp(code, time_limit, sandboxOn):
        log.info("Start Compiling.")
        if type(code) is str:
            code = {"main.cpp": code}
        result = compile_cpp(code.copy(), time_limit)
        log.info("Done.")
        return result

    @staticmethod
    def compile_git(url, time_limit, sandboxOn):
        log.info("Start Compiling.")
        if type(url) is dict:
            try:
                url = url["main.cpp"]
            except Exception as e:
                log.error(str(e))
                raise
        result = compile_git(url, time_limit, sandboxOn)
        log.info("Done.")
        return result

    def clear(self):
        self.lastCompileConfig = None
        self.lastCompileResult = None
        path = WORK_DIR
        try:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=readonly_handler)
        except Exception as e:
            log.error(str(e))
            pass
        os.mkdir(path)

    def CompileInstance(self, code_config: CompilationConfig):
        source_code = code_config.sourceCode
        language = code_config.language
        time_limit = code_config.compileTimeLimit / 1000.0 * Performance_Rate

        if code_config == self.lastCompileConfig:
            log.info("Compiler: the same code we have already compiled, just return the last compilation result")
            return self.lastCompileResult

        self.clear()
        
        if language == "c++" or language == "cpp" or language == "C++":
            self.lastCompileConfig = code_config
            self.lastCompileResult = self.compile_cpp(source_code, time_limit, code_config.sandboxOn)
        elif language == "Verilog" or language == "verilog":
            self.lastCompileConfig = code_config
            self.lastCompileResult = self.compile_verilog(source_code, time_limit, code_config.sandboxOn)
        elif language == "git" or language == "Git":
            # git would change for every compilation
            self.lastCompileConfig = None
            self.lastCompileResult = None
            return self.compile_git(source_code, time_limit, code_config.sandboxOn)
        else:
            self.lastCompileConfig = None
            self.lastCompileResult = None
            return CompilationResult(
                compiled=False,
                msg="The language '" + language + "' is not supported now",
                programPath="")

        if self.lastCompileResult == None:
            log.error("Compiler: unknown error that cause the empty compilation result")

        return self.lastCompileResult            


compiler = Compiler()
