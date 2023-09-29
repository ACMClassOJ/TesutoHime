import sys
import os
from pathlib import PosixPath

cwd = str(PosixPath(__file__).resolve().parent.parent)
sys.path.insert(0, cwd)

os.chdir(cwd)

from web.tracker import setup_log
setup_log()

from web.web import oj as application
