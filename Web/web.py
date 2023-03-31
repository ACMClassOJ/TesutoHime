import json
import os
import re
from functools import cmp_to_key
from http.client import NOT_FOUND, OK, SEE_OTHER
from math import ceil
from typing import List, Optional, Tuple
from urllib.parse import quote, urlencode, urljoin
from uuid import uuid4

from admin import admin
from config import JudgeConfig, LoginConfig, ProblemConfig, WebConfig
from const import (Privilege, ReturnCode, ContestType,
                   contributors, judge_status_info,
                   language_info, mntners, runner_status_info, aflanguages)
from contestCache import Contest_Cache
from contestManager import Contest_Manager
from discussManager import Discuss_Manager
from flask import (Blueprint, Flask, abort, make_response, redirect,
                   render_template, request, send_from_directory)
from judgeManager import (NotFoundException, abort_judge,
                          key_from_submission_id, mark_void, rejudge,
                          schedule_judge)
from oldJudgeManager import Judge_Manager
from problemManager import Problem_Manager
from quizManager import Quiz_Manager
from referenceManager import Reference_Manager
from sessionManager import Login_Manager
from sqlalchemy.orm import defer, joinedload, selectinload
from tracker import tracker
from userManager import User_Manager
from utils import *

import commons.task_typing
from commons.models import (Contest, ContestProblem, JudgeRecord2,
                            JudgeRunner2, JudgeStatus, Problem)
from commons.task_typing import ProblemJudgeResult
from commons.util import load_dataclass, serialize

web = Blueprint('web', __name__, static_folder='static', template_folder='templates')
web.register_blueprint(admin, url_prefix='/admin')


def validate(username: Optional['str'] = None,
             password: Optional['str'] = None,
             friendly_name: Optional['str'] = None,
             student_id: Optional['str'] = None) -> int:
    """Validate a user.

    This function is used in registering and updating user information.

    Args:
        username: The username to validate.
        password: The password to validate.
        friendly_name: The friendly name to validate.
        student_id: The student id to validate.
    
    Returns:
        ReturnCode.SUC_VALIDATE if all the fields are valid.
        ReturnCode.ERR_VALIDATE_INVALID_USERNAME if the username is invalid.
        ReturnCode.ERR_VALIDATE_INVALID_PASSWD if the password is invalid.
        ReturnCode.ERR_VALIDATE_INVALID_FRIENDLY_NAME if the friendly name is invalid.
        ReturnCode.ERR_VALIDATE_INVALID_STUDENT_ID if the student id is invalid.
        ReturnCode.ERR_VALIDATE_USERNAME_EXISTS if the username already exists.

        The definition of ReturnCode is at Web/const.py.
    """
    username_reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    password_reg = '([a-zA-Z0-9_\!\@\#\$\%\^&\*\(\)]{6,30})$'
    friendly_name_reg = '([a-zA-Z0-9_]{1,60})$'
    student_id_reg = '([0-9]{12})$'
    if username is not None and re.match(username_reg, username) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_USERNAME
    if password is not None and re.match(password_reg, password) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_PASSWD
    if friendly_name is not None and re.match(friendly_name_reg, friendly_name) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_FRIENDLY_NAME
    if student_id is not None and re.match(student_id_reg, student_id) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_STUDENT_ID
    if username is not None and not User_Manager.validate_username(username):
        return ReturnCode.ERR_VALIDATE_USERNAME_EXISTS
    return ReturnCode.SUC_VALIDATE


def readable_lang(lang: int) -> str:
    # Get the readable language name.
    lang_str = {
        0: 'C++',
        1: 'Git',
        2: 'Verilog',
        3: 'Quiz',
    }
    try:
        return lang_str[lang]
    except KeyError:
        return 'UNKNOWN'


"""
The exam visibility part.
"""

def problem_in_exam(problem_id):
    """This is mainly for closing the discussion & rank part.
    In exam means:
    1. user is not admin.
    2. the problem is in a ongoing exam.
    """
    exam_id, is_exam_started = Contest_Manager.get_unfinished_exam_info_for_player(Login_Manager.get_username(), unix_nano())
    
    if exam_id == -1 or is_exam_started == False:
        return False

    return Login_Manager.get_privilege() < Privilege.ADMIN and Contest_Manager.check_problem_in_contest(exam_id, problem_id)


def is_code_visible(code_owner, problem_id, shared):
    # Check whether the code is visible.

    # admin always visible
    if Login_Manager.get_privilege() >= Privilege.ADMIN:
        return True
    
    username = Login_Manager.get_username()
    # exam first
    exam_id, is_exam_started = Contest_Manager.get_unfinished_exam_info_for_player(username, unix_nano())

    if exam_id != -1 and is_exam_started:
        # if the user is in a running exam, he can only see his own problems in exam.
        return code_owner == username and Contest_Manager.check_problem_in_contest(exam_id, problem_id)
    else:
        # otherwise, the user can see his own and shared problems
        return code_owner == username or shared


@web.before_request
def log():
    if (request.full_path.startswith(('/OnlineJudge/static',
                                      '/OnlineJudge/api/heartBeat')) or
        request.full_path.endswith(('.js', '.css', '.ico'))):
        return
    tracker.log()


@web.route('/')
def index():
    return render_template(
        'index.html',
        friendlyName = Login_Manager.get_friendly_name(),
        is_Admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    )


