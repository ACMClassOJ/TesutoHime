import json
import os
import re
from datetime import datetime
from functools import wraps
from http.client import (BAD_REQUEST, FORBIDDEN, INTERNAL_SERVER_ERROR,
                         NOT_FOUND, OK, REQUEST_ENTITY_TOO_LARGE, SEE_OTHER,
                         UNAUTHORIZED)
from math import ceil
from typing import List, Optional
from urllib.parse import quote, urlencode, urljoin
from uuid import uuid4

import requests
import sqlalchemy as sa
from flask import (Blueprint, Flask, abort, g, make_response, redirect,
                   render_template, request, send_from_directory)
from sqlalchemy.orm import defer, selectinload
from werkzeug.exceptions import HTTPException
from werkzeug.routing import BaseConverter

import commons.task_typing
import web.const as consts
import web.utils as utils
from commons.models import (Contest, Course, CourseTag, Enrollment, Group,
                            JudgeRecordV2, JudgeStatus, Problem,
                            RealnameReference, Term, User)
from commons.task_typing import ProblemJudgeResult
from commons.util import deserialize, format_exc, load_dataclass, serialize
from web.admin import admin
from web.config import (JudgeConfig, LoginConfig, ProblemConfig,
                        QuizTempDataConfig, S3Config, SchedulerConfig,
                        WebConfig)
from web.const import Privilege, ReturnCode, language_info, runner_status_info
from web.contest_manager import ContestManager
from web.course_manager import CourseManager
from web.csrf import setup_csrf
from web.discuss_manager import DiscussManager
from web.judge_manager import JudgeManager
from web.news_manager import NewsManager
from web.old_judge_manager import OldJudgeManager
from web.problem_manager import ProblemManager
from web.quiz_manager import QuizManager
from web.realname_manager import RealnameManager
from web.session_manager import SessionManager
from web.tracker import tracker
from web.user_manager import UserManager
from web.utils import (SqlSession, db, gen_page, gen_page_for_problem_list,
                       generate_s3_public_url, readable_lang_v1, readable_time)

web = Blueprint('web', __name__, static_folder='static', template_folder='templates')
web.register_blueprint(admin, url_prefix='/admin')
setup_csrf(web)


def validate(username: Optional['str'] = None,
             password: Optional['str'] = None,
             friendly_name: Optional['str'] = None,
             student_id: Optional['str'] = None) -> dict:
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


"""
The exam visibility part.
"""

def problem_in_exam(problem_id):
    """This is mainly for closing the discussion & rank part.
    In exam means:
    1. user is not admin.
    2. the problem is in a ongoing exam.
    """
    exam_id, is_exam_started = ContestManager.get_unfinished_exam_info_for_player(g.user)

    if exam_id == -1 or is_exam_started == False:
        return False

    return ContestManager.check_problem_in_contest(exam_id, problem_id)


def setup_appcontext():
    g.db = SqlSession()
    g.time = datetime.now()
    g.user = SessionManager.current_user()
    g.is_admin = g.user is not None and UserManager.is_some_admin(g.user)
    g.utils = utils
    g.consts = consts

@web.before_request
def before_request():
    if (request.full_path.startswith(('/OnlineJudge/static',
                                      '/OnlineJudge/api/heartBeat')) or
        request.full_path.endswith(('.js', '.css', '.ico'))):
        return

    xff = request.headers.get('X-Forwarded-For')
    if xff is not None and xff != '':
        request.remote_addr = xff.split(',')[-1]

    if 'db' not in g:
        setup_appcontext()

    tracker.log()

@web.after_request
def after_request(resp):
    if 'db' in g:
        try:
            g.db.commit()
        except Exception as e:
            return errorhandler(e)
    return resp


@web.errorhandler(Exception)
def errorhandler(exc: Exception):
    if isinstance(exc, HTTPException):
        return exc
    if 'db' in g:
        try:
            g.db.rollback()
        except Exception as e:
            exc = e
    if 'user' in g and g.user is not None and g.user.privilege >= Privilege.SUPER:
        msg = format_exc(exc)
    else:
        msg = 'We encountered an error serving your request. Please contact site maintainer.'
    resp = make_response(msg)
    resp.status_code = INTERNAL_SERVER_ERROR
    resp.content_type = 'text/plain'
    return resp


def not_logged_in():
    return redirect('/OnlineJudge/login?next=' + quote(request.full_path))

