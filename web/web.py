import web.logging_ as logging_

import json
import os
import re
from datetime import datetime, timedelta
from functools import wraps
from http.client import (BAD_REQUEST, FORBIDDEN, FOUND, INTERNAL_SERVER_ERROR,
                         NO_CONTENT, NOT_FOUND, OK, REQUEST_ENTITY_TOO_LARGE,
                         SEE_OTHER, UNAUTHORIZED)
from itertools import groupby
from logging import getLogger
from math import ceil
from typing import Dict, Iterable, List, NoReturn, Optional
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from uuid import uuid4
from zipfile import ZipFile

import requests
import sqlalchemy as sa
from flask import (Blueprint, Flask, abort, appcontext_pushed,
                   before_render_template, current_app, g, make_response,
                   redirect, render_template, request, send_file,
                   send_from_directory, template_rendered, url_for)
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import BaseConverter

import commons.task_typing
import web.const as consts
import web.utils as utils
from commons.models import (AccessToken, CompletionCriteriaType, Contest,
                            Course, CourseTag, Enrollment, Group,
                            JudgeRecordV2, JudgeStatus, Problem,
                            ProblemPrivilege, ProblemPrivilegeType,
                            RealnameReference, Term, User)
from commons.task_typing import JudgePlanSummary, ProblemJudgeResult
from commons.util import deserialize, format_exc, load_dataclass, serialize
from web.api import api, api_get_user, token_is_valid
from web.config import (JAccountConfig, JudgeConfig, NewsConfig,
                        QuizTempDataConfig, S3Config, SchedulerConfig,
                        WebConfig)
from web.const import (Privilege, ReturnCode, api_scopes,
                       completion_criteria_max_length, language_info,
                       max_pic_size, runner_status_info)
from web.csrf import setup_csrf
from web.logging_ import log_request
from web.manager.contest import ContestManager
from web.manager.course import CourseManager
from web.manager.discuss import DiscussManager
from web.manager.judge import JudgeManager, NotFoundException
from web.manager.news import NewsManager
from web.manager.oauth import OauthManager, randtoken
from web.manager.old_judge import OldJudgeManager
from web.manager.problem import ProblemManager
from web.manager.quiz import QuizManager
from web.manager.realname import RealnameManager
from web.manager.session import SessionManager, TempSessionManager
from web.manager.user import UserManager
from web.utils import (SqlSession, abort_converter, db, gen_page,
                       gen_page_for_problem_list, generate_s3_public_url,
                       is_api_call, not_logged_in, paged_search_limitoffset,
                       readable_lang_v1, readable_time, require_logged_in,
                       s3_internal, sort_scopes)

logger = getLogger(__name__)

web = Blueprint('web', __name__, static_folder='static', template_folder='templates')
web.register_blueprint(api, url_prefix='/api/v1')
setup_csrf(web)


def validate(username: Optional['str'] = None,
             password: Optional['str'] = None,
             friendly_name: Optional['str'] = None,
             student_id: Optional['str'] = None) -> Optional[str]:
    """Validate a user.

    This function is used in registering and updating user information.

    Args:
        username: The username to validate.
        password: The password to validate.
        friendly_name: The friendly name to validate.
        student_id: The student id to validate.

    Returns:
        None if all the fields are valid.
        An error string if something is wrong.
    """
    username_reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    password_reg = '([\x20-\x7e]{6,128})$'
    friendly_name_reg = '([a-zA-Z0-9_]{1,60})$'
    student_id_reg = '([0-9]{12}|[0-9]{5})$'
    if username is not None and re.match(username_reg, username) is None:
        return '用户名不符合要求。用户名要求：20 位以内的大小写字母或数字（第一位必须是字母）。'
    if password is not None and re.match(password_reg, password) is None:
        return '密码不符合要求。密码要求：6–128 位的大小写字母、数字、下划线。'
    if friendly_name is not None and re.match(friendly_name_reg, friendly_name) is None:
        return '昵称不符合要求。昵称要求：60 位以内的大小写字母、数字、下划线。'
    if student_id is not None and re.match(student_id_reg, student_id) is None:
        return '学工号不符合注册要求。学工号要求：5 或 12 位数字（如果不够可以用0补全）。'
    if username is not None and UserManager.has_user(username):
        return '用户名已被注册。'
    return None


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
    g.cache = {}
    g.db = SqlSession()
    if is_api_call():
        g.user = api_get_user()
    else:
        g.user = SessionManager.current_user()
    if g.user is not None:
        g.user_username = g.user.username
        g.user_realname = RealnameManager.query_realname_for_logs(g.user.student_id)
    g.is_admin = g.user is not None and UserManager.is_some_admin(g.user)
    g.utils = utils
    g.consts = consts

@web.before_request
def before_request():
    if len(request.query_string) == 0 and request.full_path.endswith('?'):
        request.full_path = request.full_path[:-1]

    if (request.full_path.startswith(url_for('web.static', filename='')) or
        request.full_path.endswith(('.js', '.css', '.ico'))):
        g.skip_logging = True
        return

    xff = request.headers.get('X-Forwarded-For')
    if xff is not None and xff != '':
        request.remote_addr = xff.split(',')[-1]

    if 'db' not in g:
        setup_appcontext()

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
    msg = format_exc(exc)
    logger.error('error when handling request: %(error)s', { 'error': exc }, 'web:error')
    if 'db' in g:
        try:
            g.db.rollback()
        except Exception as e:
            exc = e
    if not current_app.debug and \
        ('user' not in g or g.user is None or g.user.privilege < Privilege.SUPER):
        msg = 'We encountered an error serving your request. Please contact site maintainer.'
    resp = make_response(msg)
    resp.status_code = INTERNAL_SERVER_ERROR
    resp.content_type = 'text/plain'
    return resp


def set_tab(tab):
    g.current_tab = tab

def alert_success(content: str):
    g.alert = { 'type': 'success', 'content': content }

class AlertFail(Exception): pass
def alert_fail(content: str) -> NoReturn:
    g.alert = { 'type': 'danger', 'content': content }
    raise AlertFail