@web.route('/index.html')
def index2():
    return redirect('/')


@web.route('/api/get_username', methods=['POST'])
def get_username():
    return Login_Manager.get_friendly_name()


@web.route('/api/get_problem_id_autoinc', methods=['POST'])
def get_problem_id_autoinc():
    return str(Problem_Manager.get_max_id() + 1)

@web.route('/api/get_contest_id_autoinc', methods=['POST'])
def get_contest_id_autoinc():
    return str(Contest_Manager.get_max_id() + 1)

@web.route('/api/get_detail', methods=['POST'])
def get_detail():
    if not Login_Manager.check_user_status():
        return '-1'
    problem_id = request.form.get('problem_id')
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        return '-1'
    return json.dumps(Problem_Manager.get_problem(problem_id))

@web.route('/api/get_contest_detail', methods=['POST'])
def get_contest_detail():
    if not Login_Manager.check_user_status():
        return '-1'
    contest_id = request.form.get('contest_id')
    return json.dumps(Contest_Manager.get_contest(contest_id))

@web.route('/api/join', methods=['POST'])
def join_contest():
    if not Login_Manager.check_user_status():
        return '-1'
    arg = request.form.get('contest_id')
    if arg is None:
        return '-1'
    st, ed = Contest_Manager.get_time(arg)
    if unix_nano() > ed:
        return '-1'
    username = Login_Manager.get_username()
    if not Contest_Manager.check_player_in_contest(arg, username):
        Contest_Manager.add_player_to_contest(arg, username)
    return '0'


@web.route('/api/code', methods=['POST'])
def get_code():
    if not Login_Manager.check_user_status():
        return '-1'
    arg = request.form.get('submit_id')
    if arg is None:
        return '-1'
    if not str(request.form.get('submit_id')).isdigit():  # bad argument
        return '-1'
    run_id = int(request.form.get('submit_id'))
    if run_id < 0 or run_id > Judge_Manager.max_id():
        return '-1'
    detail = Judge_Manager.query_judge(run_id)
    if not is_code_visible(detail['User'], detail['Problem_ID'], detail['Share']):
        return '-1'
    return detail['Code']


@web.route('/api/quiz', methods=['POST'])
def get_quiz():
    if not Login_Manager.check_user_status():
        return ReturnCode.ERR_USER_NOT_LOGGED_IN
    problem_id = request.form.get('problem_id')
    if problem_id is None:
        return ReturnCode.ERR_BAD_DATA
    if not str(problem_id).isdigit():  # bad argument
        return ReturnCode.ERR_BAD_DATA
    problem_id = int(problem_id)
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        return ReturnCode.ERR_PERMISSION_DENIED
    problem_type = Problem_Manager.get_problem_type(problem_id)
    if problem_type != 1:
        return ReturnCode.ERR_PROBLEM_NOT_QUIZ
    quiz_json = Quiz_Manager.get_json_from_data_service_by_id(QuizTempDataConfig, problem_id)
    if quiz_json['e'] == 0:
        for i in quiz_json["problems"]:
            i["answer"] = ""
    return json.dumps(quiz_json)


