import json
import os
import re
from datetime import datetime
from http.client import (BAD_REQUEST, FORBIDDEN, INTERNAL_SERVER_ERROR,
                         NOT_FOUND, OK, REQUEST_ENTITY_TOO_LARGE, SEE_OTHER,
                         UNAUTHORIZED)
from math import ceil
from typing import List, Optional, Tuple
from urllib.parse import quote, urlencode, urljoin
from uuid import uuid4

import requests
import sqlalchemy as sa
from flask import (Blueprint, Flask, abort, make_response, redirect,
                   render_template, request, send_from_directory)
from sqlalchemy.orm import defer, selectinload

import commons.task_typing
from commons.models import ContestProblem, JudgeRecord2, JudgeStatus, Problem, User
from commons.task_typing import ProblemJudgeResult
from commons.util import load_dataclass, serialize
from web.admin import admin
from web.config import (JudgeConfig, LoginConfig, ProblemConfig,
                        QuizTempDataConfig, S3Config, SchedulerConfig,
                        WebConfig)
from web.const import (Privilege, ReturnCode, contributors, judge_status_info,
                       language_info, mntners, runner_status_info)
from web.contest_manager import ContestManager
from web.discuss_manager import DiscussManager
from web.judge_manager import JudgeManager, NotFoundException
from web.old_judge_manager import OldJudgeManager
from web.problem_manager import ProblemManager
from web.quiz_manager import QuizManager
from web.realname_manager import RealnameManager
from web.session_manager import SessionManager
from web.tracker import tracker
from web.user_manager import UserManager
from web.utils import (SqlSession, gen_page, gen_page_for_problem_list,
                       generate_s3_public_url, readable_time, unix_nano)
from web.template_interface import RowJudgeStatus

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
    password_reg = '([\x20-\x7e]{6,128})$'
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
    if username is not None and UserManager.has_user(username):
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
    exam_id, is_exam_started = ContestManager.get_unfinished_exam_info_for_player(SessionManager.get_username(), unix_nano())

    if exam_id == -1 or is_exam_started == False:
        return False

    return SessionManager.get_privilege() < Privilege.ADMIN and ContestManager.check_problem_in_contest(exam_id, problem_id)


def is_code_visible(code_owner, problem_id, shared):
    # Check whether the code is visible.

    # admin always visible
    if SessionManager.get_privilege() >= Privilege.ADMIN:
        return True

    username = SessionManager.get_username()
    # exam first
    exam_id, is_exam_started = ContestManager.get_unfinished_exam_info_for_player(username, unix_nano())

    if exam_id != -1 and is_exam_started:
        # if the user is in a running exam, he can only see his own problems in exam.
        return code_owner == username and ContestManager.check_problem_in_contest(exam_id, problem_id)
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
        friendlyName = SessionManager.get_friendly_name(),
        is_Admin = SessionManager.get_privilege() >= Privilege.ADMIN
    )


@web.route('/index.html')
def index2():
    return redirect('/')


@web.route('/api/get_username', methods=['POST'])
def get_username():
    return SessionManager.get_friendly_name()


@web.route('/api/get_problem_id_autoinc', methods=['POST'])
def get_problem_id_autoinc():
    return str(ProblemManager.get_max_id() + 1)

@web.route('/api/get_contest_id_autoinc', methods=['POST'])
def get_contest_id_autoinc():
    return str(ContestManager.get_max_id() + 1)

@web.route('/api/get_detail', methods=['POST'])
def get_detail():
    if not SessionManager.check_user_status():
        return '-1'
    problem_id = request.form.get('problem_id')
    problem = ProblemManager.get_problem(problem_id)
    if not ProblemManager.should_show(problem):
        return '-1'
    data = {
        'ID': problem.id,
        'Title': problem.title,
        'Description': str(problem.description),
        'Input': str(problem.input),
        'Output': str(problem.output),
        'Example_Input': str(problem.example_input),
        'Example_Output': str(problem.example_output),
        'Data_Range': str(problem.data_range),
        'Release_Time': problem.release_time,
        'Problem_Type': problem.problem_type,
        'Limits': str(problem.limits),
    }
    return json.dumps(data)

