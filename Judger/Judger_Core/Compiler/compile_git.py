from .compile_const import *
from ..config import CompilationResult
import subprocess
import os


def compile_git(url: str, time_limit, sandboxOn: bool):
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
    if sandboxOn:
        user_id = str(99942)
        group_id = str(99958)
        if "CMakeLists.txt" in os.listdir(os.path.join(path, project)):
            try:
                print(os.path.join(path, project)[1:])
                command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1' + \
                        ' -t ' + str(int(time_limit)) + ' --user ' + user_id + ' --group ' + group_id + \
                        ' -R /lib64 -R /lib -R /usr/bin/cmake -R /usr/share/cmake-3.16 -R /usr/bin/g++' + \
                        ' -B /work/compiling -B ' + os.path.join(path, project) + \
                        ' --cwd ' + os.path.join(path, project) + \
                        ' /usr/bin/cmake CMakeLists.txt'
                        #' -R /lib/x86_64-linux-gnu/ -R /lib/x86_64-linux-gnu -R /lib64 -R /usr/bin/find -R /dev/urandom --keep_caps -- /usr/bin/find / | wc -l'
                

                process = subprocess.Popen(command, shell=True)
                process.wait()
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
        try:
            command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1' + \
                    ' -t ' + str(int(time_limit)) + ' --user ' + user_id + ' --group ' + group_id + \
                    ' --cwd ' + os.path.join(path, project) + ' -R /lib64 -R /lib -R /bin -R /usr -B ' + os.path.join(path, project)[1:] + ' /make'
            
            process = subprocess.Popen(command, shell=True)
            process.wait()
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
    else:
        if "CMakeLists.txt" in os.listdir(os.path.join(path, project)):
            try:
                process = subprocess.run(
                    ["cmake", "CMakeLists.txt"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.join(path, project),
                    timeout=time_limit)
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
    if len(msg) > 10000:
        msg = msg[0 : 10000]

    if not process or process.returncode != 0:
        return CompilationResult(
            compiled=False,
            msg=msg,
            programPath="")

    return CompilationResult(
        compiled=True,
        msg=msg + "Compile Success!",
        programPath=os.path.join(path, project, program))
