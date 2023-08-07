from dataclasses import dataclass
from typing import Optional


class String:
    TYPE = 'type'
    SESSION = 'username'
    USERNAME = 'username'
    STUDENT_ID = 'id'
    FRIENDLY_NAME = 'name'
    PASSWORD = 'password'
    PRIVILEGE = 'privilege'
    PROBLEM_ID = 'id'
    TITLE = 'title'
    PROBLEM_TYPE = 'problem_type'
    DESCRIPTION = 'description'
    INPUT = 'input'
    OUTPUT = 'output'
    EXAMPLE_INPUT = 'example_input'
    EXAMPLE_OUTPUT = 'example_output'
    DATA_RANGE = 'range'
    RELEASE_TIME = 'time'
    CONTEST_ID = 'contest_id'
    CONTEST_NAME = 'name'
    START_TIME = 'start_time'
    END_TIME = 'end_time'
    CONTEST_TYPE = 'contest_type'
    CONTEST_PROBLEM_IDS = 'id'
    CONTEST_USERNAMES = 'username'


class ReturnCode:
    SUC = {'e': 0}

    SUC_LOGIN = {'e': 0, 'msg': 'logged in successfully'}
    SUC_LOGOUT = {'e': 0, 'msg': 'logged out successfully'}
    ERR_LOGIN = {'e': -10, 'msg': 'login failed'}
    ERR_LOGOUT = {'e': -11, 'msg': 'logout failed'}
    ERR_LOGIN_MIRROR = {'e': -12, 'msg': 'login with account from mirror is prohibited'}

    SUC_VALIDATE = {'e': 0, 'msg': '用户信息通过验证！'}
    SUC_REGISTER = {'e': 0, 'msg': '注册成功！'}
    ERR_VALIDATE_INVALID_USERNAME = {'e': -20, 'msg': '用户名不符合注册要求。用户名要求：20位以内的大小写字母或数字（第一位必须是字母）。'}
    ERR_VALIDATE_INVALID_PASSWD = {'e': -21, 'msg': '密码不符合注册要求。密码要求：6-30位的大小写字母、数字、下划线。'}
    ERR_VALIDATE_INVALID_FRIENDLY_NAME = {'e': -22, 'msg': '昵称不符合注册要求。昵称要求：60位以内的大小写字母、数字、下划线。'}
    ERR_VALIDATE_INVALID_STUDENT_ID = {'e': -23, 'msg': '学号不符合注册要求。学号要求：12位数字（如果不够可以用0补全）。'}
    ERR_VALIDATE_USERNAME_EXISTS = {'e': -24, 'msg': '用户名已被注册。'}

    SUC_ADD_USER = {'e': 0, 'msg': 'user added successfully'}
    SUC_MOD_USER = {'e': 0, 'msg': 'user modified successfully'}
    SUC_DEL_USER = {'e': 0, 'msg': 'user removed successfully'}
    SUC_ADD_PROBLEM = {'e': 0, 'msg': 'problem added successfully'}
    SUC_MOD_PROBLEM = {'e': 0, 'msg': 'problem modified successfully'}
    SUC_DEL_PROBLEM = {'e': 0, 'msg': 'problem removed successfully'}
    SUC_ADD_CONTEST = {'e': 0, 'msg': 'contest created successfully'}
    SUC_MOD_CONTEST = {'e': 0, 'msg': 'contest modified successfully'}
    SUC_DEL_CONTEST = {'e': 0, 'msg': 'contest removed successfully'}
    SUC_ADD_PROBLEMS_TO_CONTEST = {'e': 0, 'msg': 'problem(s) added to contest successfully'}
    SUC_DEL_PROBLEMS_FROM_CONTEST = {'e': 0, 'msg': 'problem(s) removed from contest successfully'}
    SUC_ADD_USERS_TO_CONTEST = {'e': 0, 'msg': 'user(s) added to contest successfully'}
    SUC_DEL_USERS_FROM_CONTEST = {'e': 0, 'msg': 'user(s) removed from contest successfully'}
    SUC_QUIZ_JSON_DECODE = {'e': 0, 'msg': 'quiz.json decoded successfully'}
    SUC_PIC_SERVICE_UPLOAD = {'e': 0, 'msg': 'picture uploaded successfully'}
    SUC_REJUDGE = {'e': 0, 'msg': 'rejudge successfully'}
    SUC_ADD_JUDGE = {'e': 0, 'msg': 'add judge successfully'}
    SUC_DISABLE_JUDGE = {'e': 0, 'msg': 'disable judge successfully'}
    SUC_ABORT_JUDGE = {'e': 0, 'msg': 'abort judge successfully'}
    SUC_ADD_REALNAME = {'e': 0, 'msg': "add realname successfully"}

    ERR_BAD_DATA = {'e': -1, 'msg': 'bad data'}
    ERR_NETWORK_FAILURE = {'e': -2, 'msg': 'network failure'}

    ERR_USER_NOT_LOGGED_IN = {'e': -100, 'msg': 'user not logged in'}
    ERR_PERMISSION_DENIED = {'e': -101, 'msg': 'permission denied'}

    ERR_INVALID_USERNAME = {'e': -200, 'msg': 'invalid username'}

    ERR_ADD_USER = {'e': -300, 'msg': 'failed to add user'}
    ERR_MOD_USER = {'e': -301, 'msg': 'failed to modify user'}
    ERR_DEL_USER = {'e': -302, 'msg': 'failed to remove user'}
    ERR_ADD_PROBLEM = {'e': -303, 'msg': 'failed to add problem(s)'}
    ERR_MOD_PROBLEM = {'e': -304, 'msg': 'failed to modify problem'}
    ERR_DEL_PROBLEM = {'e': -305, 'msg': 'failed to remove problem(s)'}
    ERR_ADD_CONTEST = {'e': -306, 'msg': 'failed to create contest'}
    ERR_MOD_CONTEST = {'e': -307, 'msg': 'failed to modify contest'}
    ERR_DEL_CONTEST = {'e': -308, 'msg': 'failed to remove contest'}
    ERR_ADD_PROBLEMS_TO_CONTEST = {'e': -309, 'msg': 'failed to add problem(s) to contest'}
    ERR_DEL_PROBLEMS_FROM_CONTEST = {'e': -310, 'msg': 'failed to remove problem(s) from contest'}
    ERR_ADDS_USER_TO_CONTEST = {'e': -311, 'msg': 'failed to add user(s) to contest'}
    ERR_DEL_USERS_FROM_CONTEST = {'e': -312, 'msg': 'failed to remove user(s) from contest'}
    ERR_CONTEST_ENDTIME_BEFORE_START_TIME = {'e': -313, 'msg': 'it is not allowed that a contest\'s end time comes before start time'}
    ERR_ADD_JUDGE_PROBLEM_ID = {'e': -314, 'msg': 'wrong problem id when adding judge'}
    ERR_ADD_JUDGE_USERNAME = {'e': -315, 'msg': 'wrong username when adding judge'}
    ERR_ADD_JUDGE_CODE_LENGTH = {'e': -315, 'msg': 'code too long when adding judge'}

    ERR_ADD_JUDGE_SERVER_INVALID = {'e': -316, 'msg': 'target server name is invalid or server is not available now'}
    ERR_ADD_JUDGE_BUSY = {'e': -317, 'msg': 'busy error'}

    ERR_QUIZ_JSON_DECODE = {'e': -400, 'msg': 'failed to decode quiz.json'}
    ERR_PROBLEM_NOT_QUIZ = {'e': -401, 'msg': 'this problem is not a quiz'}
    ERR_QUIZ_ZIP_NOT_FOUND = {'e': -402, 'msg': 'zip of this quiz not found'}

    ERR_PIC_SERIVCE_TOO_BIG = {'e': -500, 'msg': 'size of the picture should be no more than 10MB!'}
    ERR_PIC_SERIVCE_WRONG_EXT = {'e': -501, 'msg': 'acceptable file extension for picture service: gif, jpg, jpeg, png'}
    ERR_PIC_SERIVCE_SYSTEM_ERROR = {'e': -502, 'msg': 'picture service system error'}
    