@web.route('/api/get_contest_detail', methods=['POST'])
def get_contest_detail():
    if not SessionManager.check_user_status():
        return '-1'
    contest_id = request.form.get('contest_id')
    contest = ContestManager.get_contest(contest_id)
    if contest is None:
        return '{}'
    data = {
        'ID': contest.id,
        'Name': contest.name,
        'Start_Time': contest.start_time,
        'End_Time': contest.end_time,
        'Type': contest.type,
        'Ranked': contest.ranked,
        'Rank_Penalty': contest.rank_penalty,
        'Rank_Partial_Score': contest.rank_partial_score,
    }
    return json.dumps(data)

@web.route('/api/join', methods=['POST'])
def join_contest():
    if not SessionManager.check_user_status():
        return '-1'
    arg = request.form.get('contest_id')
    if arg is None:
        return '-1'
    st, ed = ContestManager.get_time(arg)
    if unix_nano() > ed:
        return '-1'
    username = SessionManager.get_username()
    exam_id, _ = ContestManager.get_unfinished_exam_info_for_player(username, unix_nano())
    if exam_id != -1:
        return '-1'
    if not ContestManager.check_player_in_contest(arg, username):
        ContestManager.add_player_to_contest(arg, username)
    return '0'


@web.route('/api/code', methods=['POST'])
def get_code():
    if not SessionManager.check_user_status():
        return '-1'
    arg = request.form.get('submit_id')
    if arg is None:
        return '-1'
    if not str(request.form.get('submit_id')).isdigit():  # bad argument
        return '-1'
    run_id = int(request.form.get('submit_id'))
    if run_id < 0 or run_id > OldJudgeManager.max_id():
        return '-1'
    detail = OldJudgeManager.query_judge(run_id)
    if not is_code_visible(detail['User'], detail['Problem_ID'], detail['Share']):
        return '-1'
    return detail['Code']


@web.route('/api/quiz', methods=['POST'])
def get_quiz():
    if not SessionManager.check_user_status():
        return ReturnCode.ERR_USER_NOT_LOGGED_IN
    problem_id = request.form.get('problem_id')
    if problem_id is None:
        return ReturnCode.ERR_BAD_DATA
    if not str(problem_id).isdigit():  # bad argument
        return ReturnCode.ERR_BAD_DATA
    problem_id = int(problem_id)
    problem = ProblemManager.get_problem(problem_id)
    if not ProblemManager.should_show(problem):
        return ReturnCode.ERR_BAD_DATA
    if problem.problem_type != 1:
        return ReturnCode.ERR_PROBLEM_NOT_QUIZ
    quiz_json = QuizManager.get_json_from_data_service_by_id(QuizTempDataConfig, problem_id)
    if quiz_json['e'] == 0:
        for i in quiz_json["problems"]:
            i["answer"] = ""
    return json.dumps(quiz_json)


