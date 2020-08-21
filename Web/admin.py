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
    if 0 <= form[String.TYPE] < 2:
        # TODO: validate
        return None
    return None


def _validate_problem_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    if 1 <= form[String.TYPE] < 3:
        # TODO: validate ID
        return None
    if 0 <= form[String.TYPE] < 2:
        # TODO: validate
        return None
    return None


def _validate_contest_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    if 1 <= form[String.TYPE] < 6:
        # TODO: validate contest ID
        return None
    if 0 <= form[String.TYPE] < 2:
        # TODO: validate
        return None
    elif 3 <= form[String.TYPE] < 5:
        # TODO: validate problem ID
        return None
    elif 5 <= form[String.TYPE] < 6:
        # TODO: validate username
        return None
    return None


@app.route('/admin')
def index():
    return render_template('admin.html')


@app.route('/admin/user', methods=['post'])
def user_manager():
    form = request.form
    if session.Get_Privilege() < Privilege.SUPER:
        return ReturnCode.ERR_INSUFFICIENT_PRIVILEGE
    err = _validate_user_data(form)
    if err is not None:
        return err
    if form[String.TYPE] == 0:
        if user.Add_User(form[String.USERNAME], form[String.STUDENT_ID], form[String.FRIENDLY_NAME],
                         form[String.PASSWORD], form[String.PRIVILEGE]):
            return ReturnCode.SUC_ADD_USER
        return ReturnCode.ERR_ADD_USER
    elif form[String.TYPE] == 1:
        if user.Modify_User(form[String.USERNAME], form[String.STUDENT_ID], form[String.FRIENDLY_NAME],
                            form[String.PASSWORD], form[String.PRIVILEGE]):
            return ReturnCode.SUC_MOD_USER
        return ReturnCode.ERR_MOD_USER
    elif form[String.TYPE] == 2:
        if user.Delete_User(form[String.USERNAME]):
            return ReturnCode.SUC_DEL_USER
        return ReturnCode.ERR_DEL_USER
    else:
        return ReturnCode.ERR_BAD_DATA


@app.route('/admin/problem', methods=['post'])
def problem_manager():
    form = request.form
    if session.Get_Privilege() < Privilege.ADMIN:
        return ReturnCode.ERR_INSUFFICIENT_PRIVILEGE
    err = _validate_problem_data(form)
    if err is not None:
        return err
    if form[String.TYPE] == 0:
        if problem.Add_Problem(form[String.TITLE], form[String.DESCRIPTION], form[String.INPUT], form[String.OUTPUT],
                               form[String.EXAMPLE_INPUT], form[String.EXAMPLE_OUTPUT], form[String.DATA_RANGE],
                               form[String.RELEASE_TIME]):
            return ReturnCode.SUC_ADD_PROBLEM
        return ReturnCode.ERR_ADD_PROBLEM
    elif form[String.TYPE] == 1:
        if problem.Modify_Problem(form[String.PROBLEM_ID], form[String.TITLE], form[String.DESCRIPTION],
                                  form[String.INPUT], form[String.OUTPUT], form[String.EXAMPLE_INPUT],
                                  form[String.EXAMPLE_OUTPUT], form[String.DATA_RANGE], form[String.RELEASE_TIME]):
            return ReturnCode.SUC_MOD_PROBLEM
        return ReturnCode.ERR_MOD_PROBLEM
    elif form[String.TYPE] == 2:
        if problem.Delete_Problem(form[String.PROBLEM_ID]):
            return ReturnCode.SUC_DEL_PROBLEM
        return ReturnCode.ERR_DEL_PROBLEM
    else:
        return ReturnCode.ERR_BAD_DATA


@app.route('/admin/contest', methods=['post'])
def contest_manager():
    form = request.form
    if session.Get_Privilege() < Privilege.ADMIN:
        return ReturnCode.ERR_INSUFFICIENT_PRIVILEGE
    err = _validate_contest_data(form)
    if err is not None:
        return err
    if form[String.TYPE] == 0:
        if contest.Create_Contest(form[String.CONTEST_NAME], form[String.START_TIME], form[String.END_TIME],
                                  form[String.CONTEST_TYPE]):
            return ReturnCode.SUC_ADD_CONTEST
        return ReturnCode.ERR_ADD_CONTEST
    elif form[String.TYPE] == 1:
        if contest.Modify_Contest(form[String.CONTEST_ID], form[String.CONTEST_NAME], form[String.START_TIME],
                                  form[String.END_TIME], form[String.CONTEST_TYPE]):
            return ReturnCode.SUC_MOD_CONTEST
        return ReturnCode.ERR_MOD_CONTEST
    elif form[String.TYPE] == 2:
        if contest.Delete_Contest(form[String.CONTEST_ID]):
            return ReturnCode.SUC_DEL_CONTEST
        return ReturnCode.ERR_DEL_CONTEST
    elif form[String.TYPE] == 3:
        ok = True
        for problemId in form[String.CONTEST_PROBLEM_IDS]:
            ok &= contest.Add_Problem_To_Contest(form[String.CONTEST_ID], problemId)
        if ok:
            return ReturnCode.SUC_ADD_PROBLEMS_TO_CONTEST
        return ReturnCode.ERR_ADD_PROBLEMS_TO_CONTEST
    elif form[String.TYPE] == 4:
        ok = True
        for problemId in form[String.CONTEST_PROBLEM_IDS]:
            ok &= contest.Delete_Problem_From_Contest(form[String.CONTEST_ID], problemId)
        if ok:
            return ReturnCode.SUC_DEL_PROBLEMS_FROM_CONTEST
        return ReturnCode.ERR_DEL_PROBLEMS_FROM_CONTEST
    elif form[String.TYPE] == 5:
        ok = True
        for username in form[String.CONTEST_USERNAMES]:
            ok &= contest.Add_Player_To_Contest(form[String.CONTEST_ID], username)
        if ok:
            return ReturnCode.SUC_ADD_USERS_TO_CONTEST
        return ReturnCode.ERR_ADDS_USER_TO_CONTEST
    elif form[String.TYPE] == 6:
        ok = True
        for username in form[String.CONTEST_USERNAMES]:
            ok &= contest.Delete_Player_From_Contest(form[String.CONTEST_ID], username)
        if ok:
            return ReturnCode.SUC_DEL_USERS_FROM_CONTEST
        return ReturnCode.ERR_DEL_USERS_FROM_CONTEST
    else:
        return ReturnCode.ERR_BAD_DATA


if __name__ == '__main__':
    app.run()
