import sys
import os
from pathlib import PosixPath

cwd = str(PosixPath(__file__).resolve().parent.parent)
sys.path.insert(0, cwd)

os.chdir(cwd)

from web.web import oj as application