@web.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        nxt = request.args.get('next')
        nxt = '/' if nxt is None else nxt
        return render_template('login.html', Next=nxt, friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    if username.endswith("mirror"):
        return ReturnCode.ERR_LOGIN_MIRROR
    if not UserManager.check_login(username, password):  # no need to avoid sql injection
        return ReturnCode.ERR_LOGIN
    lid = str(uuid4())
    username = UserManager.get_canonical_username(username)
    SessionManager.new_session(username, lid)
    ret = make_response(ReturnCode.SUC_LOGIN)
    ret.set_cookie(key='Login_ID', value=lid, max_age=LoginConfig.Login_Life_Time)
    return ret


@web.route('/logout')
def logout():
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/')
    ret = make_response(redirect('/OnlineJudge/'))
    ret.delete_cookie('Login_ID')
    return ret


@web.route('/register', methods=['GET', 'POST'])
def register():
    if WebConfig.Block_Register:
        abort(NOT_FOUND)
    if request.method == 'GET':
        nxt = request.args.get('next')
        return render_template('register.html', Next=nxt, friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    friendly_name = request.form.get('friendly_name')
    student_id = request.form.get('student_id')
    val = validate(username, password, friendly_name, student_id)
    if val == ReturnCode.SUC_VALIDATE:
        UserManager.add_user(username, student_id, friendly_name, password, '0')
        return ReturnCode.SUC_REGISTER
    else:
        return val


@web.route('/problem')
def problem_list():
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    is_admin = bool(SessionManager.get_privilege() >= Privilege.ADMIN)
    page = request.args.get('page')
    page = int(page) if page else 1

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

    with SqlSession(expire_on_commit=False) as db:
        limit = WebConfig.Problems_Each_Page
        offset = (page - 1) * WebConfig.Problems_Each_Page
        query = db.query(Problem.id, Problem.title, Problem.problem_type)
        if not is_admin:
            query = query.where(Problem.release_time <= unix_nano())
        if problem_name_keyword is not None:
            query = query.where(sa.func.instr(Problem.title, problem_name_keyword) > 0)
        if problem_type is not None:
            query = query.where(Problem.problem_type == problem_type)
        if contest_id is not None:
            problem_ids = ContestManager.list_problem_for_contest(contest_id)
            query = query.where(Problem.id.in_(problem_ids))
        count_under_11000 = query.where(Problem.id <= 11000).count()
        max_page_under_11000 = ceil(count_under_11000 / WebConfig.Problems_Each_Page)
        count = query.count()
        max_page = ceil(count / WebConfig.Problems_Each_Page)
        problems: List[Problem] = query \
            .order_by(Problem.id.asc()) \
            .limit(limit).offset(offset) \
            .all()

    return render_template('problem_list.html', problems=problems,
                            pages=gen_page_for_problem_list(page, max_page, max_page_under_11000),
                            args=dict(filter(lambda e: e[0] != 'page', request.args.items())),
                            friendlyName=SessionManager.get_friendly_name(),
                            is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)

@web.route('/problem/<int:problem_id>')
def problem_detail(problem_id):
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    problem = ProblemManager.get_problem(problem_id)
    if not ProblemManager.should_show(problem):
        abort(NOT_FOUND)

    in_exam = problem_in_exam(problem_id)

    return render_template('problem_details.html', ID=problem_id, Title=problem.title,
                           In_Exam=in_exam, friendlyName=SessionManager.get_friendly_name(),
                           is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)


@web.route('/problem/<int:problem_id>/admin', methods=['GET', 'POST'])
def problem_admin(problem_id):
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    is_admin = SessionManager.get_privilege() >= Privilege.ADMIN
    if not is_admin:
        abort(NOT_FOUND)

    now = datetime.now().timestamp()
    if request.method == 'POST':
        action = request.form['action']
        if action == 'hide':
            ProblemManager.hide_problem(problem_id)
        elif action == 'show':
            ProblemManager.show_problem(problem_id)
        elif action == 'delete':
            if request.form['confirm'] != str(problem_id):
                abort(BAD_REQUEST)
            ProblemManager.delete_problem(problem_id)
            return redirect('/OnlineJudge/admin/')
        else:
            abort(BAD_REQUEST)

    with SqlSession(expire_on_commit=False) as db:
        problem = db.query(Problem).where(Problem.id == problem_id).one_or_none()
        if problem is None:
            abort(NOT_FOUND)
        submission_count = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).count()
        ac_count = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).where(JudgeRecord2.status == JudgeStatus.accepted).count()
        contests = db.query(ContestProblem.contest_id).where(ContestProblem.problem_id == problem_id).all()
        contests = [ x.contest_id for x in contests ]

    in_exam = problem_in_exam(problem_id)

    return render_template('problem_admin.html', ID=problem_id, Title=problem.title,
                           In_Exam=in_exam, friendlyName=SessionManager.get_friendly_name(),
                           problem=problem, now=now, contests=contests,
                           submission_count=submission_count, ac_count=ac_count,
                           is_Admin=is_admin)