@web.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        nxt = request.args.get('next')
        nxt = '/' if nxt is None else nxt
        return render_template('login.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    if username.endswith("mirror"):
        return ReturnCode.ERR_LOGIN_MIRROR
    if not User_Manager.check_login(username, password):  # no need to avoid sql injection
        return ReturnCode.ERR_LOGIN
    lid = str(uuid4())
    username = User_Manager.get_username(username)
    Login_Manager.new_session(username, lid)
    ret = make_response(ReturnCode.SUC_LOGIN)
    ret.set_cookie(key='Login_ID', value=lid, max_age=LoginConfig.Login_Life_Time)
    return ret


@web.route('/logout')
def logout():
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/')
    ret = make_response(redirect('/OnlineJudge/'))
    ret.delete_cookie('Login_ID')
    return ret


@web.route('/register', methods=['GET', 'POST'])
def register():
    if WebConfig.Block_Register:
        abort(404)
    if request.method == 'GET':
        nxt = request.args.get('next')
        return render_template('register.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    friendly_name = request.form.get('friendly_name')
    student_id = request.form.get('student_id')
    val = validate(username, password, friendly_name, student_id)
    if val == ReturnCode.SUC_VALIDATE:
        User_Manager.add_user(username, student_id, friendly_name, password, '0')
        return ReturnCode.SUC_REGISTER
    else:
        return val


@web.route('/problem')
def problem_list():
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    is_admin = bool(Login_Manager.get_privilege() >= Privilege.ADMIN)
    page = request.args.get('page')
    page = int(page) if page is not None else 1

    problem_id = request.args.get('problem_id')
    if problem_id == '':
        problem_id = None
    if problem_id != None:
        return redirect(f'/OnlineJudge/problem/{problem_id}')
    problem_name_keyword = request.args.get('problem_name_keyword')
    if problem_name_keyword == '':
        problem_name_keyword = None
    problem_type = request.args.get('problem_type')
    if problem_type == '-1' or problem_type == '':
        problem_type = None    
    contest_id = request.args.get('contest_id')
    if contest_id == '':
        contest_id = None        

    if problem_id is None and problem_name_keyword is None and problem_type is None and contest_id is None:
        problem_count_all = 0
        problem_count_under_11000 = 0
        if is_admin:
            problem_count_all = int(Problem_Manager.get_problem_count_admin())
            problem_count_under_11000 = (Problem_Manager.get_problem_count_under_11000_admin())
        else:
            problem_count_all = int(Problem_Manager.get_problem_count(unix_nano()))
            problem_count_under_11000 = (Problem_Manager.get_problem_count_under_11000(unix_nano()))
        max_page = int(problem_count_all / WebConfig.Problems_Each_Page)
        if problem_count_all % WebConfig.Problems_Each_Page != 0:
            max_page += 1
        latest_page_under_11000 = int(int(problem_count_under_11000 / WebConfig.Problems_Each_Page))
        if problem_count_under_11000 % WebConfig.Problems_Each_Page != 0:
            latest_page_under_11000 += 1
        page = max(min(max_page, page), 1)
        problems = Problem_Manager.problem_in_page_autocalc(page, WebConfig.Problems_Each_Page, unix_nano(),
                                                    Login_Manager.get_privilege() >= Privilege.ADMIN)

        return render_template('problem_list.html', Problems=problems, 
                            Pages=gen_page_for_problem_list(page, max_page, latest_page_under_11000),
                            Args=dict(),
                            friendlyName=Login_Manager.get_friendly_name(),
                            is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)

    problems = Problem_Manager.search_problem(unix_nano(), is_admin, problem_id, problem_name_keyword, problem_type, contest_id)
    max_page = int (len(problems) / WebConfig.Problems_Each_Page)
    page = max(min(max_page, page), 1)
    start_index = (page - 1) * WebConfig.Problems_Each_Page
    end_index = min(len(problems), page * WebConfig.Problems_Each_Page)
    return render_template('problem_list.html', Problems=problems[start_index:end_index],
                            Pages=gen_page_for_problem_list(page, max_page, 1),    
                            Args=dict(filter(lambda e: e[0] != 'page', request.args.items())),
                            friendlyName=Login_Manager.get_friendly_name(),
                            is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)                        

@web.route('/problem/<int:problem_id>')
def problem_detail(problem_id):
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    if problem_id is None or problem_id < 1000 or (problem_id > Problem_Manager.get_max_id() and problem_id < 11000) or problem_id > Problem_Manager.get_real_max_id():
        abort(404)  # No argument fed
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    
    in_exam = problem_in_exam(problem_id)

    return render_template('problem_details.html', ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           In_Exam=in_exam, friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/problem/<int:problem_id>/admin', methods=['GET', 'POST'])
def problem_admin(problem_id):
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    if not is_admin:
        abort(404)

    now = datetime.datetime.now().timestamp()
    if request.method == 'POST':
        action = request.form['action']
        if action == 'hide':
            with SqlSession() as db:
                db.query(Problem).where(Problem.id == problem_id).one().release_time = 253402216962
                db.commit()
        elif action == 'show':
            with SqlSession() as db:
                db.query(Problem).where(Problem.id == problem_id).one().release_time = now - 1
                db.commit()
        elif action == 'delete':
            if request.form['confirm'] != str(problem_id):
                abort(400)
            with SqlSession() as db:
                submission_count = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).count()
                contest_count = db.query(ContestProblem.id).where(ContestProblem.problem_id == problem_id).count()
                if submission_count > 0 or contest_count > 0:
                    abort(400)
                problem = db.query(Problem).where(Problem.id == problem_id).one_or_none()
                db.delete(problem)
                db.commit()
            return redirect('/OnlineJudge/admin/')
        else:
            abort(400)

    with SqlSession(expire_on_commit=False) as db:
        problem = db.query(Problem).where(Problem.id == problem_id).one_or_none()
        if problem is None:
            abort(404)
        submission_count = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).count()
        ac_count = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).where(JudgeRecord2.status == JudgeStatus.accepted).count()
        contests = db.query(ContestProblem.contest_id).where(ContestProblem.problem_id == problem_id).all()
        contests = [ x.contest_id for x in contests ]

    in_exam = problem_in_exam(problem_id)

    return render_template('problem_admin.html', ID=problem_id, Title=problem.title,
                           In_Exam=in_exam, friendlyName=Login_Manager.get_friendly_name(),
                           problem=problem, now=now, contests=contests,
                           submission_count=submission_count, ac_count=ac_count,
                           is_Admin=is_admin)


aflanguages_map = dict([ lang['value'], lang ] for group in aflanguages for lang in aflanguages[group])

