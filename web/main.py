from web.tracker import setup_log

from web.web import oj
from web.config import WebConfig

if __name__ == '__main__':
    setup_log()
    oj.run(host='0.0.0.0', port=5000, debug=WebConfig.Debug)