def require_logged_in(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return not_logged_in()
        return func(*args, **kwargs)
    return wrapped


@web.route('/')
def index():
    suggestions = None
    if g.user is not None:
        contests = ContestManager.get_contests_for_user(g.user)
        suggestions = ContestManager.suggest_contests(contests)
    return render_template('index.html', news=NewsManager.get_news(),
                           suggestions=suggestions)


@web.route('/index.html')
def index2():
    return redirect('/')


@web.route('/api/problem/<problem:problem>/description')
def get_problem_description(problem: Problem):
    data = {
        'ID': problem.id,
        'Title': problem.title,
        'Description': str(problem.description),
        'Input': str(problem.input),
        'Output': str(problem.output),
        'Example_Input': str(problem.example_input),
        'Example_Output': str(problem.example_output),
        'Data_Range': str(problem.data_range),
        'Release_Time': problem.release_time.isoformat(),
        'Problem_Type': problem.problem_type,
        'Limits': str(problem.limits),
    }
    return json.dumps(data)

@web.route('/api/code', methods=['POST'])
def get_code():
    if g.user is None:
        return '-1'
    run_id = request.form.get('submit_id')
    if run_id is None:
        return '-1'
    if not str(run_id).isdigit():  # bad argument
        return '-1'
    run_id = int(run_id)
    if run_id < 0 or run_id > OldJudgeManager.max_id():
        return '-1'
    detail = OldJudgeManager.query_judge(run_id)
    if detail is None:
        return '-1'
    if not JudgeManager.can_show(JudgeManager.get_submission(run_id)):
        return '-1'
    return detail.code


@web.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        nxt = request.args.get('next')
        nxt = '/' if nxt is None else nxt
        return render_template('login.html', Next=nxt)
    username = request.form.get('username')
    password = request.form.get('password')
    if username is None or password is None:
        abort(BAD_REQUEST)
    user = UserManager.get_user_by_username(username)
    if user is None:
        return ReturnCode.ERR_LOGIN
    if not UserManager.check_login(user, password):
        return ReturnCode.ERR_LOGIN
    lid = str(uuid4())
    SessionManager.new_session(user, lid)
    ret = make_response(ReturnCode.SUC_LOGIN)
    ret.set_cookie(key=SessionManager.session_cookie_name, value=lid, max_age=LoginConfig.Login_Life_Time)
    return ret


@web.route('/logout', methods=['POST'])
def logout():
    if g.user is None:
        return redirect('/OnlineJudge/')
    SessionManager.logout()
    ret = make_response(redirect('/OnlineJudge/', SEE_OTHER))
    ret.delete_cookie(SessionManager.session_cookie_name)
    return ret


@web.route('/register', methods=['GET', 'POST'])
def register():
    if WebConfig.Block_Register:
        abort(NOT_FOUND)
    if request.method == 'GET':
        nxt = request.args.get('next')
        return render_template('register.html', Next=nxt)
    username = request.form.get('username')
    password = request.form.get('password')
    friendly_name = request.form.get('friendly_name')
    student_id = request.form.get('student_id')
    if username is None or password is None or friendly_name is None or student_id is None:
        abort(BAD_REQUEST)
    val = validate(username, password, friendly_name, student_id)
    if val == ReturnCode.SUC_VALIDATE:
        UserManager.add_user(username, student_id, friendly_name, password, 0)
        return ReturnCode.SUC_REGISTER
    else:
        return val


@web.route('/problem')
@require_logged_in
def problem_list():
    page = request.args.get('page')
    page = int(page) if page else 1

    problem_id = request.args.get('problem_id')
    if problem_id == '':
        problem_id = None
    if problem_id is not None:
        return redirect(f'/OnlineJudge/problem/{problem_id}')
    problem_name_keyword = request.args.get('problem_name_keyword')
    if problem_name_keyword == '':
        problem_name_keyword = None
    problem_type = request.args.get('problem_type')
    if problem_type == '-1' or problem_type == '':
        problem_type = None
    contest_id = request.args.get('contest_id')
    contest_id = int(contest_id) if contest_id is not None and contest_id != '' else None

    limit = WebConfig.Problems_Each_Page
    offset = (page - 1) * WebConfig.Problems_Each_Page
    query = db.query(Problem.id, Problem.title, Problem.problem_type)
    if not UserManager.has_site_owner_tag(g.user):
        readable_course_ids = UserManager.get_readable_course_ids(g.user)
        query = query.where(sa.or_(Problem.release_time <= g.time,
                                   Problem.course_id.in_(readable_course_ids)))
    if problem_name_keyword is not None:
        query = query.where(sa.func.strpos(Problem.title, problem_name_keyword) > 0)
    if problem_type is not None:
        query = query.where(Problem.problem_type == problem_type)
    if contest_id is not None:
        problem_ids = ContestManager.list_problem_for_contest(contest_id)
        query = query.where(Problem.id.in_(problem_ids))
    count_under_11000 = query.where(Problem.id <= 11000).count()
    max_page_under_11000 = ceil(count_under_11000 / WebConfig.Problems_Each_Page)
    count = query.count()
    max_page = ceil(count / WebConfig.Problems_Each_Page)
    problems = query \
        .order_by(Problem.id.asc()) \
        .limit(limit).offset(offset) \
        .all()

    return render_template('problem_list.html', problems=problems,
                            pages=gen_page_for_problem_list(page, max_page, max_page_under_11000),
                            args=dict(filter(lambda e: e[0] != 'page', request.args.items())))

@web.route('/problem/<problem:problem>')
@require_logged_in
def problem_detail(problem: Problem):
    in_exam = problem_in_exam(problem.id)
    return render_template('problem_details.html', problem=problem,
                           In_Exam=in_exam)


@web.route('/problem/<problem:problem>/admin', methods=['GET', 'POST'])
@require_logged_in
def problem_admin(problem: Problem):
    if not g.can_write:
        abort(FORBIDDEN)

    if request.method == 'POST':
        action = request.form['action']
        if action == 'hide':
            ProblemManager.hide_problem(problem)
        elif action == 'show':
            ProblemManager.show_problem(problem)
        elif action == 'delete':
            if request.form['confirm'] != str(problem.id):
                abort(BAD_REQUEST)
            course_id = problem.course_id
            ProblemManager.delete_problem(problem)
            return redirect(f'/OnlineJudge/course/{course_id}/admin', SEE_OTHER)
        else:
            abort(BAD_REQUEST)

    submission_count = db.query(JudgeRecordV2.id).where(JudgeRecordV2.problem_id == problem.id).count()
    ac_count = db.query(JudgeRecordV2.id).where(JudgeRecordV2.problem_id == problem.id).where(JudgeRecordV2.status == JudgeStatus.accepted).count()

    return render_template('problem_admin.html', ID=problem.id, Title=problem.title,
                           problem=problem,
                           submission_count=submission_count, ac_count=ac_count)


@web.route('/problem/<problem:problem>/submit', methods=['GET', 'POST'])
@require_logged_in
def problem_submit(problem: Problem):
    if request.method == 'GET':
        title = problem.title
        problem_type = problem.problem_type
        in_exam = problem_in_exam(problem.id)
        if problem_type == 0:
            languages_accepted = ProblemManager.languages_accepted(problem)
            return render_template('problem_submit.html',
                                   Problem_ID=problem.id, Title=title, In_Exam=in_exam,
                                   languages_accepted=languages_accepted)
        elif problem_type == 1:
            quiz_json = QuizManager.get_json_from_data_service_by_id(QuizTempDataConfig, problem.id)
            success = quiz_json['e'] == 0
            if success:
                for i in quiz_json['problems']:
                    i['answer'] = ''

            return render_template('quiz_submit.html', Problem_ID=problem.id,
                                   Title=problem.title, In_Exam=in_exam,
                                   success=success,
                                   quiz=quiz_json['problems'] if success else None)
    else:
        public = bool(request.form.get('shared', 0))  # 0 or 1
        lang_request_str = str(request.form.get('lang'))
        if lang_request_str == 'quiz':
            user_code: Optional[str] = json.dumps(request.form.to_dict())
        else:
            user_code = request.form.get('code')
        if user_code is None:
            abort(BAD_REQUEST)
        if len(str(user_code)) > ProblemConfig.Max_Code_Length:
            abort(REQUEST_ENTITY_TOO_LARGE)
        lang_str = lang_request_str.lower()
        if lang_str not in ProblemManager.languages_accepted(problem):
            abort(BAD_REQUEST)
        submission_id = JudgeManager.add_submission(
            public=public,
            language=lang_str,
            user=g.user,
            problem_id=problem.id,
            code=user_code,
        )
        return redirect(f'/OnlineJudge/code/{submission_id}/', SEE_OTHER)


def check_scheduler_auth():
    auth = request.headers.get('Authorization', '')
    if auth != SchedulerConfig.auth:
        abort(UNAUTHORIZED)


@web.route('/api/submission/<submission_id>/status', methods=['PUT'])
def set_status(submission_id):
    check_scheduler_auth()
    status = request.get_data(as_text=True)
    if status not in ('compiling', 'judging'):
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


@web.route('/problem/<problem:problem>/rank')
@require_logged_in
def problem_rank(problem: Problem):
    sort_parameter = request.args.get('sort')

    submissions = JudgeManager.list_accepted_submissions(problem.id)
    real_name_map = {}
    languages = {}
    for submission in submissions:
        stuid = submission.user.student_id
        if stuid not in real_name_map:
            real_name_map[stuid] = RealnameManager.query_realname_for_current_user(stuid)
        languages[submission] = 'Unknown' if submission.language not in language_info \
            else language_info[submission.language].name
    has_real_name = any(len(real_name_map[x]) > 0 for x in real_name_map)

    if sort_parameter == 'memory':
        submissions = sorted(submissions, key=lambda x: x.memory_bytes if x.memory_bytes is not None else 0)
    elif sort_parameter == 'submit_time':
        submissions = sorted(submissions, key=lambda x: x.created_at)
    else:
        sort_parameter = 'time'
        submissions = sorted(submissions, key=lambda x: x.time_msecs if x.time_msecs is not None else 0)

    in_exam = problem_in_exam(problem.id)

    return render_template('problem_rank.html', Problem_ID=problem.id, Title=problem.title,
                           submissions=submissions, Sorting=sort_parameter,
                           real_name_map=real_name_map, has_real_name=has_real_name,
                           languages=languages,
                           In_Exam=in_exam)


@web.route('/problem/<problem:problem>/discuss', methods=['GET', 'POST'])
@require_logged_in
def discuss(problem: Problem):
    if request.method == 'GET':
        in_exam = problem_in_exam(problem.id)

        if in_exam:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID=problem.id,
                                   Title=problem.title, Blocked=True,
                                   In_Exam=True)  # Discussion Closed
        data = problem.discussions
        discussions = []
        for ele in data:
            tmp = [ele.id, ele.user.username, ele.data, readable_time(ele.created_at)]
            # tmp[4]: editable
            tmp.append(ele.user_id == g.user.id or g.user.privilege >= Privilege.SUPER)
            discussions.append(tmp)
        return render_template('problem_discussion.html', Problem_ID=problem.id,
                               Title=problem.title, Discuss=discussions,
                               In_Exam=False)
    else:
        try:
            form = request.json
            if form is None:
                abort(BAD_REQUEST)
            action = form.get('action')  # post, edit, delete
            if action == 'post':
                text = form.get('text')
                if ProblemManager.can_write(problem):
                    DiscussManager.add_discuss(problem.id, g.user, text)
                    return ReturnCode.SUC
                else:
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'edit':
                discuss_id = int(form.get('discuss_id'))
                discussion = DiscussManager.get_discussion(discuss_id)
                if discussion is None:
                    return ReturnCode.ERR_PERMISSION_DENIED
                text = form.get('text')
                if g.user.id == discussion.user_id or ProblemManager.can_write(problem):
                    discussion.data = text
                    return ReturnCode.SUC
                else:
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'delete':
                discuss_id = int(form.get('discuss_id'))
                discussion = DiscussManager.get_discussion(discuss_id)
                if discussion is None:
                    return ReturnCode.ERR_PERMISSION_DENIED
                if g.user.id == discussion.user_id or ProblemManager.can_write(problem):
                    DiscussManager.delete_discuss(discussion)
                    return ReturnCode.SUC
                else:
                    return ReturnCode.ERR_PERMISSION_DENIED
            else:  # what happened?
                return ReturnCode.ERR_BAD_DATA
        except KeyError:
            return ReturnCode.ERR_BAD_DATA
        except TypeError:
            return ReturnCode.ERR_BAD_DATA


