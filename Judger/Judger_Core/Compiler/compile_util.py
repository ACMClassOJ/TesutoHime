import os, stat, random, string
def readonly_handler(func, path, execinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def random_string(n):
    return "".join(random.sample(string.ascii_letters, n))