def ignore_alert_fail(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AlertFail:
            pass
    return wrapped


@web.route('/')
def index():
    suggestions = invited_courses = admin_courses = None
    if g.user is not None:
        contests = ContestManager.get_contests_for_user(g.user, include_admin=True, include_unofficial=True)
        suggestions = ContestManager.suggest_contests(list(contests))
        for type in suggestions:
            suggestions[type] = [x for x in suggestions[type] if not (x['course-member'] and x['is-external'])]
        invited_courses = CourseManager.get_invited_courses(g.user)
        invited_courses = set(c for c in invited_courses if c.id not in g.user.ignored_course_ids)
        admin_courses = CourseManager.get_admin_courses(g.user)
    return render_template('index.html',
                           news=NewsManager.get_news(),
                           news_link=NewsConfig.link,
                           suggestions=suggestions,
                           invited_courses=invited_courses,
                           admin_courses=admin_courses)


@web.route('/index.html')
def index2():
    return redirect(url_for('.index'))


def create_session(user: User):
    SessionManager.new_session(user)
    next = request.args.get('next', url_for('.index'))
    return redirect(next, SEE_OTHER)

@web.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        if username is None or password is None:
            alert_fail('请输入用户名和密码')
        user = UserManager.get_user_by_username(username)
        if user is None:
            alert_fail('用户名或密码错误')
        if not UserManager.check_login(user, password):
            alert_fail('用户名或密码错误')
        return create_session(user)
    except AlertFail:
        return render_template('login.html')

# this function is used in template login.html
@web.route('/oauth/jaccount')
def login_jaccount():
    next = request.args.get('next', '')
    ja_query = urlencode({
        'response_type': 'code',
        'scope': 'essential',
        'client_id': JAccountConfig.CLIENT_ID,
        'redirect_uri': url_for('web.jaccount_callback', _external=True),
        'state': next,
    })
    ja_url = f'{JAccountConfig.AUTHORIZATION_BASE_URL}?{ja_query}'
    return redirect(ja_url, FOUND)


def get_student_id_from_access_token(access_token: str) -> str:
    res = requests.get(
        JAccountConfig.PROFILE_URL, headers={'Authorization': f'Bearer {access_token}'}
    )
    data = res.json()
    student_id: str = data['entities'][0]['code']
    return student_id

# jAccount callback
@web.get('/oauth/jaccount/callback')
def jaccount_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': url_for('web.jaccount_callback', _external=True),
        'client_id': JAccountConfig.CLIENT_ID,
        'client_secret': JAccountConfig.CLIENT_SECRET,
    }
    res = requests.post(JAccountConfig.TOKEN_URL, data=data)
    data = res.json()
    try:
        access_token = data['access_token']
        student_id = get_student_id_from_access_token(access_token)
    except KeyError:
        return '登录状态无效，请重试或联系 OJ 运维组。', 403
    TempSessionManager.new_session(student_id)
    return redirect(url_for('web.reset_password', next=state))


@web.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # request both in GET and POST,
    # in POST, we need to validate it again to security
    student_id = TempSessionManager.current_student_id()
    if student_id is None:
        return redirect(url_for('.login_jaccount'))
    users = UserManager.get_users_by_student_id(student_id)

    def on_post():
        user_id = request.form.getlist('user_id')
        user_id = set(map(int, user_id))
        password = request.form.get('password')
        if user_id == set():
            alert_fail('请选择要修改密码的用户')
        if password is None or validate(password=password) is not None:
            alert_fail('密码不符合要求')
        # one time token
        TempSessionManager.logout()
        # set password
        for user in users:
            if user.id in user_id:
                UserManager.set_password(user, password)
        return redirect(
            url_for('.login', next=request.args.get('next', '')), code=SEE_OTHER
        )

    if request.method == 'POST':
        try:
            return on_post()
        except AlertFail:
            pass
    # GET and error POST will render this
    return render_template('reset_password.html', student_id=student_id, users=users)


@web.route('/oauth/authorize', methods=['GET', 'POST'])
@require_logged_in
def oauth_authorize():
    response_type = request.args['response_type']
    client_id = request.args['client_id']
    redirect_uri = request.args['redirect_uri']
    scope = request.args['scope']
    state = request.args.get('state', '')

    if response_type != 'code':
        abort(BAD_REQUEST, 'Invalid response_type')
    app = OauthManager.get_app(client_id)
    if app is None or not OauthManager.redirect_uri_is_valid(app, redirect_uri):
        abort(BAD_REQUEST, 'Invalid redirect_uri')
    scopes = set(scope.split(' '))
    for scope in scopes:
        if not OauthManager.scope_is_valid(app, scope):
            abort(BAD_REQUEST, f'Invalid scope {scope}')

    if request.method == 'GET':
        redirect_hostname = urlsplit(redirect_uri).hostname
        return render_template('oauth_authorize.html', app=app, scopes=scopes, redirect_hostname=redirect_hostname)
    elif request.method == 'POST':
        code = OauthManager.create_code(app, redirect_uri, scopes)
        scheme, netloc, path, query, fragment = urlsplit(redirect_uri)
        if query != '':
            query += '&'
        query += urlencode([('state', state), ('code', code)])
        return redirect(urlunsplit((scheme, netloc, path, query, fragment)), SEE_OTHER)


@web.route('/logout', methods=['POST'])
def logout():
    SessionManager.logout()
    return redirect(url_for('.index'), SEE_OTHER)


@ignore_alert_fail
def process_register():
    username = request.form.get('username')
    password = request.form.get('password')
    friendly_name = request.form.get('friendly_name')
    student_id = request.form.get('student_id')
    if username is None or password is None or friendly_name is None or student_id is None:
        abort(BAD_REQUEST)
    error = validate(username, password, friendly_name, student_id)
    if error is not None:
        alert_fail(error)

    user = UserManager.add_user(username, student_id, friendly_name, password, 0)
    return create_session(user)

@web.route('/register', methods=['GET', 'POST'])
def register():
    if WebConfig.Block_Register:
        abort(NOT_FOUND)
    if request.method == 'POST':
        resp = process_register()
        if resp is not None:
            return resp
    return render_template('register.html', student_id=request.args.get('student-id', ''))


@web.route('/problem')
@require_logged_in
def problem_list():
    problem_id = request.args.get('id', '')
    if problem_id != '':
        return redirect(url_for('.problem', problem=int(problem_id)))

    res = paged_search_limitoffset(WebConfig.Problems_Each_Page, ProblemManager.ProblemSearch)
    count_under_11000 = db.scalar(res.query.where(Problem.id <= 11000).with_only_columns(sa.func.count()))
    assert count_under_11000 is not None
    max_page_under_11000 = ceil(count_under_11000 / WebConfig.Problems_Each_Page)

    return render_template('problem_list.html', problems=res.entities,
                            pages=gen_page_for_problem_list(res.page, res.max_page, max_page_under_11000),
                            args=dict(filter(lambda e: e[0] != 'page', request.args.items())))

@web.route('/problem/<problem:problem>')
@require_logged_in
def problem(problem: Problem):
    plan_summary: JudgePlanSummary = load_dataclass(problem.plan_summary, commons.task_typing.__dict__)
    limits = []
    if plan_summary is not None:
        limits = [testpoint.limits for group in plan_summary.subtasks for testpoint in group.testpoints if testpoint.limits is not None]
    return render_template('problem_details.html', problem=problem, plan_summary=plan_summary, limits=limits)