@web.route('/status')
@require_logged_in
def status():
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

    page = request.args.get('page')
    page = int(page) if page is not None else 1
    limit = JudgeConfig.Judge_Each_Page
    offset = (page - 1) * JudgeConfig.Judge_Each_Page
    query = db.query(JudgeRecordV2) \
        .options(defer(JudgeRecordV2.details), defer(JudgeRecordV2.message)) \
        .options(selectinload(JudgeRecordV2.user).load_only(User.student_id, User.friendly_name)) \
        .options(selectinload(JudgeRecordV2.problem).load_only(Problem.title))
    if arg_submitter is not None:
        user = UserManager.get_user_by_username(arg_submitter)
        if user is not None:
            query = query.where(JudgeRecordV2.user_id == user.id)
    if arg_problem_id is not None:
        query = query.where(JudgeRecordV2.problem_id == arg_problem_id)
    if arg_status is not None:
        query = query.where(JudgeRecordV2.status == arg_status)
    if arg_lang is not None:
        query = query.where(JudgeRecordV2.language == arg_lang)
    query = query.order_by(JudgeRecordV2.id.desc())
    count = query.count()
    max_page = ceil(count / JudgeConfig.Judge_Each_Page)
    query = query.limit(limit).offset(offset)
    submissions = query.all()

    real_name_map = {}
    show_links = {}
    for submission in submissions:
        if submission.user.student_id not in real_name_map:
            real_name_map[submission.user.student_id] = \
                RealnameManager.query_realname_for_current_user(submission.user.student_id)
        show_links[submission] = JudgeManager.can_show(submission)
    return render_template('status.html', pages=gen_page(page, max_page),
                           submissions=submissions,
                           real_name_map=real_name_map,
                           show_links=show_links,
                           args=dict(filter(lambda e: e[0] != 'page', request.args.items())))


