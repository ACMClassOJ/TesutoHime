from ..compiler_interface import CompilerInterface
from ..config import CompilationConfig, CompilationResult
from .cutil import readonly_handler
import subprocess
import os
import shutil
import random
import string

class Compiler(CompilerInterface):
    def __init__(self):
        self.path = "compiling"
        self.program = "code"

    def compile_cpp(self, code : str, timeLimit):
        msg     = ""
        path    = self.path
        program = "".join(random.sample(string.ascii_letters, 10))
        source  = program + ".cpp"

        codeFile = open(os.path.join(path, source), "w")
        codeFile.write(code)
        codeFile.close()
        print("Compiling...")
        try:
            process = subprocess.run(
                ["g++", os.path.join(path, source), "-o", os.path.join(path, program), "-fmax-errors=10"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeLimit / 1000)
        except subprocess.TimeoutExpired:
            return CompilationResult(
                compiled=False,
                msg="Compile Time Out!",
                programPath="")
        if process:
            msg += process.stderr.decode() + "\n"
            msg += process.stdout.decode() + "\n"
        if not process or process.returncode != 0:
            return CompilationResult(
                compiled=False,
                msg=msg,
                programPath="")
        else:
            return CompilationResult(
                compiled=True,
                msg=msg+"Compile Success!",
                programPath=os.path.join(path, program))

    def compile_git(self, url : str, timeLimit):
        path    = self.path
        program = self.program
        msg     = ""
        print("Loading...")
        try:
            process = subprocess.run(
                ["git", "clone", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(20, timeLimit / 1000),
                cwd=path)
        except subprocess.TimeoutExpired:
            return CompilationResult(
                compiled=False,
                msg="Download Time Out!",
                programPath="")

        if process:
            msg += process.stderr.decode() + "\n"
            msg += process.stdout.decode() + "\n"

        if not process or process.returncode != 0:
            return CompilationResult(
                compiled=False,
                msg=msg,
                programPath="")

        project = process.stderr.decode()[14:-5]

        process = None
        print("Compiling...")
        if "CMakeLists.txt" in os.listdir(os.path.join(path, project)):
            try:
                process = subprocess.run(
                    ["cmake", "CMakeLists.txt"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.join(path, project))
            except subprocess.TimeoutExpired:
                pass
            if process:
                msg += process.stderr.decode() + "\n"
                msg += process.stdout.decode() + "\n"

        try:
            process = subprocess.run(
                ["make"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.join(path, project))
        except subprocess.TimeoutExpired:
            return CompilationResult(
                compiled=False,
                msg=msg,
                programPath="")
        if process:
            msg += process.stderr.decode() + "\n"
            msg += process.stdout.decode() + "\n"

        if not process or process.returncode != 0:
            return CompilationResult(
                compiled=False,
                msg=msg,
                programPath="")

        return CompilationResult(
                compiled=True,
                msg=msg+"Compile Success!",
                programPath=os.path.join(path, project, program))

    def clear(self):
        path = self.path
        if os.path.exists(path):
            shutil.rmtree(path, onerror=readonly_handler)
        os.mkdir(path)

    def CompileInstance(self, code_config : CompilationConfig):
        sourceCode  = code_config.sourceCode
        language    = code_config.language
        timeLimit   = code_config.compileTimeLimit
        self.clear()
        if language == "c++":
            return self.compile_cpp(sourceCode, timeLimit)
        elif language == "git":
            return self.compile_git(sourceCode, timeLimit)
        else:
            return CompilationResult(
                compiled    = False, 
                msg         = "The language '" + language + "' is not supported now!",
                programPath = "")

compiler = Compiler()