@web.route('/problem/<int:problem_id>/submit', methods=['GET', 'POST'])
def submit_problem(problem_id):
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    problem = ProblemManager.get_problem(problem_id)
    if not ProblemManager.should_show(problem):
        abort(NOT_FOUND)

    if request.method == 'GET':
        title = problem.title
        problem_type = problem.problem_type
        in_exam = problem_in_exam(problem_id)
        if problem_type == 0:
            return render_template('problem_submit.html', Problem_ID=problem_id, Title=title, In_Exam=in_exam,
                               friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)
        elif problem_type == 1:
            return render_template('quiz_submit.html', Problem_ID=problem_id, Title=title, In_Exam=in_exam,
                               friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)
    else:
        public = bool(request.form.get('shared', 0))  # 0 or 1
        username = SessionManager.get_username()
        lang_request_str = str(request.form.get('lang'))
        if lang_request_str == 'quiz':
            user_code = json.dumps(request.form.to_dict())
        else:
            user_code = request.form.get('code')
        if len(str(user_code)) > ProblemConfig.Max_Code_Length:
            abort(REQUEST_ENTITY_TOO_LARGE)
        lang_str = lang_request_str.lower()
        submission_id = JudgeManager.add_submission(
            public=public,
            language=lang_str,
            username=username,
            problem_id=problem_id,
            code=user_code,
        )
        return str(submission_id)


def check_scheduler_auth():
    auth = request.headers.get('Authorization', '')
    if auth != SchedulerConfig.auth:
        abort(UNAUTHORIZED)


@web.route('/api/submission/<submission_id>/status', methods=['PUT'])
def set_status(submission_id):
    check_scheduler_auth()
    status = request.get_data(as_text=True)
    if status not in ('compiling', 'judging'):
        print(status)
        abort(BAD_REQUEST)
    JudgeManager.set_status(submission_id, status)
    return ''


@web.route('/api/submission/<submission_id>/result', methods=['PUT'])
def set_result(submission_id):
    check_scheduler_auth()
    classes = commons.task_typing.__dict__
    res: ProblemJudgeResult = load_dataclass(request.json, classes)
    time_msecs = None
    memory_bytes = None
    if res is not None and res.resource_usage is not None:
        time_msecs = res.resource_usage.time_msecs
        memory_bytes = res.resource_usage.memory_bytes
    JudgeManager.set_result(
        submission_id,
        score=int(res.score),
        status=res.result,
        message=res.message,
        details=serialize(res),
        time_msecs=time_msecs,
        memory_bytes=memory_bytes,
    )
    return ''


@web.route('/problem/<int:problem_id>/rank')
def problem_rank(problem_id):
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    sort_parameter = request.args.get('sort')
    is_admin = SessionManager.get_privilege() >= Privilege.ADMIN

    submissions = JudgeManager.list_accepted_submissions(problem_id)
    real_names = {}
    languages = {}
    for submission in submissions:
        if is_admin:
            real_names[submission] = RealnameManager.query_realname(submission.user.student_id)
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

    return render_template('problem_rank.html', Problem_ID=problem_id, Title=ProblemManager.get_title(problem_id),
                           submissions=submissions, Sorting=sort_parameter, friendlyName=SessionManager.get_friendly_name(),
                           readable_lang=readable_lang, readable_time=readable_time,
                           is_Admin=is_admin, real_names=real_names, languages=languages,
                           In_Exam=in_exam)