class Privilege:
    GUEST = 0
    NORMAL = 0
    ADMIN = 1
    SUPER = 2


class ContestType:
    CONTEST = 0
    HOMEWORK = 1
    EXAM = 2


@dataclass
class JudgeStatusInfo:
    name: str
    color: str
    abbrev: Optional[str] = None
    badge_type: Optional[str] = None

judge_status_info = {
    'accepted': JudgeStatusInfo('Accepted', 'green', 'AC', 'success'),
    'wrong_answer': JudgeStatusInfo('Wrong Answer', 'red', 'WA', 'danger'),

    'compile_error': JudgeStatusInfo('Compile Error', 'yellow', 'CE', 'warning'),
    'runtime_error': JudgeStatusInfo('Runtime Error', 'red', 'RE', 'warning'),
    'time_limit_exceeded': JudgeStatusInfo('Time Limit Exceeded', 'orange', 'TLE', 'warning'),
    'memory_limit_exceeded': JudgeStatusInfo('Memory Limit Exceeded', 'orange', 'MLE', 'warning'),
    'disk_limit_exceeded': JudgeStatusInfo('Disk Limit Exceeded', 'purple', 'DLE', 'warning'),
    'memory_leak': JudgeStatusInfo('Memory Leak', 'purple', 'Leak', 'warning'),

    'pending': JudgeStatusInfo('Pending', 'gray-dark', 'Pending', 'secondary'),
    'compiling': JudgeStatusInfo('Compiling', 'blue', 'Compiling', 'info'),
    'judging': JudgeStatusInfo('Judging', 'blue', 'Judging', 'info'),
    'void': JudgeStatusInfo('Voided', 'brown', 'Void', 'warning'),
    'aborted': JudgeStatusInfo('Aborted', 'gray-dark', 'Aborted', 'secondary'),

    'skipped': JudgeStatusInfo('Skipped', 'black', 'Skip', 'secondary'),
    'system_error': JudgeStatusInfo('System Error', 'gray-dark', 'SE', 'default'),
    'unknown_error': JudgeStatusInfo('Unknown Error', 'gray-dark', 'UKE', 'default'),
}

