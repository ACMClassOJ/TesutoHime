from web import oj
from tracker import setup_log

if __name__ == '__main__':
    setup_log()
    oj.run(host='0.0.0.0', port=5001, debug=True)