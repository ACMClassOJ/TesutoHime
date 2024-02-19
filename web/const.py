from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Optional


class ReturnCode:
    SUC = {'e': 0}

    SUC_REJUDGE = {'e': 0, 'msg': 'rejudge successfully'}
    SUC_DISABLE_JUDGE = {'e': 0, 'msg': 'disable judge successfully'}
    SUC_ABORT_JUDGE = {'e': 0, 'msg': 'abort judge successfully'}

    ERR_BAD_DATA = {'e': -1, 'msg': 'bad data'}
    ERR_PERMISSION_DENIED = {'e': -101, 'msg': 'permission denied'}


class Privilege:
    GUEST = 0
    NORMAL = 0
    ADMIN = 1
    SUPER = 2


class PrivilegeType(IntEnum):
    no_privilege = 0
    readonly = 1
    owner = 2


class ContestType:
    CONTEST = 0
    HOMEWORK = 1
    EXAM = 2


FAR_FUTURE_TIME = datetime(9999, 12, 31, 8, 42, 42)


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
    'bad_problem': JudgeStatusInfo('Bad Problem', 'gray-dark', 'BP', 'default'),
    'unknown_error': JudgeStatusInfo('Unknown Error', 'gray-dark', 'UKE', 'default'),
}

@dataclass
class LanguageInfo:
    name: str
    extension: Optional[str] = None
    # if false, users could not submit in this language, unless the problem
    # allows explicitly
    acceptable_by_default: bool = True

language_info = {
    'cpp': LanguageInfo('C++', 'cpp'),
    'python': LanguageInfo('Python', 'py'),
    'git': LanguageInfo('Git'),
    'verilog': LanguageInfo('Verilog', 'v', acceptable_by_default=False),
    'quiz': LanguageInfo('Quiz', 'json', acceptable_by_default=False),
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
    Mntner('LauYeeYu', gh('LauYeeYu'), 'liu_yiyu@sjtu.edu.cn', 'https://acm.sjtu.edu.cn/OnlineJudge/oj-images/3d435e1d-274a-491b-9f36-f1433c3ccade'),
    Mntner('Wankupi', gh('Wankupi'), 'kunpengwang@sjtu.edu.cn', 'https://acm.sjtu.edu.cn/OnlineJudge/oj-images/847be529-0157-4e06-8920-48bbd4735032'),
]

contributors = [
    Contributor('Amagi_Yukisaki', 19, gh('cmd2001'), '原项目主管 & 数据库结构', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005300-112984.jpg'),
    Contributor('cong258258', 19, gh('cong258258'), '全栈', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005352-493603.jpg'),
    Contributor('Pioooooo', 19, gh('Pioooooo'), '管理界面 & 前端美化', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005321-601010.jpg'),
    Contributor('acrazyczy', 19, gh('acrazyczy'), '原评测端主管 & 接口', 'https://acm.sjtu.edu.cn/OnlineJudge/oj-images/345380f8-a061-41de-95ed-ea7bfcc1df56'),
    Contributor('Anoxiacxy', 19, gh('Anoxiacxy'), '原评测 & 编译沙箱', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005335-226765.jpg'),
    Contributor('XOR-op', 19, gh('XOR-op'), '原评测沙箱', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005240-615633.jpg'),
    Contributor('stneng', 19, gh('stneng'), '原数据服务 & 数据库', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-005212-276113.jpg'),
    Contributor('SiriusNEO', 20, gh('SiriusNEO'), 'Web', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211116-011839-997531.jpg'),
    Contributor('Sakits', 20, gh('Sakits'), '管理界面', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211124-010147-269063.jpg'),
    Contributor('Alan Liang', 21, gh('Alan-Liang'), '评测端 & 全栈', 'https://acm.sjtu.edu.cn/OnlineJudge-pic/20211124-010333-292122.png'),
    Contributor('LauYeeYu', 21, gh('LauYeeYu'), '文档 & 前端', 'https://acm.sjtu.edu.cn/OnlineJudge/oj-images/3d435e1d-274a-491b-9f36-f1433c3ccade'),
    Contributor('Wankupi', 22, gh('Wankupi'), '前端', 'https://acm.sjtu.edu.cn/OnlineJudge/oj-images/847be529-0157-4e06-8920-48bbd4735032'),
]
