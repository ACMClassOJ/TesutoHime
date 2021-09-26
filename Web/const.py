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

    ERR_BAD_DATA = {'e': -1, 'msg': 'bad data'}
    ERR_NETWORK_FAILURE = {'e': -2, 'msg': 'network failure'}
    ERR_LOGIN = {'e': -10, 'msg': 'login failed'}
    ERR_LOGOUT = {'e': -11, 'msg': 'logout failed'}

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