@web.route('/problem/<int:problem_id>/discuss', methods=['GET', 'POST'])
def discuss(problem_id):
    if request.method == 'GET':
        if not SessionManager.check_user_status():
            return redirect('/OnlineJudge/login?next=' + request.full_path)

        in_exam = problem_in_exam(problem_id)

        if in_exam:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID=problem_id,
                                   Title=ProblemManager.get_title(problem_id), Blocked=True,
                                   friendlyName=SessionManager.get_friendly_name(),
                                   is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN,
                                   In_Exam=True)  # Discussion Closed
        username = SessionManager.get_username()  # for whether to display edit or delete
        privilege = SessionManager.get_privilege()
        data = DiscussManager.get_discuss_for_problem(problem_id)
        discussion = []
        for ele in data:
            tmp = [ele.id, UserManager.get_friendly_name(ele.username), ele.data, readable_time(int(ele.time))]
            # tmp[4]: editable
            tmp.append(ele.username == username or privilege >= Privilege.SUPER)
            discussion.append(tmp)
        return render_template('problem_discussion.html', Problem_ID=problem_id,
                               Title=ProblemManager.get_title(problem_id), Discuss=discussion,
                               friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN,
                               In_Exam=False)
    else:
        if not SessionManager.check_user_status():
            return ReturnCode.ERR_USER_NOT_LOGGED_IN
        try:
            form = request.json
            action = form.get('action')  # post, edit, delete
            if action == 'post':
                text = form.get('text')
                username = SessionManager.get_username()
                if SessionManager.get_privilege() >= Privilege.ADMIN:    # administrator
                    DiscussManager.add_discuss(problem_id, username, text)
                    return ReturnCode.SUC
                else:
                    print('Access Denied in Discuss: Add')
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'edit':
                discuss_id = form.get('discuss_id')
                text = form.get('text')
                username = SessionManager.get_username()
                if username == DiscussManager.get_author(
                        discuss_id) or SessionManager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                    DiscussManager.modify_discuss(discuss_id, text)
                    return ReturnCode.SUC
                else:
                    print('Access Denied in Discuss: Edit')
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'delete':
                discuss_id = form.get('discuss_id')
                username = SessionManager.get_username()
                if username == DiscussManager.get_author(
                        discuss_id) or SessionManager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                    DiscussManager.delete_discuss(discuss_id)
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
    if not SessionManager.check_user_status():
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
            abort(BAD_REQUEST)
    arg_lang = request.args.get('lang')
    if arg_lang == '':
        arg_lang = None
    username = SessionManager.get_username()
    is_admin = SessionManager.get_privilege() >= Privilege.ADMIN

    with SqlSession(expire_on_commit=False) as db:
        page = int(page) if page is not None else 1
        limit = JudgeConfig.Judge_Each_Page
        offset = (page - 1) * JudgeConfig.Judge_Each_Page
        query = db.query(JudgeRecord2) \
            .options(defer(JudgeRecord2.details), defer(JudgeRecord2.message)) \
            .options(selectinload(JudgeRecord2.user).load_only(User.student_id, User.friendly_name)) \
            .options(selectinload(JudgeRecord2.problem).load_only(Problem.title))
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
        submissions: List[RowJudgeStatus] = query.all()

    exam_id, is_exam_started = ContestManager.get_unfinished_exam_info_for_player(username, unix_nano())
    # if not None, only problems in here are visible to user
    exam_visible_problems = None

    # only change the visibility when the exam started
    if exam_id != -1 and is_exam_started:
        exam_visible_problems = ContestManager.list_problem_for_contest(exam_id)

    for submission in submissions:
        if is_admin:
            submission.real_name = RealnameManager.query_realname(submission.user.student_id)
        submission.visible = (
            is_admin or (
                # user's own problem: username == ele['Username']
                # shared problems are always banned if exam_visible_problems is None (this means user in exam)
                (username == submission.username or (exam_visible_problems is None and submission.public))
                # and exam visible check for problems
                and (exam_visible_problems is None or submission.problem_id in exam_visible_problems)
            )
        )
        submission.language = 'Unknown' if submission.language not in language_info \
            else language_info[submission.language]
    return render_template('status.html', pages=gen_page(page, max_page),
                           judge_status_info=judge_status_info, language_info=language_info,
                           submissions=submissions,
                           args=dict(filter(lambda e: e[0] != 'page', request.args.items())),
                           is_Admin=is_admin, friendlyName=SessionManager.get_friendly_name())


def code_old(run_id):
    if not SessionManager.check_user_status():  # not login
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    if run_id < 0 or run_id > OldJudgeManager.max_id():
        abort(NOT_FOUND)
    detail = OldJudgeManager.query_judge(run_id)
    if not is_code_visible(detail['User'], detail['Problem_ID'], detail['Share']):
        abort(FORBIDDEN)
    else:
        detail['Friendly_Name'] = UserManager.get_friendly_name(detail['User'])
        detail['Problem_Title'] = ProblemManager.get_title(detail['Problem_ID'])
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
                               friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)

@web.route('/code')
def code_compat():
    submit_id = request.args.get('submit_id')
    if submit_id is None:
        abort(NOT_FOUND)
    return redirect(f'/OnlineJudge/code/{submit_id}/')

