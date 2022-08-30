import sys
from pathlib import PosixPath

sys.path.append(str(PosixPath(__file__).parent.parent))

from tracker import setup_log
from web import oj

if __name__ == '__main__':
    setup_log()
    oj.run(host='0.0.0.0', port=5000, debug=True)