def code_old(run_id):
    if run_id < 0 or run_id > OldJudgeManager.max_id():
        abort(NOT_FOUND)
    detail = OldJudgeManager.query_judge(run_id)
    if detail is None:
        abort(NOT_FOUND)
    else:
        friendly_name = detail.user.friendly_name
        problem_title = detail.problem.title
        language = readable_lang_v1(detail.language)
        time = readable_time(int(detail.time))
        data = None
        if detail.detail is not None and detail.detail != 'None':
            temp = json.loads(detail.detail)
            score = int(temp[1])
            data = temp[4:]
        else:
            score = 0
        return render_template('judge_detail_old.html', Detail=detail, Data=data,
                               friendly_name=friendly_name,
                               problem_title=problem_title,
                               language=language,
                               time=time,
                               score=score)

@web.route('/code')
def code_compat():
    submit_id = request.args.get('submit_id')
    if submit_id is None:
        abort(NOT_FOUND)
    return redirect(f'/OnlineJudge/code/{submit_id}/')

@web.route('/code/<submission:submission>/')
@require_logged_in
def code(submission: JudgeRecordV2):
    if submission.id <= OldJudgeManager.max_id():
        return code_old(submission.id)

    details = deserialize(submission.details) if submission.details is not None else None
    if details is None and submission.status == JudgeStatus.judging:
        url = f'submission/{quote(str(submission.id))}/status'
        # TODO: caching
        res = requests.get(urljoin(SchedulerConfig.base_url, url))
        if res.status_code == OK:
            details = deserialize(res.text)
        elif res.status_code == NOT_FOUND:
            pass
        else:
            raise Exception(f'Unknown status code {res.status_code} fetching judge status')

    code_url = generate_s3_public_url('get_object', {
        'Bucket': S3Config.Buckets.submissions,
        'Key': JudgeManager.key_from_submission_id(submission.id),
    }, ExpiresIn=60)
    show_score = not g.can_abort and submission.status not in \
        (JudgeStatus.void, JudgeStatus.aborted)
    real_name = RealnameManager.query_realname_for_current_user(submission.user.student_id)
    return render_template('judge_detail.html',
                           submission=submission,
                           real_name=real_name,
                           code_url=code_url,
                           details=details,
                           show_score=show_score)