@ignore_alert_fail
def process_problem_admin(problem: Problem):
    action = request.form['action']
    if action == 'edit':
        set_tab('overview')
        problem.title = request.form['title']
        problem.release_time = datetime.fromisoformat(request.form['time'])
        problem.problem_type = int(request.form['problem_type'])
        problem.allow_public_submissions = request.form['allow_public_submissions'] == 'true'
        alert_success('编辑基本信息成功')
    elif action == 'hide':
        set_tab('overview')
        ProblemManager.hide_problem(problem)
        alert_success('已取消发布')
    elif action == 'show':
        set_tab('overview')
        ProblemManager.show_problem(problem)
        alert_success('已发布题目')
    elif action == 'delete':
        set_tab('overview')
        if request.form['confirm'] != str(problem.id):
            alert_fail('输入的题号不正确')
        course_id = problem.course_id
        ProblemManager.delete_problem(problem)
        return redirect(url_for('.course_admin', course=course_id, tab='problem'), SEE_OTHER)
    elif action == 'priv-add':
        set_tab('privileges')
        username = request.form['username']
        user = UserManager.get_user_by_username(username)
        if user is None:
            alert_fail(f'用户 {repr(username)} 不存在')
        priv_type_str = request.form['privilege']
        if priv_type_str == 'readonly':
            priv_type = ProblemPrivilegeType.readonly
        elif priv_type_str == 'owner':
            priv_type = ProblemPrivilegeType.owner
        else:
            alert_fail(f'未知权限类型 {repr(priv_type_str)}')
        comment = request.form['comment']
        db.add(ProblemPrivilege(user_id=user.id, problem_id=problem.id,
                                privilege=priv_type, comment=comment))
        db.flush()
        UserManager.flush_privileges(user)
        alert_success('已赋予权限')
    elif action == 'priv-remove':
        set_tab('privileges')
        priv = db.get(ProblemPrivilege, int(request.form['id']))
        if priv is None:
            abort(BAD_REQUEST)
        user = priv.user
        if priv.problem != problem:
            abort(BAD_REQUEST)
        db.delete(priv)
        db.flush()
        UserManager.flush_privileges(user)
        alert_success('已移除权限')
    else:
        abort(BAD_REQUEST)

@web.route('/problem/<problem:problem>/admin', methods=['GET', 'POST'])
@require_logged_in
def problem_admin(problem: Problem):
    if not g.can_write:
        abort(FORBIDDEN)

    if request.method == 'POST':
        resp = process_problem_admin(problem)
        if resp is not None:
            return resp

    submission_count = db.query(JudgeRecordV2.id).where(JudgeRecordV2.problem_id == problem.id).count()
    ac_count = db.query(JudgeRecordV2.id).where(JudgeRecordV2.problem_id == problem.id).where(JudgeRecordV2.status == JudgeStatus.accepted).count()

    return render_template('problem_admin.html', problem=problem,
                           submission_count=submission_count, ac_count=ac_count)

@web.route('/problem/admin')
def problem_admin_form():
    id = request.args.get('id')
    if id is None:
        abort(BAD_REQUEST)
    return redirect(url_for('.problem_admin', problem=int(id)))


@web.route('/problem/<problem:problem>/submit', methods=['GET', 'POST'])
@require_logged_in
def problem_submit(problem: Problem):
    if request.method == 'GET':
        if problem.problem_type == 0:
            languages_accepted = ProblemManager.languages_accepted(problem)
            return render_template('problem_submit.html',
                                   problem=problem,
                                   languages_accepted=languages_accepted)
        elif problem.problem_type == 1:
            quiz_json = QuizManager.get_json_from_data_service_by_id(QuizTempDataConfig, problem.id)
            problems = None
            if quiz_json is not None:
                problems = quiz_json['problems']
                for i in problems:
                    i['answer'] = ''

            return render_template('quiz_submit.html', problem=problem,
                                   problems=problems)
    else:
        public = bool(request.form.get('public', 0))  # 0 or 1
        lang_str = str(request.form.get('language'))
        if lang_str == 'quiz':
            user_code = json.dumps(request.form.to_dict(), ensure_ascii=False)
        else:
            user_code = request.form['code']
        if not JudgeManager.can_create(problem, public, lang_str, user_code):
            abort(BAD_REQUEST)
        submission = JudgeManager.create_submission(
            public=public,
            language=lang_str,
            user=g.user,
            problem_id=problem.id,
            code=user_code,
        )
        return redirect(url_for('.submission', submission=submission), SEE_OTHER)


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

    return render_template('problem_rank.html', problem=problem,
                           submissions=submissions, Sorting=sort_parameter,
                           real_name_map=real_name_map, has_real_name=has_real_name,
                           languages=languages)


@web.route('/problem/<problem:problem>/discuss', methods=['GET', 'POST'])
@require_logged_in
def problem_discuss(problem: Problem):
    if request.method == 'GET':
        if g.in_exam:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', problem=problem,
                                   Blocked=True)  # Discussion Closed
        data = problem.discussions
        discussions = []
        for ele in data:
            tmp = [ele.id, ele.user.username, ele.data, readable_time(ele.created_at)]
            # tmp[4]: editable
            tmp.append(ele.user_id == g.user.id or g.user.privilege >= Privilege.SUPER)
            discussions.append(tmp)
        return render_template('problem_discussion.html', problem=problem,
                               Discuss=discussions)
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

def reads_problem(func):
    @wraps(func)
    def wrapped(problem, *args, **kwargs):
        if not g.can_read:
            abort(FORBIDDEN)
        return func(problem, *args, **kwargs)
    return wrapped

def writes_problem(func):
    @wraps(func)
    def wrapped(problem, *args, **kwargs):
        if not g.can_write:
            abort(FORBIDDEN)
        return func(problem, *args, **kwargs)
    return wrapped

@web.route('/problem/<problem:problem>/description', methods=['GET', 'PUT'])
@writes_problem
def problem_description(problem: Problem):
    rows = 'description', 'input', 'output', 'examples', 'example_input', 'example_output', 'data_range'
    if request.method == 'GET':
        data = {}
        for row in rows:
            data[row] = getattr(problem, row)
        return data

    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    for row in rows:
        content = form.get(row, None)
        if content == 'None' or content == '':
            content = None
        setattr(problem, row, content)
    return make_response('', NO_CONTENT)

@web.route('/problem/<problem:problem>/upload-url')
@writes_problem
def problem_upload_url(problem: Problem):
    return generate_s3_public_url('put_object', {
        'Bucket': S3Config.Buckets.problems,
        'Key': f'{problem.id}.zip',
    }, ExpiresIn=3600)

@web.route('/problem/<problem:problem>/update-plan', methods=['POST'])
@writes_problem
def problem_update_plan(problem: Problem):
    url = urljoin(SchedulerConfig.base_url, f'problem/{problem.id}/update')
    res = requests.post(url).json()
    if res['result'] == 'ok':
        problem.languages_accepted = res['languages']
        problem.plan_summary = res['summary']
        return 'ok'
    elif res['result'] == 'invalid problem':
        return f'Invalid problem: {res["error"]}'
    elif res['result'] == 'system error':
        return f'System error: {res["error"]}'
    return 'Bad result from scheduler'

