import sys

sys.path.append("..")
import formats.config as conf
import os
import random
import string

defaultPath = "/Users/vortox/tmp/test/"


def get_random_string(length):
    letters = string.ascii_letters+ string.digits
    return ''.join(random.choice(letters) for i in range(length))


def makeEnvironment() -> str:
    os.chdir(defaultPath)
    os.system("rm -r /Users/vortox/tmp/test/*")  # avoid misbehavior
    rand_name = get_random_string(16)
    os.system("mkdir " + rand_name)
    return defaultPath + rand_name


makeEnvironment()