@web.route('/code/<submission:submission>/void', methods=['POST'])
def mark_void(submission: JudgeRecordV2):
    if not g.can_write:
        abort(FORBIDDEN)
    JudgeManager.mark_void(submission)
    return redirect('.', SEE_OTHER)


@web.route('/code/<submission:submission>/rejudge', methods=['POST'])
def rejudge(submission: JudgeRecordV2):
    if not g.can_write:
        abort(FORBIDDEN)
    JudgeManager.rejudge(submission)
    return redirect('.', SEE_OTHER)


@web.route('/code/<submission:submission>/abort', methods=['POST'])
@require_logged_in
def abort_judge(submission: JudgeRecordV2):
    if not g.can_abort:
        abort(FORBIDDEN)
    JudgeManager.abort_judge(submission)
    return redirect('.', SEE_OTHER)


@require_logged_in
def contest_list_generic(type, type_zh):
    contest_id = request.args.get(f'{type}_id')
    if contest_id is not None:
        return redirect(f'/OnlineJudge/problemset/{contest_id}')
    implicit_contests = ContestManager._get_implicit_contests(g.user)
    user_contests = set(implicit_contests).union(g.user.external_contests)

    page = request.args.get('page')
    page = int(page) if page is not None else 1
    type_ids = [0, 2] if type == 'contest' else [1]
    keyword = request.args.get('keyword')
    status = request.args.get('status')
    count, contests = ContestManager.list_contest(type_ids, page, WebConfig.Contests_Each_Page, keyword=keyword, status=status)

    max_page = ceil(count / WebConfig.Contests_Each_Page)

    return render_template('contest_list.html', contests=contests,
                           get_status=ContestManager.get_status,
                           reason_cannot_join=ContestManager.reason_cannot_join,
                           implicit_contests=implicit_contests,
                           user_contests=user_contests,
                           type=type, type_zh=type_zh,
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

@web.route('/problemset/<contest:contest>')
def problemset(contest: Contest):
    problems = ContestManager.list_problem_for_contest(contest.id)
    problems_visible = g.time >= contest.start_time or ContestManager.can_read(contest)
    data = ContestManager.get_board_view(contest)
    student_ids = set(x['student_id'] for x in data)
    real_name_map = dict((s, RealnameManager.query_realname_for_contest(s, contest)) for s in student_ids)
    has_real_name = any(real_name_map[s] is not None for s in real_name_map)
    contest_status = ContestManager.get_status(contest)

    time_elapsed = (g.time - contest.start_time).total_seconds()
    time_overall = (contest.end_time - contest.start_time).total_seconds()
    percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)

    return render_template(
        'contest.html',
        contest=contest,
        problems=problems,
        status=contest_status,
        percentage=percentage,
        problems_visible=problems_visible,
        has_real_name=has_real_name,
        real_name_map=real_name_map,
        data=data,
    )

