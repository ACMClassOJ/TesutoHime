import sys
sys.path.insert(0,'/home/acmoj/TesutoHime/Web')
import os
os.chdir('/home/acmoj/TesutoHime/Web')
from tracker import setup_log
setup_log()
from web import oj as application