@ignore_alert_fail
def handle_problem_data_zip() -> bool:
    if 'submit' not in request.args:
        return False
    if request.args.get('agree') != 'yes':
        alert_fail('请阅读提示后再下载数据')
    g.user.data_license_agreed = True
    return True

@web.route('/problem/<problem:problem>/data-zip', methods=['GET', 'POST'])
def problem_data_zip(problem: Problem):
    if not g.is_admin and not g.can_read:
        abort(FORBIDDEN)
    if not g.can_read and not g.user.data_license_agreed:
        ok = handle_problem_data_zip()
        if ok is None or not ok:
            return render_template('data_license.html')
    key = f'{problem.id}.zip'
    url = generate_s3_public_url('get_object', {
        'Bucket': S3Config.Buckets.problems,
        'Key': key,
    }, ExpiresIn=3600)
    return redirect(url, SEE_OTHER)

@web.route('/problem/<problem:problem>/attachment/', methods=['GET', 'POST'])
def problem_attachment_index(problem: Problem):
    if request.method == 'POST':
        if not g.can_write:
            abort(FORBIDDEN)
        name = request.form['name']
        size_bytes = int(request.form['length'])
        try:
            attachment = ProblemManager.create_attachment(problem, name, size_bytes)
        except ValueError as e:
            abort(make_response(str(e), BAD_REQUEST))
        return ProblemManager.upload_url_of_attachment(attachment)

    return [
        {
            'name': x.name,
            'size': x.size_bytes,
            'user': x.user.username if g.can_write else None,
            'url': url_for('.problem_attachment', problem=problem, name=x.name),
        } for x in problem.attachments
    ]

@web.route('/problem/<problem:problem>/attachment/<name>', methods=['GET', 'DELETE'])
def problem_attachment(problem: Problem, name: str):
    attachment = ProblemManager.get_attachment(problem, name)
    if attachment is None: abort(NOT_FOUND)

    if request.method == 'DELETE':
        if not g.can_write:
            abort(FORBIDDEN)
        ProblemManager.delete_attachment(attachment)
        return make_response('', NO_CONTENT)

    return redirect(ProblemManager.download_url_of_attachment(attachment))


@web.route('/status')
@require_logged_in
def status():
    res = paged_search_limitoffset(JudgeConfig.Judge_Each_Page, JudgeManager.SubmissionSearch)
    submissions = res.entities

    real_name_map = {}
    show_links = {}
    show_title = {}
    for submission in submissions:
        if submission.user.student_id not in real_name_map:
            real_name_map[submission.user.student_id] = \
                RealnameManager.query_realname_for_current_user(submission.user.student_id)
        show_links[submission] = JudgeManager.can_show(submission)
        show_title[submission] = ProblemManager.can_show(submission.problem)
    return render_template('status.html', pages=gen_page(res.page, res.max_page),
                           submissions=submissions,
                           real_name_map=real_name_map,
                           show_links=show_links,
                           show_title=show_title,
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

@web.route('/get-code-old', methods=['POST'])
def get_code_old():
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

@web.route('/code')
def code_compat():
    submit_id = request.args.get('submit_id')
    if submit_id is None:
        abort(NOT_FOUND)
    return redirect(url_for('.submission', submission=int(submit_id)))

@web.route('/code/<submission:submission>/')
@require_logged_in
def submission(submission: JudgeRecordV2):
    if submission.id <= OldJudgeManager.max_id():
        return code_old(submission.id)

    real_name = RealnameManager.query_realname_for_current_user(submission.user.student_id)
    return render_template('judge_detail.html',
                           submission=submission,
                           real_name=real_name,
                           code_url=JudgeManager.sign_code_url(submission),
                           details=JudgeManager.get_details(submission),
                           show_score=JudgeManager.should_show_score(submission))

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
        return redirect(url_for('.problemset', contest=int(contest_id)))
    implicit_contests = ContestManager.get_implicit_contests(g.user)
    user_contests = set(implicit_contests).union(g.user.external_contests)

    type_ids = [0, 2] if type == 'contest' else [1]
    desc = ContestManager.ContestSearch(type_ids)
    res = paged_search_limitoffset(WebConfig.Contests_Each_Page, desc)

    return render_template('contest_list.html', contests=res.entities,
                           get_status=ContestManager.get_status,
                           reason_cannot_join=ContestManager.reason_cannot_join,
                           implicit_contests=implicit_contests,
                           user_contests=user_contests,
                           type=type, type_zh=type_zh,
                           pages=gen_page(res.page, res.max_page),
                           args=dict(filter(lambda e: e[0] != 'page' and e[0] != 'all', request.args.items())))

@web.route('/contest')
def contest_list():
    return contest_list_generic('contest', '比赛')

@web.route('/homework')
def homework_list():
    return contest_list_generic('homework', '作业')

@web.route('/contest/<int:contest_id>')
def contest(contest_id):
    return redirect(url_for('.problemset', contest=contest_id))
@web.route('/homework/<int:contest_id>')
def homework(contest_id):
    return redirect(url_for('.problemset', contest=contest_id))

@web.route('/problemset/<contest:contest>')
def problemset(contest: Contest):
    problems_visible = ContestManager.problems_visible(contest)
    data = ContestManager.get_board_view(contest)
    student_ids = set(x['student_id'] for x in data)
    real_name_map = dict((s, RealnameManager.query_realname_for_contest(s, contest)) for s in student_ids)
    has_real_name = any(real_name_map[s] is not None for s in real_name_map)
    contest_status = ContestManager.get_status(contest)
    my_data = next((x for x in data if x['id'] == g.user.id), None)

    time_elapsed = (g.time - contest.start_time).total_seconds()
    time_overall = (contest.end_time - contest.start_time).total_seconds()
    if time_overall > 0:
        percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)
    else:
        percentage = 0 if time_elapsed < 0 else 100

    return render_template(
        'contest.html',
        contest=contest,
        status=contest_status,
        percentage=percentage,
        problems_visible=problems_visible,
        has_real_name=has_real_name,
        real_name_map=real_name_map,
        data=data,
        my_data=my_data,
    )


