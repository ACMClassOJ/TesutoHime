from .compile_const import *
from .compile_util import random_string
from ..config import CompilationResult
from ...util import log
import subprocess
import os


def compile_verilog(codes, time_limit, seccomp=False):
    msg = ""
    path = WORK_DIR
    program = random_string(10)
    source = program + ".v"

    

    if "test.v" in codes.keys():
        codes[source] = codes["test.v"]
        del codes["test.v"]
    else:
        log.warning("cannot found 'test.v'")
        return CompilationResult(
            compiled=False,
            msg="cannot found 'test.v'",
            programPath="")
    try:
        #print(codes.keys())
        for file, code in codes.items():
            code_file = open(os.path.join(path, file), "w")
            code_file.write(code)
            code_file.close()
    except IOError:
        msg = "Failed to create the file\n"
        log.error(msg)
        return CompilationResult(
            compiled=False,
            msg=msg,
            programPath="")
    except Exception as e:
        msg += str(e) + "\n"
        return CompilationResult(
            compiled=False,
            msg="Unknown Error!\n",
            programPath="")
            
    try:
        parameter = ["iverilog", source, "-o", program]
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
            msg=msg + "Compile Time Out!\n",
            programPath="")
    except Exception as e:
        msg += str(e) + "\n"
        return CompilationResult(
            compiled=False,
            msg=msg + "Unknown Error!\n",
            programPath="")

    if process:
        msg += process.stderr.decode() + "\n"
        msg += process.stdout.decode() + "\n"

    msg = msg.replace(program, "test")
    if not process or process.returncode != 0:
        return CompilationResult(
            compiled=False,
            msg=msg,
            programPath="")
    else:
        return CompilationResult(
            compiled=True,
            msg=msg+"Compile Success!\n",
            programPath=os.path.join(path, program))