@web.route('/problem/<int:problem_id>/submit', methods=['GET', 'POST'])
def submit_problem(problem_id):
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('/OnlineJudge/login?next=' + request.full_path)
        if Problem_Manager.get_release_time(
                problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
            abort(404)
        title = Problem_Manager.get_title(problem_id)
        problem_type = Problem_Manager.get_problem_type(problem_id)
        in_exam = problem_in_exam(problem_id)
        if problem_type == 0:
            return render_template('problem_submit.html', Problem_ID=problem_id, Title=title, In_Exam=in_exam,
                               friendlyName=Login_Manager.get_friendly_name(),
                               aflanguages=aflanguages,
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
        elif problem_type == 1:
            return render_template('quiz_submit.html', Problem_ID=problem_id, Title=title, In_Exam=in_exam,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        if not Login_Manager.check_user_status():
            return redirect('/OnlineJudge/login?next=' + request.full_path)
        if Problem_Manager.get_release_time(
                problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
            return '-1'
        share = bool(request.form.get('shared', 0))  # 0 or 1
        
        if (problem_id < 1000 or
            (problem_id > Problem_Manager.get_max_id() and problem_id < 11000) or
            problem_id > Problem_Manager.get_real_max_id()):
            abort(404)
        if (unix_nano() < Problem_Manager.get_release_time(int(problem_id)) and
            Login_Manager.get_privilege() < Privilege.ADMIN):
            return '-1'
        username = Login_Manager.get_username()
        lang_request_str = str(request.form.get('lang'))
        if lang_request_str == 'quiz':
            user_code = json.dumps(request.form.to_dict())
        else:
            user_code = request.form.get('code')
        if len(str(user_code)) > ProblemConfig.Max_Code_Length:
            return '-1'
        lang_str = lang_request_str.lower()
        if lang_str not in aflanguages_map:
            abort(400)
        lang = aflanguages_map[lang_str]
        if 'link' in lang:
            with open('af.log', 'a') as f:
                f.write(lang_str + '\n')
            return lang['link']
        with SqlSession() as db:
            rec = JudgeRecord2(
                public=share,
                language=lang_str,
                username=username,
                problem_id=problem_id,
                status=JudgeStatus.pending,
            )
            db.add(rec)
            db.commit()
            submission_id = rec.id
        key = key_from_submission_id(submission_id)
        bucket = S3Config.Buckets.submissions
        s3_internal.put_object(Bucket=bucket, Key=key, Body=user_code.encode())
        schedule_judge(problem_id, submission_id, lang_str, username)
        return '0'


def check_scheduler_auth():
    auth = request.headers.get('Authorization', '')
    if auth != SchedulerConfig.auth:
        abort(401)


@web.route('/api/submission/<submission_id>/status', methods=['PUT'])
def set_status(submission_id):
    check_scheduler_auth()
    status = request.get_data(as_text=True)
    if status not in ('compiling', 'judging'):
        print(status)
        abort(400)
    with SqlSession() as db:
        rec: JudgeRecord2 = db \
            .query(JudgeRecord2) \
            .where(JudgeRecord2.id == submission_id) \
            .one_or_none()
        if rec is None:
            abort(404)
        rec.status = getattr(JudgeStatus, status)
        rec.details = None
        rec.message = None
        db.commit()
    return ''


@web.route('/api/submission/<submission_id>/result', methods=['PUT'])
def set_result(submission_id):
    check_scheduler_auth()
    classes = commons.task_typing.__dict__
    res: ProblemJudgeResult = load_dataclass(request.json, classes)
    with SqlSession() as db:
        rec: JudgeRecord2 = db \
            .query(JudgeRecord2) \
            .where(JudgeRecord2.id == submission_id) \
            .one_or_none()
        if rec is None:
            abort(404)
        rec.score = int(res.score)
        rec.status = res.result
        rec.message = res.message
        rec.details = serialize(res)
        if res is not None and res.resource_usage is not None:
            rec.time_msecs = res.resource_usage.time_msecs
            rec.memory_bytes = res.resource_usage.memory_bytes
        db.commit()
    return ''


@web.route('/problem/<int:problem_id>/rank')
def problem_rank(problem_id):
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    sort_parameter = request.args.get('sort')
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    with SqlSession(expire_on_commit=False) as db:
        submissions: List[JudgeRecord2] = db \
            .query(JudgeRecord2) \
            .options(defer(JudgeRecord2.details), defer(JudgeRecord2.message)) \
            .options(selectinload(JudgeRecord2.user)) \
            .where(JudgeRecord2.problem_id == problem_id) \
            .where(JudgeRecord2.status == JudgeStatus.accepted) \
            .all()

    real_names = {}
    languages = {}
    for submission in submissions:
        if is_admin:
            real_names[submission] = Reference_Manager.Query_Realname(submission.user.student_id)
        languages[submission] = 'Unknown' if submission.language not in language_info \
            else language_info[submission.language]

    if sort_parameter == 'memory':
        submissions = sorted(submissions, key=lambda x: x.memory_bytes)
    elif sort_parameter == 'submit_time':
        submissions = sorted(submissions, key=lambda x: x.created)
    else:
        sort_parameter = 'time'
        submissions = sorted(submissions, key=lambda x: x.time_msecs)

    in_exam = problem_in_exam(problem_id)

    return render_template('problem_rank.html', Problem_ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           submissions=submissions, Sorting=sort_parameter, friendlyName=Login_Manager.get_friendly_name(),
                           readable_lang=readable_lang, readable_time=readable_time,
                           is_Admin=is_admin, real_names=real_names, languages=languages,
                           In_Exam=in_exam)


@web.route('/problem/<int:problem_id>/discuss', methods=['GET', 'POST'])
def discuss(problem_id):
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('/OnlineJudge/login?next=' + request.full_path)

        in_exam = problem_in_exam(problem_id)

        if in_exam:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID=problem_id,
                                   Title=Problem_Manager.get_title(problem_id), Blocked=True,
                                   friendlyName=Login_Manager.get_friendly_name(),
                                   is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN,
                                   In_Exam=True)  # Discussion Closed
        username = Login_Manager.get_username()  # for whether to display edit or delete
        privilege = Login_Manager.get_privilege()
        data = Discuss_Manager.get_discuss_for_problem(problem_id)
        discussion = []
        for ele in data:
            tmp = [ele[0], User_Manager.get_friendly_name(ele[1]), ele[2], readable_time(int(ele[3]))]
            if ele[1] == username or privilege >= Privilege.SUPER:  # ele[4]: editable?
                tmp.append(True)
            else:
                tmp.append(False)
            discussion.append(tmp)
        return render_template('problem_discussion.html', Problem_ID=problem_id,
                               Title=Problem_Manager.get_title(problem_id), Discuss=discussion,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN,
                               In_Exam=False)
    else:
        if not Login_Manager.check_user_status():
            return ReturnCode.ERR_USER_NOT_LOGGED_IN
        try:
            form = request.json
            action = form.get('action')  # post, edit, delete
            if action == 'post':
                text = form.get('text')
                username = Login_Manager.get_username()
                if Login_Manager.get_privilege() >= Privilege.ADMIN:    # administrator
                    Discuss_Manager.add_discuss(problem_id, username, text)
                    return ReturnCode.SUC
                else:
                    print('Access Denied in Discuss: Add')
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'edit':
                discuss_id = form.get('discuss_id')
                text = form.get('text')
                username = Login_Manager.get_username()
                if username == Discuss_Manager.get_author(
                        discuss_id) or Login_Manager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                    Discuss_Manager.modify_discuss(discuss_id, text)
                    return ReturnCode.SUC
                else:
                    print('Access Denied in Discuss: Edit')
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'delete':
                discuss_id = form.get('discuss_id')
                username = Login_Manager.get_username()
                if username == Discuss_Manager.get_author(
                        discuss_id) or Login_Manager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                    Discuss_Manager.delete_discuss(discuss_id)
                    return ReturnCode.SUC
                else:
                    print('Access Dined in Discuss: Delete')
                    return ReturnCode.ERR_PERMISSION_DENIED
            else:  # what happened?
                return ReturnCode.ERR_BAD_DATA
        except KeyError:
            return ReturnCode.ERR_BAD_DATA
        except TypeError:
            return ReturnCode.ERR_BAD_DATA


@web.route('/status')
def status():
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)

    page = request.args.get('page')
    arg_submitter = request.args.get('submitter')
    if arg_submitter == '':
        arg_submitter = None
    arg_problem_id = request.args.get('problem_id')
    if arg_problem_id == '':
        arg_problem_id = None
    arg_status = request.args.get('status')
    if arg_status == '':
        arg_status = None
    if arg_status is not None:
        arg_status = getattr(JudgeStatus, arg_status, None)
        if not isinstance(arg_status, JudgeStatus):
            abort(400)
    arg_lang = request.args.get('lang')
    if arg_lang == '':
        arg_lang = None
    username = Login_Manager.get_username()
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN

    with SqlSession(expire_on_commit=False) as db:
        page = int(page) if page is not None else 1
        limit = JudgeConfig.Judge_Each_Page
        offset = (page - 1) * JudgeConfig.Judge_Each_Page
        query = db.query(JudgeRecord2) \
            .options(defer(JudgeRecord2.details), defer(JudgeRecord2.message)) \
            .options(selectinload(JudgeRecord2.user)) \
            .options(selectinload(JudgeRecord2.problem))
        if arg_submitter is not None:
            query = query.where(JudgeRecord2.username == arg_submitter)
        if arg_problem_id is not None:
            query = query.where(JudgeRecord2.problem_id == arg_problem_id)
        if arg_status is not None:
            query = query.where(JudgeRecord2.status == arg_status)
        if arg_lang is not None:
            query = query.where(JudgeRecord2.language == arg_lang)
        query = query.order_by(JudgeRecord2.id.desc())
        count = query.count()
        max_page = ceil(count / JudgeConfig.Judge_Each_Page)
        query = query.limit(limit).offset(offset)
        submissions: List[JudgeRecord2] = query.all()

    exam_id, is_exam_started = Contest_Manager.get_unfinished_exam_info_for_player(username, unix_nano())
    # if not None, only problems in here are visible to user
    exam_visible_problems = None

    # only change the visibility when the exam started
    if exam_id != -1 and is_exam_started: 
        exam_visible_problems = list()
        exam_problems_raw = Contest_Manager.list_problem_for_contest(exam_id)
        for raw_tuple in exam_problems_raw:
            exam_visible_problems.append(raw_tuple[0])

    real_names = {}
    visible = {}
    languages = {}
    for submission in submissions:
        if is_admin:
            real_names[submission] = Reference_Manager.Query_Realname(submission.user.student_id)
        visible[submission] = (
            is_admin or (
                # user's own problem: username == ele['Username']
                # shared problems are always banned if exam_visible_problems is None (this means user in exam)
                (username == submission.username or (exam_visible_problems is None and submission.public)) 
                # and exam visible check for problems
                and (exam_visible_problems is None or submission.problem_id in exam_visible_problems)
            )
        )
        languages[submission] = 'Unknown' if submission.language not in language_info \
            else language_info[submission.language]
    return render_template('status.html', Pages=gen_page(page, max_page),
                           judge_status_info=judge_status_info, language_info=language_info,
                           submissions=submissions, real_names=real_names, visible=visible,
                           languages=languages,
                           Args=dict(filter(lambda e: e[0] != 'page', request.args.items())),
                           is_Admin=is_admin, friendlyName=Login_Manager.get_friendly_name())


def code_old(run_id):
    if not Login_Manager.check_user_status():  # not login
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    if run_id < 0 or run_id > Judge_Manager.max_id():
        abort(404)
    detail = Judge_Manager.query_judge(run_id)
    if not is_code_visible(detail['User'], detail['Problem_ID'], detail['Share']):
        return abort(403)
    else:
        detail['Friendly_Name'] = User_Manager.get_friendly_name(detail['User'])
        detail['Problem_Title'] = Problem_Manager.get_title(detail['Problem_ID'])
        detail['Lang'] = readable_lang(detail['Lang'])
        detail['Time'] = readable_time(int(detail['Time']))
        data = None
        if detail['Detail'] != 'None':
            temp = json.loads(detail['Detail'])
            detail['Score'] = int(temp[1])
            data = temp[4:]
        else:
            detail['Score'] = 0
        return render_template('judge_detail_old.html', Detail=detail, Data=data,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)

@web.route('/code')
def code_compat():
    submit_id = request.args.get('submit_id')
    if submit_id is None:
        abort(404)
    return redirect(f'/OnlineJudge/code/{submit_id}/')

@web.route('/code/<int:submit_id>/')
def code(submit_id):
    if not Login_Manager.check_user_status():  # not login
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    if submit_id <= Judge_Manager.max_id():
        return code_old(submit_id)
    with SqlSession(expire_on_commit=False) as db:
        submission: JudgeRecord2 = db \
            .query(JudgeRecord2) \
            .options(joinedload(JudgeRecord2.user)) \
            .options(joinedload(JudgeRecord2.problem)) \
            .where(JudgeRecord2.id == submit_id) \
            .one_or_none()
        if submission is None:
            abort(404)
    if not is_code_visible(submission.username, submission.problem_id, submission.public):
        abort(403)

    details = json.loads(submission.details) if submission.details is not None else None
    if details is None and submission.status == JudgeStatus.judging:
        url = f'submission/{quote(str(submission.id))}/status'
        try:
            # TODO: caching
            res = requests.get(urljoin(SchedulerConfig.base_url, url))
            if res.status_code == OK:
                details = res.json()
            elif res.status_code == NOT_FOUND:
                pass
            else:
                raise Exception(f'Unknown status code {res.status_code}')
        except BaseException as e:
            # TODO: error handling
            print(e)
            pass
    if details is not None:
        details = load_dataclass(details, commons.task_typing.__dict__)

    code_url = generate_s3_public_url('get_object', {
        'Bucket': S3Config.Buckets.submissions,
        'Key': key_from_submission_id(submission.id),
    }, ExpiresIn=60)
    language = language_info[submission.language] \
        if submission.language in language_info else 'Unknown'
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    abortable = submission.status in \
        (JudgeStatus.pending, JudgeStatus.compiling, JudgeStatus.judging) and \
        (is_admin or submission.username == Login_Manager.get_username())
    show_score = not abortable and submission.status not in \
        (JudgeStatus.void, JudgeStatus.aborted)

    return render_template('judge_detail.html', submission=submission,
                           enumerate=enumerate, code_url=code_url,
                           details=details, judge_status_info=judge_status_info,
                           language=language, abortable=abortable,
                           show_score=show_score,
                           friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=is_admin)

@web.route('/code/<int:submit_id>/void', methods=['POST'])
def web_mark_void(submit_id):
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(403)
    try:
        mark_void(submit_id)
    except NotFoundException:
        abort(404)
    return redirect('.', SEE_OTHER)


@web.route('/code/<int:submit_id>/rejudge', methods=['POST'])
def web_rejudge(submit_id):
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(403)
    try:
        rejudge(submit_id)
    except NotFoundException:
        abort(404)
    return redirect('.', SEE_OTHER)


@web.route('/code/<int:submit_id>/abort', methods=['POST'])
def web_abort_judge(submit_id):
    if not Login_Manager.check_user_status():  # not login
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    with SqlSession(expire_on_commit=False) as db:
        submission: Optional[Tuple[str, int]] = db \
            .query(JudgeRecord2.username) \
            .where(JudgeRecord2.id == submit_id) \
            .one_or_none()
        if submission is None:
            abort(404)
        username = submission[0]
    if username != Login_Manager.get_username() \
        and Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(403)
    try:
        abort_judge(submit_id)
    except BaseException as e:
        abort(500, str(e))
    return redirect('.', SEE_OTHER)


@web.route('/problem-group/<int:contest_id>')
def problem_group(contest_id):
    if Contest_Manager.get_contest_type(contest_id) == ContestType.HOMEWORK:
        return redirect(f'/OnlineJudge/homework/{contest_id}')
    else:
        return redirect(f'/OnlineJudge/contest/{contest_id}')

@web.route('/contest')
def contest_list():
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    contest_id = request.args.get('contest_id')
    if contest_id is not None:
        return redirect(f'/OnlineJudge/contest/{contest_id}')
    username = Login_Manager.get_username()
    contest_list = Contest_Manager.list_contest_and_exam()
    data = []
    cur_time = unix_nano()
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    exam_id, _ = Contest_Manager.get_unfinished_exam_info_for_player(username, cur_time)
    # here exam_id is an *arbitary* unfinished exam in which the player is in 

    # Blocked: indicate whether the join button should be disabled because time is over
    # Joined: indicate whether the user has joined the contest, join button should also be disabled
    # Exam_Blocked: indicate that the user is in an *arbitary* exam, so even if there are available contests, join button should be disabled
    for ele in contest_list:
        cur = {'ID': int(ele[0]),
               'Title': str(ele[1]),
               'Start_Time': readable_time(int(ele[2])),
               'End_Time': readable_time(int(ele[3])),
               'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
               'Blocked': unix_nano() > int(ele[3]),
               'Exam_Blocked': (exam_id != -1 and ele[4] == 2 and exam_id != int(ele[0]))}
        if cur_time < int(ele[2]):
            cur['Status'] = 'Pending'
        elif cur_time > int(ele[3]):
            cur['Status'] = 'Finished'
        else:
            cur['Status'] = 'Going On'
        data.append(cur)
    
    return render_template('contest_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=is_admin)

@web.route('/contest/<int:contest_id>')
def contest(contest_id):
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    with SqlSession() as db:
        contest = db.query(Contest.id).where(Contest.id == contest_id).one_or_none()
        if contest == None:
            abort(404)
    start_time, end_time = Contest_Manager.get_time(contest_id)
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    problems = Contest_Manager.list_problem_for_contest(contest_id)
    problems_visible = is_admin or unix_nano() >= start_time
    players = Contest_Manager.list_player_for_contest(contest_id)

    data = Contest_Cache.get('contest', contest_id)
    if data is None:
        data = [
            {
                'score': 0,
                'penalty': 0,
                'friendly_name': User_Manager.get_friendly_name(username),
                'problems': [
                    {
                        'score': 0,
                        'count': 0,
                        'accepted': False,
                    } for _ in problems
                ],
                'realname': Reference_Manager.Query_Realname(User_Manager.get_student_id(username)),
                'student_id': User_Manager.get_student_id(username),
                'username': username,
            } for username in players
        ]
        username_to_num = dict(map(lambda entry: [regularize_string(entry[1]), entry[0]], enumerate(players)))
        problem_to_num = dict(map(lambda entry: [entry[1][0], entry[0]], enumerate(problems)))

        with SqlSession() as db:
            submits = db \
                .query(JudgeRecord2) \
                .options(defer(JudgeRecord2.details), defer(JudgeRecord2.message)) \
                .where(JudgeRecord2.problem_id.in_(problems)) \
                .where(JudgeRecord2.username.in_(players)) \
                .where(JudgeRecord2.created >= datetime.datetime.fromtimestamp(start_time)) \
                .where(JudgeRecord2.created < datetime.datetime.fromtimestamp(end_time)) \
                .all()
        for submit in submits:
            username = submit.username
            problem_id = submit.problem_id
            status = 2 if submit.status == JudgeStatus.accepted else -1
            score = submit.score
            submit_time = submit.created.timestamp()

            if regularize_string(username) not in username_to_num:
                continue

            rank = username_to_num[regularize_string(username)]
            problem_index = problem_to_num[problem_id]
            user_data = data[rank]
            problem = user_data['problems'][problem_index]

            if problem['accepted'] == True:
                continue
            max_score = problem['score']
            # FIXME: magic number 2 for AC
            is_ac = int(status) == 2
            submit_count = problem['count']

            if int(score) > max_score:
                user_data['score'] -= max_score
                max_score = int(score)
                user_data['score'] += max_score

            submit_count += 1

            if is_ac:
                user_data['penalty'] += (int(submit_time) - start_time + (submit_count - 1) * 1200) // 60

            problem['score'] = max_score
            problem['count'] = submit_count
            problem['accepted'] = is_ac

        Contest_Cache.put('contest', contest_id, data)    

    cur_time = unix_nano()
    if cur_time < start_time:
        contest_status = 'Pending'
    elif cur_time > end_time:
        contest_status = 'Finished'
    else:
        contest_status = 'Going On'
    data = sorted(data, key=cmp_to_key(lambda x, y: y['score'] - x['score'] if x['score'] != y['score'] else x['penalty'] - y['penalty']))
    title = Contest_Manager.get_title(contest_id)[0][0]

    time_elapsed = float(unix_nano() - start_time)
    time_overall = float(end_time - start_time)
    percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)

    status_url = 'status'
    ac_status = 'accepted'

    return render_template(
        'contest.html',
        id=contest_id,
        Title=title,
        Status=contest_status,
        StartTime=readable_time(start_time),
        EndTime=readable_time(end_time),
        Problems=problems,
        problems_visible=problems_visible,
        data=data,
        status_url=status_url,
        ac_status=ac_status,
        is_Admin=is_admin,
        Percentage=percentage,
        friendlyName=Login_Manager.get_friendly_name(),
        enumerate=enumerate,
    )


@web.route('/homework')
def homework_list():
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    contest_id = request.args.get('homework_id')
    if contest_id is not None:  # display contest list
        return redirect(f'/OnlineJudge/homework/{contest_id}')
    username = Login_Manager.get_username()
    contest_list = Contest_Manager.list_contest(1)
    data = []
    cur_time = unix_nano()
    for ele in contest_list:
        cur = {'ID': int(ele[0]),
               'Title': str(ele[1]),
               'Start_Time': readable_time(int(ele[2])),
               'End_Time': readable_time(int(ele[3])),
               'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
               'Blocked': unix_nano() > int(ele[3])}
        if cur_time < int(ele[2]):
            cur['Status'] = 'Pending'
        elif cur_time > int(ele[3]):
            cur['Status'] = 'Finished'
        else:
            cur['Status'] = 'Going On'
        data.append(cur)
    return render_template('homework_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/homework/<int:contest_id>')
def homework(contest_id):
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    with SqlSession() as db:
        contest = db.query(Contest.id).where(Contest.id == contest_id).one_or_none()
        if contest == None:
            abort(404)            
    start_time, end_time = Contest_Manager.get_time(contest_id)
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
    problems = Contest_Manager.list_problem_for_contest(contest_id)
    problems_visible = is_admin or unix_nano() >= start_time
    players = Contest_Manager.list_player_for_contest(contest_id)

    data = Contest_Cache.get('homework', contest_id)

    if data is None:
        data = [
            {
                'ac_count': 0,
                'friendly_name': User_Manager.get_friendly_name(username),
                'problems': [
                    {
                        'accepted': False,
                        'count': 0,
                    } for _ in problems
                ],
                'realname': Reference_Manager.Query_Realname(User_Manager.get_student_id(username)),
                'student_id': User_Manager.get_student_id(username),
                'username': username,
            } for username in players
        ]
        username_to_num = dict(map(lambda entry: [regularize_string(entry[1]), entry[0]], enumerate(players)))
        problem_to_num = dict(map(lambda entry: [entry[1][0], entry[0]], enumerate(problems)))

        with SqlSession() as db:
            submits = db \
                .query(JudgeRecord2) \
                .options(defer(JudgeRecord2.details), defer(JudgeRecord2.message)) \
                .where(JudgeRecord2.problem_id.in_(problems)) \
                .where(JudgeRecord2.username.in_(players)) \
                .where(JudgeRecord2.created >= datetime.datetime.fromtimestamp(start_time)) \
                .where(JudgeRecord2.created < datetime.datetime.fromtimestamp(end_time)) \
                .all()

        for submit in submits:
            username = submit.username
            problem_id = submit.problem_id

            if regularize_string(username) not in username_to_num:
                continue

            user_num = username_to_num[regularize_string(username)]
            problem_index = problem_to_num[problem_id]
            user_data = data[user_num]
            problem = user_data['problems'][problem_index]

            if problem['accepted'] == True:
                continue

            if submit.status == JudgeStatus.accepted:
                problem['accepted'] = True
                user_data['ac_count'] += 1

            problem['count'] += 1

        Contest_Cache.put('homework', contest_id, data)    

    cur_time = unix_nano()
    if cur_time < start_time:
        contest_status = 'Pending'
    elif cur_time > end_time:
        contest_status = 'Finished'
    else:
        contest_status = 'Going On'
    title = Contest_Manager.get_title(contest_id)[0][0]

    time_elapsed = float(unix_nano() - start_time)
    time_overall = float(end_time - start_time)
    percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)

    status_url = 'status'
    ac_status = 'accepted'

    return render_template(
        'homework.html',
        id=contest_id,
        Title=title,
        Status=contest_status,
        StartTime=readable_time(start_time),
        EndTime=readable_time(end_time),
        Problems=problems,
        problems_visible=problems_visible,
        Players=players,
        data=data,
        status_url=status_url,
        ac_status=ac_status,
        is_Admin=is_admin,
        Percentage=percentage,
        friendlyName=Login_Manager.get_friendly_name(),
        enumerate=enumerate,
    )

@web.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('/OnlineJudge/login?next=' + request.full_path)
        return render_template('profile.html', friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        if not Login_Manager.check_user_status():
            return ReturnCode.ERR_USER_NOT_LOGGED_IN
        form = request.json
        try:
            ret = validate(password=form.get('password'), friendly_name=form.get('friendly_name'))
            if ret == ReturnCode.SUC_VALIDATE:
                User_Manager.modify_user(Login_Manager.get_username(), None, form.get('friendly_name'), form.get(
                    'password'), None)
                return ReturnCode.SUC_MOD_USER

        except KeyError:
            return ReturnCode.ERR_BAD_DATA
        except TypeError:
            return ReturnCode.ERR_BAD_DATA


@web.route('/about')
def about():
    with SqlSession(expire_on_commit=False) as db:
        runner2s: List[JudgeRunner2] = db \
            .query(JudgeRunner2) \
            .order_by(JudgeRunner2.id) \
            .all()
    if len(runner2s) == 0:
        runner2_dict = {}
        runner2_list = []
    else:
        query = urlencode({'id': ','.join(str(x.id) for x in runner2s)})
        url = urljoin(SchedulerConfig.base_url, f'status?{query}')
        try:
            runner2_res = requests.get(url)
        except Exception as e:
            print(e)
            abort(500, '无法获取评测机状态')
        if runner2_res.status_code != OK:
            abort(500)
        runner2_dict = runner2_res.json()
        runner2_list = []
        for runner in runner2s:
            r = runner2_dict[str(runner.id)]
            r['id'] = str(runner.id)
            r['name'] = runner.name
            r['hardware'] = runner.hardware
            r['provider'] = runner.provider
            if r['last_seen'] is not None:
                r['last_seen'] = readable_time(r['last_seen'])
            else:
                r['last_seen'] = 'N/A'
            status_info = runner_status_info[r['status']]
            r['status'] = status_info.name
            r['status_color'] = status_info.color
            runner2_list.append(r)
    return render_template('about.html',
                           runner2=runner2_list,
                           mntners=mntners, contributors=contributors,
                           friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(web.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')

oj = Flask('WEB')
oj.register_blueprint(web, url_prefix='/OnlineJudge')
oj.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400