def export_problemset(contest: Contest):
    def format_realname(rr: Optional[RealnameReference]) -> str:
        if rr is None:
            return 'Unknown'
        name = rr.real_name
        for g in sorted(rr.groups, key=lambda g: g.name, reverse=True):
            name = f'[{g.name}]{name}'
        return name.replace('/', '_')

    def filename (s: JudgeRecordV2) -> str:
        ext = language_info[s.language].extension
        ext = '.' + ext if ext is not None else ''
        user = player_by_id[s.user_id]
        late_phrase = '-late' if ContestManager.is_late(contest, s.created_at) else ''
        return f'{user.student_id}-{names[user.id]}-{user.username}-{s.id}-P{s.problem_id}-{s.status.name}-{s.score}{late_phrase}{ext}'

    def process_prelude(content: str, language: str):
        prelude_formatting = {
            'cpp': ('/**\n', ' * ', '\n */'),
            'verilog': ('/**\n', ' * ', '\n */'),
            'python': ('', '# ', ''),
        }

        if language not in prelude_formatting:
            return content
        prefix, line_prefix, postfix = prelude_formatting[language]
        return (prefix +
                '\n'.join(line_prefix + x for x in content.strip().splitlines()) +
                postfix)

    def prelude (s: JudgeRecordV2) -> str:
        details_message = ''
        message = s.message
        if s.details is not None:
            details: ProblemJudgeResult = deserialize(s.details)
            details_message = '\n'.join(f'{group.name}: {group.score} {group.result}' for group in details.groups)
        user = player_by_id[s.user_id]
        late_phrase = ''
        if ContestManager.is_late(contest, s.created_at):
            late_phrase = ' (Late Submission)'
        content = f'''
{user.student_id} {names[user.id]} ({user.username})
Problem {s.problem_id} - {problem_by_id[s.problem_id].title}
Time: {s.created_at.strftime('%Y-%m-%d %H:%M:%S')}{late_phrase}
Status: {s.status.name}
Score: {s.score}
Message: {message}

{details_message}
'''.strip()
        return process_prelude(content, s.language) + '\n\n'

    players: Iterable[User]
    if contest.rank_all_users:
        players = ContestManager.get_players(contest)
    else:
        players = ContestManager.get_implicit_players(contest)
    player_by_id = dict((x.id, x) for x in players)
    problem_by_id = dict((x.id, x) for x in contest.problems)
    names = dict(
        (x.id, format_realname(RealnameManager.query_realname_for_contest(x.student_id, contest)))
        for x in players)
    submissions = ContestManager.get_contest_submissions(contest, players)
    submissions = sorted(submissions, key=lambda x: (x.user_id, x.problem_id))
    scores_list = ContestManager.get_scores(contest)
    scores = {}
    for player in scores_list:
        scores[player['id']] = player

    zip_filename = f'/tmp/export-{contest.id}-{uuid4()}.zip'
    g.export_filename = zip_filename
    f = ZipFile(zip_filename, 'w')
    for _, tries_i in groupby(submissions, lambda x: (x.user_id, x.problem_id)):
        tries = list(tries_i)
        problem_data = [ x for x in scores[tries[0].user_id]['problems'] if x['id'] == tries[0].problem_id ][0]
        if not problem_data['late']:
            tries = [ x for x in tries if not ContestManager.is_late(contest, x.created_at) ]
            if len(tries) == 0: continue
        score = max(x.score for x in tries)
        score_tries = list(sorted(filter(lambda x: x.score == score, tries), key=lambda x: x.id))
        s = score_tries[-1]
        r = s3_internal.get_object(Bucket=S3Config.Buckets.submissions,
                                   Key=f'{s.id}.code')['Body'].read()
        with f.open(f'{s.problem_id}/{filename(s)}', 'w') as w:
            w.write(prelude(s).encode())
            w.write(r)

    f.close()
    return send_file(zip_filename, as_attachment=True, download_name=f'export-{contest.id}.zip')

@web.after_request
def export_problemset_cleanup(resp):
    if 'export_filename' in g:
        try:
            os.remove(g.export_filename)
        except Exception:
            pass
    return resp

@ignore_alert_fail
def process_problemset_admin(contest: Contest):
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
        contest.rank_all_users = form.get('rank_all_users', 'off') == 'on'
        ContestManager.flush_cache(contest)
        alert_success('基本信息已保存')
    elif action == 'delete':
        if request.form['confirm'] != str(contest.id):
            alert_fail('输入的比赛编号不正确')
        course_id = contest.course_id
        ContestManager.delete_contest(contest)
        return redirect(url_for('.course_admin', course=course_id), SEE_OTHER)
    elif action == 'requirements':
        cc_type_str = form.get('type', 'none')
        cc_type = getattr(CompletionCriteriaType, cc_type_str, None)
        if not isinstance(cc_type, CompletionCriteriaType):
            alert_fail(f'作业要求类型 {repr(cc_type_str)} 不正确')
        cc_value = form.get('completion_criteria', None)
        if cc_value is not None and len(cc_value) > completion_criteria_max_length:
            alert_fail('作业要求超出长度限制')
        if cc_type == CompletionCriteriaType.none:
            cc_value = None
        err = ContestManager.validate_completion_criteria(contest, cc_type, cc_value)
        if err is not None:
            alert_fail(err)
        contest.completion_criteria_type = cc_type
        contest.completion_criteria = cc_value

        languages = []
        for lang in language_info:
            if form.get(f'lang-{lang}', 'off') == 'on':
                languages.append(lang)
        contest.allowed_languages = None if len(languages) == len(language_info) or len(languages) == 0 else languages

        late_submission_enable = form.get('enable', 'no') == 'yes'
        if late_submission_enable:
            ddl_string = form.get('deadline', '')
            if ddl_string == '':
                alert_fail('请填写迟交截止时间')
            ddl = datetime.fromisoformat(ddl_string)
            if ddl <= contest.end_time:
                alert_fail('迟交截止时间需晚于结束时间')
            contest.late_submission_deadline = ddl
        else:
            contest.late_submission_deadline = None

        db.flush()
        ContestManager.flush_cache(contest)
        alert_success('作业要求已保存')
    elif action == 'groups':
        if form.get('all', 'off') == 'on':
            contest.group_ids = None
        else:
            gs = []
            for group in contest.course.groups:
                if form.get(f'group-{group.id}', 'off') == 'on':
                    gs.append(group.id)
            contest.group_ids = gs
        ContestManager.flush_cache(contest)
        alert_success('分组已保存')
    elif action == 'export':
        return export_problemset(contest)
    elif action == 'duplicate':
        if form.get('confirm') != 'duplicate':
            abort(BAD_REQUEST)
        new_contest = ContestManager.duplicate_contest(contest)
        return redirect(url_for('.problemset_admin', contest=new_contest), SEE_OTHER)
    else:
        abort(BAD_REQUEST)

