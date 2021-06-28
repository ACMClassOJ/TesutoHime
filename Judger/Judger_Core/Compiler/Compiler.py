from ..compiler_interface import CompilerInterface
from ..config import CompilationConfig, CompilationResult
from .compile_util import readonly_handler
from .compile_const import WORK_DIR
from .compile_cpp import compile_cpp
from .compile_git import compile_git
from .compile_verilog import compile_verilog
from ...util import log # cxy 2021 6 28
import os
import shutil

class Compiler(CompilerInterface):
    @staticmethod
    def compile_verilog(code, time_limit):
        log.info("Start Compiling.")
        result = compile_verilog(code.copy(), time_limit)
        log.info("Done.")
        return result

    @staticmethod
    def compile_cpp(code, time_limit):
        log.info("Start Compiling.")
        if type(code) is str:
            code = {"main.cpp": code}
        result = compile_cpp(code.copy(), time_limit)
        log.info("Done.")
        return result

    @staticmethod
    def compile_git(url, time_limit):
        log.info("Start Compiling.")
        if type(url) is dict:
            try:
                url = url["main.cpp"]
            except Exception as e:
                log.error(str(e))
                raise
        result = compile_git(url, time_limit)
        log.info("Done.")
        return result

    @staticmethod
    def clear():
        path = WORK_DIR
        try:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=readonly_handler)
        except Exception as e:
            log.error(str(e))
        os.mkdir(path)

    def CompileInstance(self, code_config: CompilationConfig):
        source_code = code_config.sourceCode
        language = code_config.language
        time_limit = code_config.compileTimeLimit / 1000.0
        Compiler.clear()
        if language == "c++" or language == "cpp":
            return self.compile_cpp(source_code, time_limit)
        elif language == "git":
            return self.compile_git(source_code, time_limit)
        elif language == "verilog":
            return self.compile_verilog(source_code, time_limit)
        else:
            return CompilationResult(
                compiled=False,
                msg="The language '" + language + "' is not supported now!",
                programPath="")


compiler = Compiler()
