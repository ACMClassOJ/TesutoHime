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
        self.cpp_header = '''
#include <stdio.h>
#include <seccomp.h>
class {a} {{
public:
    {a}() {{
        scmp_filter_ctx ctx;
        ctx = seccomp_init(SCMP_ACT_KILL);
        int syscalls_whitelist[] = {{SCMP_SYS(read), SCMP_SYS(fstat),
                                SCMP_SYS(mmap), SCMP_SYS(mprotect),
                                SCMP_SYS(munmap), SCMP_SYS(uname),
                                SCMP_SYS(arch_prctl), SCMP_SYS(brk),
                                SCMP_SYS(access), SCMP_SYS(exit_group),
                                SCMP_SYS(close), SCMP_SYS(readlink),
                                SCMP_SYS(sysinfo), SCMP_SYS(write),
                                SCMP_SYS(writev), SCMP_SYS(lseek),
                                SCMP_SYS(clock_gettime), SCMP_SYS(open),
                                SCMP_SYS(dup), SCMP_SYS(dup2), SCMP_SYS(dup3)}};
        int syscalls_whitelist_length = sizeof(syscalls_whitelist) / sizeof(int);                            
        for (int i = 0; i < syscalls_whitelist_length; i++) 
            seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscalls_whitelist[i], 0);
        seccomp_load(ctx);        
    }}
}} _{a};             
'''

    def compile_cpp(self, code : str, timeLimit):
        msg     = ""
        path    = self.path
        program = "".join(random.sample(string.ascii_letters, 10))
        source  = program + ".cpp"

        className = "".join(random.sample(string.ascii_letters, 10))
        #code = code + self.cpp_header.format(a=className)

        try:
            codeFile = open(os.path.join(path, source), "w")
            codeFile.write(code)
            codeFile.close()
        except IOError:
            print("Compiler:", "faild to open the file")
        except Exception as e:
            print(e)
            return CompilationResult(
                compiled=False,
                msg="Unknown Error!",
                programPath="")

        try:
            print("Compiling...", end="")
            process = subprocess.run(
                ["g++", os.path.join(path, source), "-o", os.path.join(path, program), "-fmax-errors=10", "-lseccomp", "-O2", "-DONLINE_JUDGE", "-lm"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeLimit)
        except subprocess.TimeoutExpired:
            return CompilationResult(
                compiled=False,
                msg="Compile Time Out!",
                programPath="")
        except Exception as e:
            print(e)
            return CompilationResult(
                compiled=False,
                msg="Unknown Error!",
                programPath="")
        else:
            print("Done.")

        if process:
            msg += process.stderr.decode() + "\n"
            msg += process.stdout.decode() + "\n"

        msg = msg.replace(program, "main")
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

        try:
            print("Cloning...", end="")
            process = subprocess.run(
                ["git", "clone", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeLimit / 1000,
                cwd=path)
        except subprocess.TimeoutExpired:
            return CompilationResult(
                compiled=False,
                msg="Download Time Out!",
                programPath="")
        except Exception as e:
            print(e)
            return CompilationResult(
                compiled=False,
                msg="Unknown Error!",
                programPath="")
        else:
            print("Done.")

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
        print("Compiling...", end="")
        if "CMakeLists.txt" in os.listdir(os.path.join(path, project)):
            try:
                process = subprocess.run(
                    ["cmake", "CMakeLists.txt"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.join(path, project),
                    timeout=timeLimit)
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
                cwd=os.path.join(path, project),
                timeout=timeLimit)
        except subprocess.TimeoutExpired:
            return CompilationResult(
                compiled=False,
                msg=msg,
                programPath="")
        except Exception as e:
            print(e)
            return CompilationResult(
                compiled=False,
                msg="Unknown Error!",
                programPath="")
        else:
            print("Done.")
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
        try:
            if os.path.exists(path):
                shutil.rmtree(path, onerror=readonly_handler)
        except Exception as e:
            print(e)
        os.mkdir(path)

    def CompileInstance(self, code_config : CompilationConfig):
        sourceCode  = code_config.sourceCode
        language    = code_config.language
        timeLimit   = code_config.compileTimeLimit / 1000.0
        self.clear()
        if language == "c++" or language == "cpp":
            return self.compile_cpp(sourceCode, timeLimit)
        elif language == "git":
            return self.compile_git(sourceCode, timeLimit)
        else:
            return CompilationResult(
                compiled    = False, 
                msg         = "The language '" + language + "' is not supported now!",
                programPath = "")

compiler = Compiler()
