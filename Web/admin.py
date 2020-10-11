from flask import Flask, request, render_template, url_for
from const import *
from sessionManager import SessionManager
from userManager import UserManager
from problemManager import ProblemManager
from contestManager import ConetstManager

app = Flask('app')

session = SessionManager()
user = UserManager()
problem = ProblemManager()
contest = ConetstManager()


@app.route('/')
def test():
    return 'index'


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


@app.route('/admin')
def index():
    return render_template('admin.html')


@app.route('/admin/user', methods=['post'])
def user_manager():
    form = request.json
    # if session.Get_Privilege() < Privilege.SUPER:
    #     return ReturnCode.ERR_PERMISSION_DENIED
    err = _validate_user_data(form)
    if err is not None:
        return err
    op = int(form[String.TYPE])
    if op == 0:
        user.Add_User(form[String.USERNAME], int(form[String.STUDENT_ID]), form[String.FRIENDLY_NAME],
                      form[String.PASSWORD], form[String.PRIVILEGE])
        return ReturnCode.SUC_ADD_USER
    elif op == 1:
        user.Modify_User(form[String.USERNAME], form[String.STUDENT_ID], form[String.FRIENDLY_NAME],
                         form[String.PASSWORD], form[String.PRIVILEGE])
        return ReturnCode.SUC_MOD_USER
    elif op == 2:
        user.Delete_User(form[String.USERNAME])
        return ReturnCode.SUC_DEL_USER
    else:
        return ReturnCode.ERR_BAD_DATA


@app.route('/admin/problem', methods=['post'])
def problem_manager():
    form = request.json
    # if session.Get_Privilege() < Privilege.ADMIN:
    #     return ReturnCode.ERR_PERMISSION_DENIED
    err = _validate_problem_data(form)
    if err is not None:
        return err
    op = int(form[String.TYPE])
    if op == 0:
        problem.Add_Problem(form[String.TITLE], form[String.DESCRIPTION], form[String.INPUT], form[String.OUTPUT],
                            form[String.EXAMPLE_INPUT], form[String.EXAMPLE_OUTPUT], form[String.DATA_RANGE],
                            form[String.RELEASE_TIME])
        return ReturnCode.SUC_ADD_PROBLEM
    elif op == 1:
        problem.Modify_Problem(int(form[String.PROBLEM_ID]), form[String.TITLE], form[String.DESCRIPTION],
                               form[String.INPUT], form[String.OUTPUT], form[String.EXAMPLE_INPUT],
                               form[String.EXAMPLE_OUTPUT], form[String.DATA_RANGE], form[String.RELEASE_TIME])
        return ReturnCode.SUC_MOD_PROBLEM
    elif op == 2:
        problem.Delete_Problem(form[String.PROBLEM_ID])
        return ReturnCode.SUC_DEL_PROBLEM
    else:
        return ReturnCode.ERR_BAD_DATA


@app.route('/admin/contest', methods=['post'])
def contest_manager():
    form = request.json
    # if session.Get_Privilege() < Privilege.ADMIN:
    #     return ReturnCode.ERR_PERMISSION_DENIED
    err = _validate_contest_data(form)
    if err is not None:
        return err
    op = int(form[String.TYPE])
    print(form)
    if op == 0:
        contest.Create_Contest(form[String.CONTEST_NAME], int(form[String.START_TIME]), int(form[String.END_TIME]),
                               int(form[String.CONTEST_TYPE]))
        return ReturnCode.SUC_ADD_CONTEST
    elif op == 1:
        contest.Modify_Contest(int(form[String.CONTEST_ID]), form[String.CONTEST_NAME], int(form[String.START_TIME]),
                               int(form[String.END_TIME]), int(form[String.CONTEST_TYPE]))
        return ReturnCode.SUC_MOD_CONTEST
    elif op == 2:
        contest.Delete_Contest(int(form[String.CONTEST_ID]))
        return ReturnCode.SUC_DEL_CONTEST
    elif op == 3:
        for problemId in form[String.CONTEST_PROBLEM_IDS]:
            contest.Add_Problem_To_Contest(int(form[String.CONTEST_ID]), int(problemId))
        return ReturnCode.SUC_ADD_PROBLEMS_TO_CONTEST
    elif op == 4:
        for problemId in form[String.CONTEST_PROBLEM_IDS]:
            contest.Delete_Problem_From_Contest(int(form[String.CONTEST_ID]), int(problemId))
        return ReturnCode.SUC_DEL_PROBLEMS_FROM_CONTEST
    elif op == 5:
        for username in form[String.CONTEST_USERNAMES]:
            contest.Add_Player_To_Contest(int(form[String.CONTEST_ID]), username)
        return ReturnCode.SUC_ADD_USERS_TO_CONTEST
    elif op == 6:
        for username in form[String.CONTEST_USERNAMES]:
            contest.Delete_Player_From_Contest(int(form[String.CONTEST_ID]), username)
        return ReturnCode.SUC_DEL_USERS_FROM_CONTEST
    else:
        return ReturnCode.ERR_BAD_DATA


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)