language_info = {
    'cpp': 'C++',
    'git': 'Git',
    'verilog': 'Verilog',
    'quiz': 'Quiz',
}

@dataclass
class RunnerStatus:
    name: str
    color: str

runner_status_info = {
    'invalid': RunnerStatus('Invalid', 'black-50'),
    'idle': RunnerStatus('Idle', 'blue'),
    'offline': RunnerStatus('Offline', 'black-50'),
    'busy': RunnerStatus('Busy', 'orange'),
}

@dataclass
class Mntner:
    name: str
    link: str
    email: str
    avatar: str

@dataclass
class Contributor:
    name: str
    year: int
    link: str
    description: str
    avatar: str

def gh(x): return f'https://github.com/{x}'

mntners = [
    Mntner('Alan Liang', gh('Alan-Liang'), 'liangyalun@sjtu.edu.cn', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211124-010333-292122.png'),
    Mntner('Sakits', gh('Sakits'), 'sakits_tjm@sjtu.edu.cn', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211124-010147-269063.jpg'),
    Mntner('SiriusNEO', gh('SiriusNEO'), 'siriusneo@sjtu.edu.cn', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-011839-997531.jpg'),
]

contributors = [
    Contributor('Amagi_Yukisaki', 19, gh('cmd2001'), '原项目主管 & 数据库结构', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005300-112984.jpg'),
    Contributor('cong258258', 19, gh('cong258258'), '全栈', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005352-493603.jpg'),
    Contributor('Pioooooo', 19, gh('Pioooooo'), '管理界面 & 前端美化', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005321-601010.jpg'),
    Contributor('acrazyczy', 19, gh('acrazyczy'), '原评测端主管 & 接口', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005436-860153.jpg'),
    Contributor('Anoxiacxy', 19, gh('Anoxiacxy'), '原评测 & 编译沙箱', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005335-226765.jpg'),
    Contributor('XOR-op', 19, gh('XOR-op'), '原评测沙箱', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005240-615633.jpg'),
    Contributor('stneng', 19, gh('stneng'), '原数据服务 & 数据库', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005212-276113.jpg'),
    Contributor('SiriusNEO', 20, gh('SiriusNEO'), 'Web', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-011839-997531.jpg'),
    Contributor('Sakits', 20, gh('Sakits'), '管理界面', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211124-010147-269063.jpg'),
    Contributor('Alan Liang', 21, gh('Alan-Liang'), '评测端 & 全栈', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211124-010333-292122.png'),
    Contributor('LauYeeYu', 21, gh('LauYeeYu'), '文档 & 前端', 'https://acm.sjtu.edu.cn/OnlineJudge/oj-images/bb12bce8-11ee-4593-8e8b-8e9cc5843b38'),
]