@web.route('/problemset/<contest:contest>/admin', methods=['GET', 'POST'])
def problemset_admin(contest: Contest):
    if not g.can_write:
        abort(FORBIDDEN)

    if request.method == 'POST':
        form = request.form
        action = form['action']
        if action == 'edit':
            contest.name = form['name']
            contest.description = form.get('description', '')
            contest.start_time = datetime.fromisoformat(form['start_time'])
            contest.end_time = datetime.fromisoformat(form['end_time'])
            contest.type = int(form['type'])
            contest.ranked = form.get('ranked', 'off') == 'on'
            contest.rank_penalty = form.get('rank_penalty', 'off') == 'on'
            contest.rank_partial_score = form.get('rank_partial_score', 'off') == 'on'
        elif action == 'delete':
            if request.form['confirm'] != str(contest.id):
                abort(BAD_REQUEST)
            course_id = contest.course_id
            ContestManager.delete_contest(contest)
            return redirect(f'/OnlineJudge/course/{course_id}/admin', SEE_OTHER)
        elif action == 'requirements':
            cc_str = form.get('completion_criteria', '')
            cc = None if cc_str == '' else int(cc_str)
            if cc is not None:
                if contest.rank_partial_score:
                    valid = cc >= 0
                else:
                    valid = 0 <= cc <= len(contest.problems)
                if not valid:
                    abort(BAD_REQUEST, f'完成条件为负或超过题目总数')
            contest.completion_criteria = cc

            languages = []
            for lang in language_info:
                if form.get(f'lang-{lang}', 'off') == 'on':
                    languages.append(lang)
            contest.allowed_languages = None if len(languages) == len(language_info) or len(languages) == 0 else languages
        elif action == 'groups':
            # TODO: recompute membership
            if form.get('all', 'off') == 'on':
                contest.group_ids = None
            else:
                gs = []
                for group in contest.course.groups:
                    if form.get(f'group-{group.id}', 'off') == 'on':
                        gs.append(group.id)
                contest.group_ids = gs
        else:
            abort(BAD_REQUEST)

    scores = ContestManager.get_scores(contest)
    # problem id -> (try count, ac count)
    problem_stats = dict((problem.id, { 'try': 0, 'ac': 0 }) for problem in contest.problems)
    completion_stats = { 'total': 0, 'completed': 0 }
    for player in scores:
        if player['is_external']:
            continue
        if contest.completion_criteria is not None:
            completion_stats['total'] += 1
            if ContestManager.user_has_completed_by_scores(contest, player):
                completion_stats['completed'] += 1
        for problem in player['problems']:
            if problem['count'] > 0:
                problem_stats[problem['id']]['try'] += 1
            if problem['accepted']:
                problem_stats[problem['id']]['ac'] += 1

    return render_template('contest_admin.html', contest=contest,
                           problem_stats=problem_stats,
                           completion_stats=completion_stats)

@web.route('/problemset/<contest:contest>/problem/add', methods=['POST'])
def problemset_problem_add(contest: Contest):
    if not g.can_write:
        abort(FORBIDDEN)

    try:
        ids = [int(x) for x in request.form['id'].strip().splitlines()]
    except ValueError as e:
        abort(BAD_REQUEST, e)
    for problem_id in ids:
        problem = ProblemManager.get_problem(problem_id)
        if problem is None:
            db.rollback()
            abort(BAD_REQUEST, f'题目 {problem_id} 不存在')
        if problem not in contest.problems:
            contest.problems.append(problem)

    return redirect(f'/OnlineJudge/problemset/{contest.id}/admin', SEE_OTHER)

@web.route('/problemset/<contest:contest>/problem/remove', methods=['POST'])
def problemset_problem_remove(contest: Contest):
    if not g.can_write:
        abort(FORBIDDEN)

    try:
        ids = [int(x) for x in request.form['id'].strip().splitlines()]
    except ValueError as e:
        abort(BAD_REQUEST, e)
    for problem_id in ids:
        ContestManager.delete_problem_from_contest(contest.id, problem_id)

    return redirect(f'/OnlineJudge/problemset/{contest.id}/admin', SEE_OTHER)

@web.route('/problemset/<contest:contest>/quit', methods=['POST'])
def problemset_quit(contest: Contest):
    if g.time >= contest.end_time:
        abort(BAD_REQUEST, '比赛已结束')
    if g.user in contest.external_players:
        contest.external_players.remove(g.user)
    return redirect(f'/OnlineJudge/problemset/{contest.id}', SEE_OTHER)

@web.route('/problemset/<contest:contest>/join', methods=['POST'])
def problemset_join(contest: Contest):
    if not ContestManager.can_join(contest):
        abort(BAD_REQUEST)
    if g.user not in contest.external_players:
        contest.external_players.add(g.user)
    return redirect(f'/OnlineJudge/problemset/{contest.id}', SEE_OTHER)

@require_logged_in
def course_list_generic(title: str, description: str, query,
                        show_tag: bool = True,
                        show_term: bool = True):
    page = request.args.get('page')
    page = int(page) if page else 1

    limit = WebConfig.Courses_Each_Page
    offset = (page - 1) * limit
    count = db.scalar(sa.select(sa.func.count()).select_from(query.subquery()))
    assert count is not None
    max_page = ceil(count / limit)
    courses = db.scalars(
        query
        .order_by(Course.id.asc())
        .limit(limit).offset(offset)
    ).all()

    return render_template('course_list.html', courses=courses,
                           title=title,
                           description=description,
                           show_tag=show_tag,
                           show_term=show_term,
                           can_join=CourseManager.can_join,
                           pages=gen_page(page, max_page),
                           args=dict(filter(lambda e: e[0] != 'page', request.args.items())))

@web.route('/course')
def course_list():
    return course_list_generic('班级列表', '', sa.select(Course))

@web.route('/course/tag/<int:tag_id>')
def course_list_tag(tag_id):
    tag = db.get(CourseTag, tag_id)
    if tag is None: abort(NOT_FOUND)
    stmt = sa.select(Course).where(Course.tag_id == tag_id)
    return course_list_generic(tag.name, '', stmt, show_tag=False)

