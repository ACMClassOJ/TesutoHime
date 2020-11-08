from .compile_const import *
from ..config import CompilationResult
import subprocess
import os


def compile_git(url: str, time_limit):

    path = WORK_DIR
    program = PROGRAM_NAME
    msg = ""
    try:
        print("\nCloning...", end="")
        process = subprocess.run(
            ["git", "clone", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=time_limit,
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
        print("Done.\n")

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
                timeout=time_limit)
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
            timeout=time_limit)
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
        msg=msg + "Compile Success!",
        programPath=os.path.join(path, project, program))