@web.route('/problemset/<contest:contest>/admin', methods=['GET', 'POST'])
def problemset_admin(contest: Contest):
    if not g.can_write:
        abort(FORBIDDEN)

    if request.method == 'POST':
        resp = process_problemset_admin(contest)
        if resp is not None:
            return resp

    scores = ContestManager.get_scores(contest)
    # problem id -> (try count, ac count)
    problem_stats = dict((problem.id, { 'try': 0, 'ac': 0 }) for problem in contest.problems)
    completion_stats = { 'total': 0, 'completed': 0, 'completed-late': 0, 'errors': set() }
    for player in scores:
        if player['is_external'] and not contest.rank_all_users:
            continue
        if contest.completion_criteria_type != CompletionCriteriaType.none:
            completion_stats['total'] += 1  # type: ignore
            if type(player['completed']) == str:
                completion_stats['errors'].add(player['completed'])  # type: ignore
            elif player['completed'] == True:  # can also be str
                if player['late_time'] is not None:
                    completion_stats['completed-late'] += 1  # type: ignore
                else:
                    completion_stats['completed'] += 1  # type: ignore
        for problem in player['problems']:
            if problem['count'] > 0:
                problem_stats[problem['id']]['try'] += 1
            if problem['accepted']:
                problem_stats[problem['id']]['ac'] += 1

    return render_template('contest_admin.html', contest=contest,
                           problem_stats=problem_stats,
                           completion_stats=completion_stats,
                           completion_criteria_max_length=completion_criteria_max_length)

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

    ContestManager.flush_cache(contest)
    return redirect(url_for('.problemset_admin', contest=contest), SEE_OTHER)

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

    ContestManager.flush_cache(contest)
    return redirect(url_for('.problemset_admin', contest=contest), SEE_OTHER)

@web.route('/problemset/<contest:contest>/quit', methods=['POST'])
def problemset_quit(contest: Contest):
    ContestManager.quit(contest)
    return redirect(request.form['back'], SEE_OTHER)