@web.route('/code/<int:submission_id>/')
def code(submission_id):
    if not SessionManager.check_user_status():  # not login
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    if submission_id <= OldJudgeManager.max_id():
        return code_old(submission_id)
    submission: RowJudgeStatus = JudgeManager.get_submission(submission_id)
    if submission is None:
        abort(NOT_FOUND)
    if not is_code_visible(submission.username, submission.problem_id, submission.public):
        abort(FORBIDDEN)

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
        'Key': JudgeManager.key_from_submission_id(submission.id),
    }, ExpiresIn=60)
    is_admin = SessionManager.get_privilege() >= Privilege.ADMIN
    abortable = submission.status in \
        (JudgeStatus.pending, JudgeStatus.compiling, JudgeStatus.judging) and \
        (is_admin or submission.username == SessionManager.get_username())
    show_score = not abortable and submission.status not in \
        (JudgeStatus.void, JudgeStatus.aborted)
    submission.real_name = RealnameManager.query_realname(submission.user.student_id) if is_admin else ''
    submission.language = language_info[submission.language] \
        if submission.language in language_info else 'Unknown'
    if details is not None and details.resource_usage is not None:
        submission.time_msecs = details.resource_usage.time_msecs
        submission.memory_bytes = details.resource_usage.memory_bytes
        show_time = True
        show_memory = True
    else:
        show_time = False
        show_memory = False
    return render_template('judge_detail.html', submissions=[submission],
                           enumerate=enumerate, code_url=code_url,
                           details=details, judge_status_info=judge_status_info,
                           abortable=abortable,
                           show_score=show_score,
                           show_time=show_time,
                           show_memory=show_memory,
                           friendlyName=SessionManager.get_friendly_name(),
                           is_Admin=is_admin)

@web.route('/code/<int:submit_id>/void', methods=['POST'])
def mark_void(submit_id):
    if SessionManager.get_privilege() < Privilege.ADMIN:
        abort(FORBIDDEN)
    try:
        JudgeManager.mark_void(submit_id)
    except NotFoundException:
        abort(NOT_FOUND)
    return redirect('.', SEE_OTHER)


@web.route('/code/<int:submit_id>/rejudge', methods=['POST'])
def rejudge(submit_id):
    if SessionManager.get_privilege() < Privilege.ADMIN:
        abort(FORBIDDEN)
    try:
        JudgeManager.rejudge(submit_id)
    except NotFoundException:
        abort(NOT_FOUND)
    return redirect('.', SEE_OTHER)


@web.route('/code/<int:submit_id>/abort', methods=['POST'])
def abort_judge(submit_id):
    if not SessionManager.check_user_status():  # not login
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    with SqlSession(expire_on_commit=False) as db:
        submission: Optional[Tuple[str, int]] = db \
            .query(JudgeRecord2.username) \
            .where(JudgeRecord2.id == submit_id) \
            .one_or_none()
        if submission is None:
            abort(NOT_FOUND)
        username = submission[0]
    if username != SessionManager.get_username() \
        and SessionManager.get_privilege() < Privilege.ADMIN:
        abort(FORBIDDEN)
    try:
        JudgeManager.abort_judge(submit_id)
    except BaseException as e:
        abort(INTERNAL_SERVER_ERROR, str(e))
    return redirect('.', SEE_OTHER)


def contest_list_generic(type, type_zh):
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    contest_id = request.args.get(f'{type}_id')
    if contest_id is not None:
        return redirect(f'/OnlineJudge/problemset/{contest_id}')
    username = SessionManager.get_username()
    is_admin = SessionManager.get_privilege() >= Privilege.ADMIN
    user_contests = UserManager.list_contests(username)

    page = request.args.get('page')
    page = int(page) if page else 1
    type_ids = [0, 2] if type == 'contest' else [1]
    keyword = request.args.get('keyword')
    status = request.args.get('status')
    count, contests = ContestManager.list_contest(type_ids, page, WebConfig.Contests_Each_Page, keyword=keyword, status=status)
    current_time = unix_nano()

    max_page = ceil(count / WebConfig.Contests_Each_Page)
    # here exam_id is an *arbitary* unfinished exam in which the player is in
    exam_id, _ = ContestManager.get_unfinished_exam_info_for_player(username, current_time)

    return render_template('contest_list.html', contests=contests, friendlyName=SessionManager.get_friendly_name(),
                           current_time=current_time, readable_time=readable_time, get_status=ContestManager.get_status,
                           user_contests=user_contests, exam_id=exam_id,
                           is_Admin=is_admin, type=type, type_zh=type_zh,
                           pages=gen_page(page, max_page),
                           args=dict(filter(lambda e: e[0] != 'page' and e[0] != 'all', request.args.items())))

