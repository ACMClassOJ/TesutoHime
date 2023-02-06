import sys
import os
from pathlib import PosixPath

cwd = str(PosixPath(__file__).resolve().parent)
sys.path.insert(0, cwd)
sys.path.insert(0, str(PosixPath(__file__).resolve().parent.parent))

os.chdir(cwd)

from tracker import setup_log
setup_log()

from web import oj as application
