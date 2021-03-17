from .compile_const import *
from .compile_util import random_string
from ..config import CompilationResult
import subprocess
import os


def pragma_check(file: str, code: str):
    lines = code.split('\n')
    for line in lines:
        if line.strip().startswith("#pragma"):
            if line.strip() not in PRAGMA_WHITE_LIST:
                return CompilationResult(
                    compiled=False,
                    msg="In file {}:\n{}\nThis command is not allowed"
                        "!".format(file, line),
                    programPath="")
    return None


def compile_cpp(codes, time_limit, seccomp=False):
    msg = ""
    path = WORK_DIR
    program = random_string(10)
    source = program + ".cpp"

    class_name = random_string(10)
    print(codes.keys())
    if "main.cpp" in codes.keys():
        if seccomp:
            codes["main.cpp"] = codes["main.cpp"] + CPP_APPENDIX.format(a=class_name)
        codes[source] = codes["main.cpp"]
        del codes["main.cpp"]
    try:
        #print(codes.keys())
        for file, code in codes.items():
            code_file = open(os.path.join(path, file), "w")
            code_file.write(code)
            code_file.close()
    except IOError:
        print("Failed to create the file")
    except Exception as e:
        print(e)
        return CompilationResult(
            compiled=False,
            msg="Unknown Error!",
            programPath="")

    try:
        parameter = ["g++", source, "-o", program] + \
                    ["-fmax-errors=10", "-O2", "-DONLINE_JUDGE", "-lm", "-std=c++17"]
        if seccomp:
            parameter += ["-lseccomp"]
        print(parameter)
        process = subprocess.run(
            parameter,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=time_limit,
            cwd=path
        )
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
