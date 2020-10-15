from flask import request, render_template, Blueprint, abort
from const import *
from sessionManager import Login_Manager
from userManager import User_Manager
from problemManager import Problem_Manager
from contestManager import Contest_Manager
from requests import post

admin = Blueprint('admin', __name__, static_folder='static')


# TODO(Pioooooo): validate data
def _validate_user_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    # TODO: validate username
    op = int(form[String.TYPE])
    if 0 <= op < 2:
        # TODO: validate
        return None
    return None


def _validate_problem_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    op = int(form[String.TYPE])
    if 1 <= op < 3:
        # TODO: validate ID
        return None
    if 0 <= op < 2:
        # TODO: validate
        return None
    return None


def _validate_contest_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    op = int(form[String.TYPE])
    if 1 <= op < 6:
        # TODO: validate contest ID
        return None
    if 0 <= op < 2:
        # TODO: validate
        return None
    elif 3 <= op < 5:
        # TODO: validate problem ID
        return None
    elif 5 <= op < 6:
        # TODO: validate username
        return None
    return None


@admin.route('/')
def index():
    privilege = Login_Manager.Get_Privilege()
    privilege = Privilege.SUPER
    if privilege < Privilege.ADMIN:
        abort(404)
    return render_template('admin.html', privilege=privilege, Privilege=Privilege)


@admin.route('/user', methods=['post'])
def user_manager():
    if Login_Manager.Get_Privilege() < Privilege.SUPER:
        abort(404)
    form = request.json
    # err = _validate_user_data(form)
    # if err is not None:
    #     return err
    op = int(form[String.TYPE])
    if op == 0:
        User_Manager.Add_User(form[String.USERNAME], int(form[String.STUDENT_ID]), form[String.FRIENDLY_NAME],
                              form[String.PASSWORD], form[String.PRIVILEGE])
        return ReturnCode.SUC_ADD_USER
    elif op == 1:
        User_Manager.Modify_User(form[String.USERNAME], form[String.STUDENT_ID], form[String.FRIENDLY_NAME],
                                 form[String.PASSWORD], form[String.PRIVILEGE])
        return ReturnCode.SUC_MOD_USER
    elif op == 2:
        User_Manager.Delete_User(form[String.USERNAME])
        return ReturnCode.SUC_DEL_USER
    else:
        return ReturnCode.ERR_BAD_DATA


@admin.route('/problem', methods=['post'])
def problem_manager():
    if Login_Manager.Get_Privilege() < Privilege.ADMIN:
        abort(404)
    form = request.json
    # err = _validate_problem_data(form)
    # if err is not None:
    #     return err
    op = int(form[String.TYPE])
    if op == 0:
        Problem_Manager.Add_Problem(form[String.TITLE], form[String.DESCRIPTION], form[String.INPUT],
                                    form[String.OUTPUT],
                                    form[String.EXAMPLE_INPUT], form[String.EXAMPLE_OUTPUT], form[String.DATA_RANGE],
                                    form[String.RELEASE_TIME])
        return ReturnCode.SUC_ADD_PROBLEM
    elif op == 1:
        Problem_Manager.Modify_Problem(int(form[String.PROBLEM_ID]), form[String.TITLE], form[String.DESCRIPTION],
                                       form[String.INPUT], form[String.OUTPUT], form[String.EXAMPLE_INPUT],
                                       form[String.EXAMPLE_OUTPUT], form[String.DATA_RANGE], form[String.RELEASE_TIME])
        return ReturnCode.SUC_MOD_PROBLEM
    elif op == 2:
        Problem_Manager.Delete_Problem(form[String.PROBLEM_ID])
        return ReturnCode.SUC_DEL_PROBLEM
    else:
        return ReturnCode.ERR_BAD_DATA


@admin.route('/contest', methods=['post'])
def contest_manager():
    if Login_Manager.Get_Privilege() < Privilege.ADMIN:
        abort(404)
    form = request.json
    # err = _validate_contest_data(form)
    # if err is not None:
    #     return err
    op = int(form[String.TYPE])
    if op == 0:
        Contest_Manager.Create_Contest(form[String.CONTEST_NAME], int(form[String.START_TIME]),
                                       int(form[String.END_TIME]),
                                       int(form[String.CONTEST_TYPE]))
        return ReturnCode.SUC_ADD_CONTEST
    elif op == 1:
        Contest_Manager.Modify_Contest(int(form[String.CONTEST_ID]), form[String.CONTEST_NAME],
                                       int(form[String.START_TIME]),
                                       int(form[String.END_TIME]), int(form[String.CONTEST_TYPE]))
        return ReturnCode.SUC_MOD_CONTEST
    elif op == 2:
        Contest_Manager.Delete_Contest(int(form[String.CONTEST_ID]))
        return ReturnCode.SUC_DEL_CONTEST
    elif op == 3:
        for problemId in form[String.CONTEST_PROBLEM_IDS]:
            Contest_Manager.Add_Problem_To_Contest(int(form[String.CONTEST_ID]), int(problemId))
        return ReturnCode.SUC_ADD_PROBLEMS_TO_CONTEST
    elif op == 4:
        for problemId in form[String.CONTEST_PROBLEM_IDS]:
            Contest_Manager.Delete_Problem_From_Contest(int(form[String.CONTEST_ID]), int(problemId))
        return ReturnCode.SUC_DEL_PROBLEMS_FROM_CONTEST
    elif op == 5:
        for username in form[String.CONTEST_USERNAMES]:
            Contest_Manager.Add_Player_To_Contest(int(form[String.CONTEST_ID]), username)
        return ReturnCode.SUC_ADD_USERS_TO_CONTEST
    elif op == 6:
        for username in form[String.CONTEST_USERNAMES]:
            Contest_Manager.Delete_Player_From_Contest(int(form[String.CONTEST_ID]), username)
        return ReturnCode.SUC_DEL_USERS_FROM_CONTEST
    else:
        return ReturnCode.ERR_BAD_DATA


@admin.route('/data', methods=['POST'])
def data_upload():
    if Login_Manager.Get_Privilege() < Privilege.ADMIN:
        abort(404)
    if 'file' in request.files:
        f = request.files['file']
        try:
            r = post('', files={'file': (f.filename, f)})
            return {'e': r.content}
        except:
            pass
    return {'e': -1}
