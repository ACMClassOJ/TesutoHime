import os, stat
def readonly_handler(func, path, execinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)