@web.route('/contest')
def contest_list():
    return contest_list_generic('contest', '比赛')

@web.route('/homework')
def homework_list():
    return contest_list_generic('homework', '作业')

@web.route('/contest/<int:contest_id>')
def contest(contest_id):
    return redirect(f'/OnlineJudge/problemset/{contest_id}')
@web.route('/homework/<int:contest_id>')
def homework(contest_id):
    return redirect(f'/OnlineJudge/problemset/{contest_id}')

@web.route('/problemset/<int:contest_id>')
def problemset(contest_id):
    if not SessionManager.check_user_status():
        return redirect('/OnlineJudge/login?next=' + request.full_path)
    contest = ContestManager.get_contest_for_board(contest_id)
    if contest == None:
        abort(NOT_FOUND)

    is_admin = SessionManager.get_privilege() >= Privilege.ADMIN
    problems = ContestManager.list_problem_for_contest(contest_id)
    problems_visible = is_admin or unix_nano() >= contest.start_time
    data = ContestManager.get_board_view(contest)
    contest_status = ContestManager.get_status(contest)

    time_elapsed = float(unix_nano() - contest.start_time)
    time_overall = float(contest.end_time - contest.start_time)
    percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)

    return render_template(
        'contest.html',
        contest=contest,
        start_time=readable_time(contest.start_time),
        end_time=readable_time(contest.end_time),
        problems=problems,
        status=contest_status,
        percentage=percentage,
        problems_visible=problems_visible,
        data=data,
        is_Admin=is_admin,
        friendlyName=SessionManager.get_friendly_name(),
        enumerate=enumerate,
    )


@web.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'GET':
        if not SessionManager.check_user_status():
            return redirect('/OnlineJudge/login?next=' + request.full_path)
        return render_template('profile.html', friendlyName=SessionManager.get_friendly_name(),
                               is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)
    else:
        if not SessionManager.check_user_status():
            return ReturnCode.ERR_USER_NOT_LOGGED_IN
        form = request.json
        try:
            ret = validate(password=form.get('password'), friendly_name=form.get('friendly_name'))
            if ret == ReturnCode.SUC_VALIDATE:
                UserManager.modify_user(SessionManager.get_username(), None, form.get('friendly_name'), form.get(
                    'password'), None)
                return ReturnCode.SUC_MOD_USER
            else:
                return ret

        except KeyError:
            return ReturnCode.ERR_BAD_DATA
        except TypeError:
            return ReturnCode.ERR_BAD_DATA


@web.route('/about')
def about():
    runners = JudgeManager.list_runners()
    if len(runners) == 0:
        runner_dict = {}
        runner_list = []
    else:
        query = urlencode({'id': ','.join(str(x.id) for x in runners)})
        url = urljoin(SchedulerConfig.base_url, f'status?{query}')
        try:
            runner_res = requests.get(url)
            runner_success = True
        except Exception as e:
            print(e)
            runner_res = None
        if runner_res is None or runner_res.status_code != OK:
            runner_success = False
            runner_list = []
        else:
            runner_dict = runner_res.json()
            runner_list = []
            for runner in runners:
                r = runner_dict[str(runner.id)]
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
                runner_list.append(r)
    return render_template('about.html',
                           runners=runner_list, runner_success=runner_success,
                           mntners=mntners, contributors=contributors,
                           friendlyName=SessionManager.get_friendly_name(),
                           is_Admin=SessionManager.get_privilege() >= Privilege.ADMIN)


@web.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(web.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')

oj = Flask('WEB')
oj.register_blueprint(web, url_prefix='/OnlineJudge')
oj.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400