@web.route('/course/term/<int:term_id>')
def course_list_term(term_id):
    term = db.get(Term, term_id)
    if term is None: abort(NOT_FOUND)
    stmt = sa.select(Course).where(Course.term_id == term_id)
    return course_list_generic(f'{term.name} 班级列表', '', stmt, show_term=False)

@web.route('/course/<course:course>/')
def course(course: Course):
    suggestions = ContestManager.suggest_contests(course.contests)

    return render_template('course.html', course=course,
                           suggestions=suggestions)

def course_contest_list_generic(course: Course, type: str):
    type_ids = [0, 2] if type == 'contest' else [1]
    contests = list(filter(lambda c: c.type in type_ids, course.contests))
    contests.sort(key=lambda c: c.end_time, reverse=True)
    contests_enrolled = ContestManager.get_contests_for_user(g.user)
    statuses = [ContestManager.get_status_for_card(c, c in contests_enrolled) for c in contests]

    return render_template('course_contest_list.html', type=type,
                           course=course, contests=statuses)

@web.route('/course/<course:course>/contest')
def course_contest_list(course: Course):
    return course_contest_list_generic(course, 'contest')

@web.route('/course/<course:course>/homework')
def course_homework_list(course: Course):
    return course_contest_list_generic(course, 'homework')

@web.route('/course/<course:course>/join', methods=['POST'])
def course_join(course: Course):
    if not CourseManager.can_join(course):
        abort(BAD_REQUEST)
    if g.user not in course.users:
        db.add(Enrollment(user_id=g.user.id, course_id=course.id))
        db.flush()
    return redirect(f'/OnlineJudge/course/{course.id}/', SEE_OTHER)

@web.route('/course/<course:course>/admin', methods=['GET', 'POST'])
def course_admin(course: Course):
    if not g.can_write:
        abort(FORBIDDEN)

    tab = request.args.get('tab', 'overview')
    expand_group = request.args.get('group', None)
    if request.method == 'POST':
        form = request.form
        action = form['action']
        if action == 'edit':
            course.name = form['name']
            course.description = form['description']
        elif action == 'realname-create':
            data = [line.split(',') for line in request.form['data'].strip().splitlines()]
            for line in data:
                groups: List[Group] = []
                if len(line) > 2:
                    group_names = [x.strip() for x in line[2].split('|')]
                    for group_name in group_names:
                        group = CourseManager.get_group_by_name(course, group_name)
                        if group is None:
                            db.rollback()
                            return abort(BAD_REQUEST, f'分组 {repr(group_name)} 不存在')
                        groups.append(group)
                rr = RealnameManager.query_realname_for_course(line[0], course.id)
                if rr is not None:
                    for e in rr.enrollments:
                        if e.admin:
                            abort(BAD_REQUEST, f'不能修改课程管理员 {repr(e.user.username)} 的实名信息')
                RealnameManager.add_student(line[0], line[1], course, groups)
            tab = 'user'
        elif action == 'realname-delete':
            rr_id = int(form['id'])
            rr = db.get(RealnameReference, rr_id)
            if rr is None or rr.course_id != course.id:
                abort(BAD_REQUEST)
            for e in rr.enrollments:
                if e.admin:
                    abort(BAD_REQUEST, f'不能删除课程管理员 {repr(e.user.username)} 的实名信息')
            db.delete(rr)
            db.flush()
            tab = 'user'
        elif action == 'problem-create':
            problem = ProblemManager.create_problem(course)
            return redirect(f'/OnlineJudge/problem/{problem.id}/admin', SEE_OTHER)
        elif action == 'contest-create':
            contest = ContestManager.create_contest(course)
            return redirect(f'/OnlineJudge/problemset/{contest.id}/admin', SEE_OTHER)
        elif action == 'group-create':
            name = form['name']
            if CourseManager.get_group_by_name(course, name) != None:
                abort(BAD_REQUEST, f'分组 {repr(name)} 已存在')
            group = Group(name=name,
                          description=form.get('description', ''),
                          course_id=course.id)
            db.add(group)
            db.flush()
            tab = 'group'
            expand_group = str(group.id)
        elif action == 'group-edit':
            group = CourseManager.get_group_in_course(course, int(form['id']))
            if group is None:
                abort(BAD_REQUEST)
            name = form['name']
            existing_group = CourseManager.get_group_by_name(course, name)
            if existing_group is not None and existing_group != group:
                abort(BAD_REQUEST, f'分组 {repr(name)} 已存在')
            group.name = name
            group.description = form['description']
            tab = 'group'
            expand_group = str(group.id)
        elif action == 'group-delete':
            group = CourseManager.get_group_in_course(course, int(form['id']))
            if group is None:
                abort(BAD_REQUEST)
            db.delete(group)
            db.flush()
            tab = 'group'
        elif action == 'user-delete':
            usernames = form['data'].strip().splitlines()
            for username in usernames:
                user = UserManager.get_user_by_username(username)
                if user is None:
                    db.rollback()
                    abort(BAD_REQUEST, f'用户 {repr(username)} 不存在')
                enrollment = UserManager.get_enrollment(user, course)
                if enrollment is None:
                    continue
                if enrollment.admin:
                    db.rollback()
                    abort(BAD_REQUEST, f'用户 {repr(username)} 是课程管理员，请先移除管理权限')
                db.delete(enrollment)
                db.flush()
            tab = 'user'
        elif action == 'user-demote':
            enrollment = db.get(Enrollment, int(form['id']))
            if enrollment is None or not enrollment.admin or enrollment.course_id != course.id:
                abort(BAD_REQUEST)
            enrollment.admin = False
            UserManager.flush_privileges(enrollment.user)
            tab = 'user'
        elif action == 'user-promote':
            usernames = form['data'].strip().splitlines()
            for username in usernames:
                user = UserManager.get_user_by_username(username)
                if user is None:
                    db.rollback()
                    abort(BAD_REQUEST, f'用户 {repr(username)} 不存在')
                enrollment = UserManager.get_enrollment(user, course)
                if enrollment is None:
                    db.rollback()
                    abort(BAD_REQUEST, f'用户 {repr(username)} 未报名课程')
                if enrollment.realname_reference is None:
                    db.rollback()
                    abort(BAD_REQUEST, f'用户 {repr(username)} 未添加实名信息')
                enrollment.admin = True
                UserManager.flush_privileges(user)
            tab = 'user'
        else:
            abort(BAD_REQUEST, f'Unknown action {action}')

    return render_template('course_admin.html', course=course, tab=tab, expand_group=expand_group)