@web.route('/problemset/<contest:contest>/join', methods=['POST'])
def problemset_join(contest: Contest):
    ContestManager.join(contest)
    return redirect(url_for('.problemset', contest=contest), SEE_OTHER)

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
        .order_by(Course.id.desc())
        .limit(limit).offset(offset)
    ).all()

    return render_template('course_list.html', courses=courses,
                           title=title,
                           description=description,
                           show_tag=show_tag,
                           show_term=show_term,
                           can_join=CourseManager.can_join,
                           get_enrollment=UserManager.get_enrollment,
                           get_realname_reference=RealnameManager.query_realname_for_course,
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
    return course_list_generic(f'{tag.name} 班级列表', '', stmt, show_tag=False)

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
    contests.sort(key=lambda c: c.start_time, reverse=True)
    contests_enrolled = [x.id for x in ContestManager.get_contests_for_user(g.user)]
    statuses = [ContestManager.get_status_for_card(c, c.id in contests_enrolled) for c in contests]

    return render_template('course_contest_list.html', type=type,
                           course=course, contests=statuses,
                           show_type=type != 'homework')

@web.route('/course/<course:course>/contest')
def course_contest_list(course: Course):
    return course_contest_list_generic(course, 'contest')

@web.route('/course/<course:course>/homework')
def course_homework_list(course: Course):
    return course_contest_list_generic(course, 'homework')

@web.route('/course/<course:course>/ignore', methods=['POST'])
def course_ignore(course: Course):
    if not CourseManager.can_join(course):
        abort(BAD_REQUEST)
    if course.id not in g.user.ignored_course_ids:
        g.user.ignored_course_ids.append(course.id)
    return redirect(url_for('.index'), SEE_OTHER)

@web.route('/course/<course:course>/join', methods=['POST'])
def course_join(course: Course):
    CourseManager.join(course)
    return redirect(url_for('.course', course=course), SEE_OTHER)

@web.route('/course/<course:course>/quit', methods=['POST'])
def course_quit(course: Course):
    CourseManager.quit(course)
    return redirect(request.form['back'], SEE_OTHER)

@ignore_alert_fail
def process_course_admin(course: Course):
    form = request.form
    action = form['action']
    if action == 'edit':
        set_tab('overview')
        course.name = form['name']
        course.description = form['description']
        alert_success('已编辑基本信息')
    elif action == 'realname-create':
        set_tab('user')
        data = [line.split(',') for line in request.form['data'].strip().splitlines()]
        for line in data:
            groups: List[Group] = []
            if len(line) > 2:
                group_names = [x.strip() for x in line[2].split('|')]
                for group_name in group_names:
                    group = CourseManager.get_group_by_name(course, group_name)
                    if group is None:
                        db.rollback()
                        return alert_fail(f'分组 {repr(group_name)} 不存在')
                    groups.append(group)
            rr = RealnameManager.query_realname_for_course(line[0], course.id)
            if rr is not None:
                for e in rr.enrollments:
                    if e.admin:
                        alert_fail(f'不能修改班级管理员 {repr(e.user.username)} 的实名信息')
            RealnameManager.add_student(line[0], line[1], course, groups)
        alert_success('编辑实名信息成功')
    elif action == 'realname-delete':
        set_tab('user')
        rr_id = int(form['id'])
        rr = db.get(RealnameReference, rr_id)
        if rr is None or rr.course_id != course.id:
            abort(BAD_REQUEST)
        for e in rr.enrollments:
            if e.admin:
                alert_fail(f'不能删除班级管理员 {repr(e.user.username)} 的实名信息')
        db.delete(rr)
        db.flush()
        alert_success('已删除实名信息')
    elif action == 'problem-create':
        problem = ProblemManager.create_problem(course)
        return redirect(url_for('.problem_admin', problem=problem), SEE_OTHER)
    elif action == 'contest-create':
        contest = ContestManager.create_contest(course)
        return redirect(url_for('.problemset_admin', contest=contest), SEE_OTHER)
    elif action == 'group-create':
        set_tab('group')
        name = form['name']
        if CourseManager.get_group_by_name(course, name) is not None:
            alert_fail(f'分组 {repr(name)} 已存在')
        group = Group(name=name,
                      description=form.get('description', ''),
                      course_id=course.id)
        db.add(group)
        db.flush()
        g.expand_group = str(group.id)
        alert_success('已添加分组')
    elif action == 'group-edit':
        set_tab('group')
        group = CourseManager.get_group_in_course(course, int(form['id']))
        if group is None:
            abort(BAD_REQUEST)
        name = form['name']
        existing_group = CourseManager.get_group_by_name(course, name)
        if existing_group is not None and existing_group != group:
            abort(BAD_REQUEST, f'分组 {repr(name)} 已存在')
        group.name = name
        group.description = form['description']
        g.expand_group = str(group.id)
        alert_success('修改分组成功')
    elif action == 'group-delete':
        set_tab('group')
        group = CourseManager.get_group_in_course(course, int(form['id']))
        if group is None:
            alert_fail('分组不存在')
        db.delete(group)
        db.flush()
        alert_success('已删除分组')
    elif action == 'user-delete':
        set_tab('user')
        usernames = form['data'].strip().splitlines()
        for username in usernames:
            user = UserManager.get_user_by_username(username)
            if user is None:
                db.rollback()
                alert_fail(f'用户 {repr(username)} 不存在')
            enrollment = UserManager.get_enrollment(user, course)
            if enrollment is None:
                continue
            if enrollment.admin:
                db.rollback()
                alert_fail(f'用户 {repr(username)} 是班级管理员，请先移除管理权限')
            db.delete(enrollment)
            db.flush()
        alert_success('已移除用户')
    elif action == 'user-demote':
        set_tab('user')
        enrollment = db.get(Enrollment, int(form['id']))
        if enrollment is None or not enrollment.admin or enrollment.course_id != course.id:
            abort(BAD_REQUEST)
        enrollment.admin = False
        UserManager.flush_privileges(enrollment.user)
        alert_success('已移除权限')
    elif action == 'user-promote':
        set_tab('user')
        usernames = form['data'].strip().splitlines()
        for username in usernames:
            user = UserManager.get_user_by_username(username)
            if user is None:
                db.rollback()
                alert_fail(f'用户 {repr(username)} 不存在')
            enrollment = UserManager.get_enrollment(user, course)
            if enrollment is None:
                db.rollback()
                alert_fail(f'用户 {repr(username)} 未加入班级')
            if enrollment.realname_reference is None:
                db.rollback()
                alert_fail(f'用户 {repr(username)} 未添加实名信息')
            enrollment.admin = True
            UserManager.flush_privileges(user)
        alert_success('已添加权限')
    else:
        abort(BAD_REQUEST, f'Unknown action {action}')

@web.route('/course/<course:course>/admin', methods=['GET', 'POST'])
def course_admin(course: Course):
    if not g.can_write:
        abort(FORBIDDEN)

    g.expand_group = request.args.get('group', None)
    if request.method == 'POST':
        resp = process_course_admin(course)
        if resp is not None:
            return resp

    return render_template('course_admin.html', course=course)

@web.route('/course/<course:course>/realname', methods=['GET', 'POST'])
def course_realname_export(course: Course):
    if not g.can_write:
        abort(FORBIDDEN)
    def format(rr: RealnameReference):
        groups = '|'.join(g.name for g in rr.groups)
        if len(groups) > 0:
            groups = ',' + groups
        return f'{rr.student_id},{rr.real_name}{groups}'
    text = '\n'.join(format(rr) for rr in course.realname_references)
    resp = make_response(text)
    resp.content_type = 'text/plain;charset=utf-8'
    return resp

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
            abort(BAD_REQUEST, f'学工号 {repr(id)} 没有对应的实名信息')
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
    return redirect(url_for('.course_admin', course=course, tab='group', group=str(group.id)), SEE_OTHER)


@ignore_alert_fail
def process_profile():
    form = request.form
    friendly_name = form.get('friendly_name')
    password = form.get('password')
    password_repeat = form.get('password_repeat')
    if password != password_repeat:
        alert_fail('两次输入的密码不一致')
    if password == '': password = None
    if friendly_name == '': friendly_name = None

    error = validate(friendly_name=friendly_name, password=password)
    if error is not None:
        alert_fail(error)

    if friendly_name is not None:
        g.user.friendly_name = friendly_name
    if password is not None:
        UserManager.set_password(g.user, password)
    alert_success('成功修改个人信息')

@web.route('/settings/profile', methods=['GET', 'POST'])
@require_logged_in
def profile():
    if request.method == 'POST':
        process_profile()
    return render_template('profile.html')

@ignore_alert_fail
def process_settings_api():
    form = request.form
    action = form['action']
    if action == 'app:revoke':
        app_id = int(form['id'])
        app = OauthManager.from_app_id(app_id)
        if app is None:
            return alert_fail('此应用不存在')
        OauthManager.revoke_app(app)
        alert_success(f'已撤销 {app.name} 的授权')
    elif action == 'pat:create':
        name = form['name']
        scopes = [s for s in api_scopes if form.get(f'scope-{s}', 'off') == 'on']
        token = AccessToken()
        token.token = randtoken()
        token.name = name
        token.user_id = g.user.id
        token.scopes = scopes
        token.expires_at = g.time + timedelta(days=365)
        db.add(token)
        alert_success(f'访问令牌已创建。请记下您的令牌： {token.token} 。此令牌以后不会再次展示给您。')
    elif action == 'pat:revoke':
        id = int(form['id'])
        t = db.get(AccessToken, id)
        if t is None:
            alert_fail('访问令牌不存在')
        if t.user_id != g.user.id or t.app_id is not None:
            alert_fail('访问令牌不属于本用户')
        if not token_is_valid(t):
            alert_fail('令牌已经失效')
        t.revoked_at = g.time
        db.flush()
        alert_success('已撤销令牌')
    else:
        alert_fail(f'Unknown action {action}')

@web.route('/settings/api', methods=['GET', 'POST'])
@require_logged_in
def settings_api():
    if request.method == 'POST':
        process_settings_api()

    user: User = g.user
    tokens = user.access_tokens
    app_ids = set(token.app_id for token in tokens if token.app_id is not None and token_is_valid(token))
    apps = [app for app in (OauthManager.from_app_id(id) for id in app_ids) if app is not None]
    app_tokens = dict((app, [t for t in tokens if t.app_id == app.id and token_is_valid(t)]) for app in apps)
    apps_info = [{
        'app': app,
        'last_used': max(token.created_at for token in app_tokens[app]),
        'scopes': sort_scopes(set(scope for token in app_tokens[app] for scope in token.scopes)),
    } for app in apps if len(app_tokens[app]) > 0]
    apps_info.sort(key=lambda x: x['last_used'], reverse=True)  # type: ignore

    pats = [t for t in tokens if t.app_id is None and token_is_valid(t)]

    return render_template('settings_api.html', apps=apps_info, pats=pats)


# admin

def require_admin(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not g.is_admin:
            abort(FORBIDDEN)
        return func(*args, **kwargs)
    return wrapped

@ignore_alert_fail
def process_admin():
    form = request.form
    action = form['action']
    if action == 'user':
        if g.user.privilege < Privilege.SUPER:
            abort(FORBIDDEN)
        set_tab('user')
        user = UserManager.get_user_by_username(form['username'])
        if user is None:
            alert_fail('用户不存在')
        args = {}
        for key in 'student_id', 'friendly_name', 'password':
            args[key] = request.form.get(key)
            if args[key] == '': args[key] = None
        error = validate(**args)
        if error is not None:
            alert_fail(error)
        if args['student_id'] is not None:
            user.student_id = args['student_id']
        if args['friendly_name'] is not None:
            user.student_id = args['friendly_name']
        if args['password'] is not None:
            UserManager.set_password(user, args['password'])
        priv = request.form.get('privilege')
        if priv is not None and priv != '':
            user.privilege = int(priv)
        db.flush()
        alert_success('修改用户信息成功')

@web.route('/admin/', methods=['GET', 'POST'])
@require_admin
def admin():
    if request.method == 'POST':
        process_admin()
    admin_courses = CourseManager.get_admin_courses(g.user, current_only=False)
    return render_template('admin.html',
                           admin_courses=admin_courses)

@web.route('/admin/su', methods=['POST'])
@require_admin
def admin_su():
    if g.user.privilege < Privilege.SUPER:
        abort(FORBIDDEN)
    user = UserManager.get_user_by_username(request.form['username'])
    if user is None:
        abort(BAD_REQUEST, '用户不存在')
    SessionManager.switch_user(user)
    return redirect(url_for('.index'))


def problem_admin_api(callback, success_retcode):
    type = request.form['type']

    if type == 'by_judge_id':
        id = request.form['judge_id']
        id_list = id.strip().splitlines()
        try:
            for i in id_list:
                submission = JudgeManager.get_submission(int(i))
                if submission is None:
                    raise NotFoundException
                if not ProblemManager.can_write(submission.problem):
                    raise NotFoundException
                callback(submission)
            return success_retcode
        except NotFoundException:
            return ReturnCode.ERR_BAD_DATA
    elif type == 'by_problem_id':
        ids = request.form['problem_id'].strip().splitlines()
        try:
            for id in ids:
                problem = ProblemManager.get_problem(int(id))
                if problem is None:
                    raise NotFoundException
                if not ProblemManager.can_write(problem):
                    raise NotFoundException
                JudgeManager.problem_judge_foreach(callback, id)
            return success_retcode
        except NotFoundException:
            return ReturnCode.ERR_BAD_DATA

@web.route('/admin/rejudge', methods=['POST'])
def admin_rejudge():
    return problem_admin_api(JudgeManager.rejudge, ReturnCode.SUC_REJUDGE)

@web.route('/admin/mark-void', methods=['POST'])
def admin_mark_void():
    return problem_admin_api(JudgeManager.mark_void, ReturnCode.SUC_DISABLE_JUDGE)

@web.route('/admin/abort-judge', methods=['POST'])
def admin_abort_judge():
    return problem_admin_api(JudgeManager.abort_judge, ReturnCode.SUC_ABORT_JUDGE)

@web.route('/admin/pic-url', methods=['POST'])
@require_admin
def admin_pic_url():
    length = int(request.form['length'])
    if length > max_pic_size:
        abort(REQUEST_ENTITY_TOO_LARGE)
    if length <= 0:
        abort(BAD_REQUEST)
    type = str(request.form['type'])
    if not type.startswith('image/'):
        abort(BAD_REQUEST)
    return generate_s3_public_url('put_object', {
        'Bucket': S3Config.Buckets.images,
        'Key': str(uuid4()),
        'ContentLength': length,
        'ContentType': type,
    }, ExpiresIn=3600)



# help

help_cache: Dict[str, Optional[str]] = {}

@web.route('/help/<path:page>')
def help(page):
    if re.search(r'[^-a-zA-Z0-9_/]', page) is not None or page[0] == '/':
        abort(NOT_FOUND)
    if page in help_cache:
        content = help_cache[page]
    else:
        try:
            with open(os.path.join(web.root_path, 'help', page + '.html'), 'r') as f:
                content = f.read()
        except FileNotFoundError:
            content = None
        help_cache[page] = content
    if content is None:
        abort(NOT_FOUND)
    match_title = re.search('<h1[^>]*>([^<]+)</h1>', content)
    if match_title is None:
        title = '帮助'
    else:
        title = match_title.group(1)
    return render_template('help.html', title=title, content=content)

@web.route('/help/')
def help_index():
    return help('index')


@web.route('/about')
def about():
    runners = JudgeManager.get_runner_status()
    return render_template('about.html', runners=runners)


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
            not_logged_in()
        try:
            return self.get(int(value))
        except ValueError:
            abort_converter(BAD_REQUEST, 'invalid argument')

    def to_url(self, value) -> str:
        if isinstance(value, int):
            return str(value)
        return str(value.id)

class ProblemConverter(ModelConverter):
    def get(self, model_id: int) -> Problem:
        problem = ProblemManager.get_problem(model_id)
        if not ProblemManager.can_show(problem):
            abort_converter(NOT_FOUND)
        g.can_read = ProblemManager.can_read(problem)
        g.can_write = ProblemManager.can_write(problem)
        g.in_exam = problem_in_exam(problem.id)
        return problem

class SubmissionConverter(ModelConverter):
    def get(self, model_id: int) -> JudgeRecordV2:
        submission = JudgeManager.get_submission(model_id)
        if not JudgeManager.can_show(submission):
            abort_converter(NOT_FOUND)
        g.can_write = JudgeManager.can_write(submission)
        g.can_abort = JudgeManager.can_abort(submission)
        return submission

class ContestConverter(ModelConverter):
    def get(self, model_id: int) -> Contest:
        contest = ContestManager.get_contest(model_id)
        if contest is None:
            abort_converter(NOT_FOUND)
        g.can_read = ContestManager.can_read(contest)
        g.can_write = ContestManager.can_write(contest)
        return contest

class CourseConverter(ModelConverter):
    def get(self, model_id: int) -> Course:
        course = CourseManager.get_course(model_id)
        if course is None:
            abort_converter(NOT_FOUND)
        g.can_read = CourseManager.can_read(course)
        g.can_write = CourseManager.can_write(course)
        return course


oj = Flask('WEB')
oj.url_map.converters['problem'] = ProblemConverter
oj.url_map.converters['submission'] = SubmissionConverter
oj.url_map.converters['contest'] = ContestConverter
oj.url_map.converters['course'] = CourseConverter
oj.register_blueprint(web, url_prefix='/OnlineJudge')
oj.jinja_env.add_extension('jinja2.ext.do')
oj.jinja_env.tests['None'] = oj.jinja_env.tests['none']
oj.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400

# url_for(xxx,_external=True) should give correct scheme
# nginx should set `proxy_set_header X-Forwarded-Proto $scheme;`
oj.wsgi_app = ProxyFix(oj.wsgi_app, x_proto=1, x_host=1)  # type: ignore


def appcontext_pushed_log(*args, **kwargs):
    g.time = datetime.now()
    g.timings = { 'sql': 0.0, 'sqlcount': 0, 'template': 0.0 }
def before_render_template_log(*args, **kwargs):
    g.time_before_render_template = datetime.now()
def template_rendered_log(*args, **kwargs):
    timedelta = datetime.now() - g.time_before_render_template
    g.timings['template'] += timedelta.total_seconds()

appcontext_pushed.connect(appcontext_pushed_log, oj)
before_render_template.connect(before_render_template_log, oj)
template_rendered.connect(template_rendered_log, oj)

@oj.before_request
def before_request_log(*args, **kwargs):
    g.timings['init'] = (datetime.now() - g.time).total_seconds()

@oj.teardown_request
def teardown_request_log(*args, **kwargs):
    g.timings['total'] = (datetime.now() - g.time).total_seconds()
    log_request()
    if 'db' in g:
        g.db.close()
        g.db = None