@web.route('/course/<course:course>/group/<int:group_id>/<action>', methods=['POST'])
def course_group_edit(course, group_id, action):
    if not g.can_write:
        abort(FORBIDDEN)

    group = CourseManager.get_group_in_course(course, group_id)
    if group is None:
        abort(BAD_REQUEST)

    data = request.form['data'].strip().splitlines()
    realname_references = [RealnameManager.query_realname_for_course(x, course.id) for x in data]
    for id, rr in zip(data, realname_references):
        if rr is None:
            abort(BAD_REQUEST, f'学号 {repr(id)} 没有对应的实名信息')
    realname_references: List[RealnameReference]
    if action == 'add':
        for rr in realname_references:
            group.realname_references.add(rr)
    elif action == 'remove':
        for rr in realname_references:
            group.realname_references.remove(rr)
    else:
        abort(NOT_FOUND)

    db.flush()
    return redirect(f'/OnlineJudge/course/{course.id}/admin?tab=group&group={group.id}', SEE_OTHER)


@web.route('/profile', methods=['GET', 'POST'])
@require_logged_in
def profile():
    if request.method == 'GET':
        return render_template('profile.html')
    else:
        form = request.json
        if form is None:
            abort(BAD_REQUEST)
        try:
            ret = validate(password=form.get('password'), friendly_name=form.get('friendly_name'))
            if ret == ReturnCode.SUC_VALIDATE:
                UserManager.modify_user(g.user.username, None, form.get('friendly_name'), form.get(
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
        runner_list: List[dict] = []
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
    return render_template('about.html', runners=runner_list, runner_success=runner_success)


@web.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(web.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


class ModelConverter(BaseConverter):
    def get(self, model_id: int):
        raise NotImplementedError

    def to_python(self, value: str):
        setup_appcontext()
        if g.user is None:
            abort(not_logged_in())
        try:
            return self.get(int(value))
        except ValueError:
            abort(BAD_REQUEST)

    def to_url(self, value) -> str:
        return str(value.id)

class ProblemConverter(ModelConverter):
    def get(self, model_id: int) -> Problem:
        problem = ProblemManager.get_problem(model_id)
        if not ProblemManager.can_show(problem):
            abort(NOT_FOUND)
        g.can_read = ProblemManager.can_read(problem)
        g.can_write = ProblemManager.can_write(problem)
        return problem

class SubmissionConverter(ModelConverter):
    def get(self, model_id: int) -> JudgeRecordV2:
        submission = JudgeManager.get_submission(model_id)
        if not JudgeManager.can_show(submission):
            abort(NOT_FOUND)
        g.can_write = JudgeManager.can_write(submission)
        g.can_abort = JudgeManager.can_abort(submission)
        return submission

class ContestConverter(ModelConverter):
    def get(self, model_id: int) -> Contest:
        contest = ContestManager.get_contest(model_id)
        if contest is None:
            abort(NOT_FOUND)
        g.can_read = ContestManager.can_read(contest)
        g.can_write = ContestManager.can_write(contest)
        return contest

class CourseConverter(ModelConverter):
    def get(self, model_id: int) -> Course:
        course = CourseManager.get_course(model_id)
        if course is None:
            abort(NOT_FOUND)
        g.can_read = CourseManager.can_read(course)
        g.can_write = CourseManager.can_write(course)
        return course


oj = Flask('WEB')
oj.url_map.converters['problem'] = ProblemConverter
oj.url_map.converters['submission'] = SubmissionConverter
oj.url_map.converters['contest'] = ContestConverter
oj.url_map.converters['course'] = CourseConverter
oj.register_blueprint(web, url_prefix='/OnlineJudge')
oj.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400
