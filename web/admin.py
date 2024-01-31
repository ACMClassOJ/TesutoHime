from datetime import datetime
from functools import wraps
from http.client import (BAD_REQUEST, FORBIDDEN, NO_CONTENT,
                         REQUEST_ENTITY_TOO_LARGE, SEE_OTHER)
from typing import List
from urllib.parse import urljoin
from uuid import uuid4

import requests
from flask import (Blueprint, abort, g, make_response, redirect,
                   render_template, request)

from commons.models import Course, Group, Problem
from web.config import S3Config, SchedulerConfig
from web.const import Privilege, ReturnCode, String
from web.contest_manager import ContestManager
from web.course_manager import CourseManager
from web.judge_manager import JudgeManager, NotFoundException
from web.problem_manager import ProblemManager
from web.realname_manager import RealnameManager
from web.user_manager import UserManager
from web.utils import db, generate_s3_public_url

admin = Blueprint('admin', __name__, static_folder='static')

def require_admin(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not g.is_admin:
            abort(FORBIDDEN)
        return func(*args, **kwargs)
    return wrapped

@admin.route('/')
@require_admin
def index():
    return render_template('admin.html')


# docs

@admin.route('/admin-doc')
def admin_doc():
    return render_template('admin_doc.html')

@admin.route('/problem-format-doc')
def problem_format_doc():
    return render_template('problem_format_doc.html')

@admin.route('/data-doc')
def data_doc():
    return render_template('data_doc.html')

@admin.route('/package-sample')
def package_sample():
    return render_template('package_sample.html')


# user

@admin.route('/user', methods=['post'])
def user_manager():
    if g.user is None or g.user.privilege < Privilege.SUPER:
        abort(FORBIDDEN)
    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    # err = _validate_user_data(form)
    # if err is not None:
    #     return err
    try:
        op = int(form[String.TYPE])
        if op == 0:
            UserManager.add_user(form[String.USERNAME], form[String.STUDENT_ID], form[String.FRIENDLY_NAME],
                                  form[String.PASSWORD], form[String.PRIVILEGE])
            return ReturnCode.SUC_ADD_USER
        elif op == 1:
            UserManager.modify_user(form[String.USERNAME], form.get(String.STUDENT_ID, None),
                                     form.get(String.FRIENDLY_NAME, None), form.get(String.PASSWORD, None),
                                     form.get(String.PRIVILEGE, None))
            return ReturnCode.SUC_MOD_USER
        else:
            return ReturnCode.ERR_BAD_DATA
    except KeyError:
        return ReturnCode.ERR_BAD_DATA
    except TypeError:
        return ReturnCode.ERR_BAD_DATA


# course

@admin.route('/course/<course:course>/problem', methods=['post'])
def problem_create(course: Course):
    if not g.can_write:
        abort(FORBIDDEN)
    problem_id = ProblemManager.add_problem(course.id)
    return redirect(f'/OnlineJudge/problem/{problem_id}/admin', SEE_OTHER)

@admin.route('/course/<course:course>/realname', methods=['post'])
def add_realname(course: Course):
    if not g.can_write:
        abort(FORBIDDEN)

    data = [line.split(',') for line in request.form['data'].strip().splitlines()]
    for line in data:
        groups: List[Group] = []
        if len(line) > 2:
            group_names = [x.strip() for x in line[2].split('|')]
            for group_name in group_names:
                group = CourseManager.get_group_by_name(course, group_name)
                if group is None:
                    db.rollback()
                    return { 'e': 400, 'msg': f'分组 {repr(group_name)} 不存在' }
                groups.append(group)
        RealnameManager.add_student(line[0], line[1], course, groups)

    return ReturnCode.SUC_ADD_REALNAME


# problem

def reads_problem(func):
    @wraps(func)
    def wrapped(problem, *args, **kwargs):
        if not ProblemManager.can_read(problem):
            abort(FORBIDDEN)
        return func(problem, *args, **kwargs)
    return wrapped

def writes_problem(func):
    @wraps(func)
    def wrapped(problem, *args, **kwargs):
        if not ProblemManager.can_write(problem):
            abort(FORBIDDEN)
        return func(problem, *args, **kwargs)
    return wrapped

@admin.route('/problem/<problem:problem>', methods=['put'])
@writes_problem
def problem_info(problem: Problem):
    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    try:
        problem.title = form['title']
        problem.release_time = datetime.fromisoformat(form['time'])
        problem.problem_type = form['problem_type']
        return make_response('', NO_CONTENT)
    except KeyError:
        abort(BAD_REQUEST)
    except ValueError:
        abort(BAD_REQUEST)

@admin.route('/problem/<problem:problem>/description', methods=['put'])
@writes_problem
def problem_description(problem: Problem):
    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    for row in 'description', 'input', 'output', 'example_input', 'example_output', 'data_range':
        data = form.get(row, None)
        if data == 'None' or data == '':
            data = None
        setattr(problem, row, data)
    return make_response('', NO_CONTENT)

@admin.route('/problem/<problem:problem>/limit', methods=['put'])
@writes_problem
def problem_limit(problem: Problem):
    problem.limits = request.json
    return make_response('', NO_CONTENT)

@admin.route('/problem/<problem:problem>/upload-url')
@writes_problem
def data_upload(problem: Problem):
    return generate_s3_public_url('put_object', {
        'Bucket': S3Config.Buckets.problems,
        'Key': f'{problem.id}.zip',
    }, ExpiresIn=3600)


@admin.route('/problem/<problem:problem>/update-plan', methods=['POST'])
@writes_problem
def data_update(problem: Problem):
    url = urljoin(SchedulerConfig.base_url, f'problem/{problem.id}/update')
    res = requests.post(url).json()
    if res['result'] == 'ok':
        problem.languages_accepted = res['languages']
        return 'ok'
    elif res['result'] == 'invalid problem':
        return f'Invalid problem: {res["error"]}'
    elif res['result'] == 'system error':
        return f'System error: {res["error"]}'
    return 'Bad result from scheduler'

@admin.route('/problem/<problem:problem>/data-zip')
@reads_problem
def data_download(problem: Problem):
    key = f'{problem.id}.zip'
    url = generate_s3_public_url('get_object', {
        'Bucket': S3Config.Buckets.problems,
        'Key': key,
    }, ExpiresIn=3600)
    return redirect(url, SEE_OTHER)

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

@admin.route('/rejudge', methods=['POST'])
def rejudge():
    return problem_admin_api(JudgeManager.rejudge, ReturnCode.SUC_REJUDGE)

@admin.route('/mark-void', methods=['POST'])
def mark_void():
    return problem_admin_api(JudgeManager.mark_void, ReturnCode.SUC_DISABLE_JUDGE)

@admin.route('/abort-judge', methods=['POST'])
def abort_judge():
    return problem_admin_api(JudgeManager.abort_judge, ReturnCode.SUC_ABORT_JUDGE)


# contest

@admin.route('/contest', methods=['post'])
@require_admin
def contest_manager():
    form = request.json
    if form is None:
        abort(BAD_REQUEST)
    try:
        op = int(form[String.TYPE])
        if op == 0:
            ContestManager.create_contest(int(form[String.CONTEST_ID]), form[String.CONTEST_NAME],
                                          datetime.fromisoformat(form[String.START_TIME]),
                                          datetime.fromisoformat(form[String.END_TIME]),
                                          int(form[String.CONTEST_TYPE]),
                                          form[String.CONTEST_RANKED],
                                          form[String.CONTEST_RANK_PENALTY],
                                          form[String.CONTEST_RANK_PARTIAL_SCORE])
            return ReturnCode.SUC_ADD_CONTEST
        elif op == 1:
            ContestManager.modify_contest(int(form[String.CONTEST_ID]), form.get(String.CONTEST_NAME, None),
                                          datetime.fromisoformat(form[String.START_TIME]),
                                          datetime.fromisoformat(form[String.END_TIME]),
                                          int(form.get(String.CONTEST_TYPE, None)),
                                          form[String.CONTEST_RANKED],
                                          form[String.CONTEST_RANK_PENALTY],
                                          form[String.CONTEST_RANK_PARTIAL_SCORE])
            return ReturnCode.SUC_MOD_CONTEST
        elif op == 2:
            ContestManager.delete_contest(int(form[String.CONTEST_ID]))
            return ReturnCode.SUC_DEL_CONTEST
        elif op == 3:
            for problemId in form[String.CONTEST_PROBLEM_IDS]:
                ContestManager.add_problem_to_contest(int(form[String.CONTEST_ID]), int(problemId))
            return ReturnCode.SUC_ADD_PROBLEMS_TO_CONTEST
        elif op == 4:
            for problemId in form[String.CONTEST_PROBLEM_IDS]:
                ContestManager.delete_problem_from_contest(int(form[String.CONTEST_ID]), int(problemId))
            return ReturnCode.SUC_DEL_PROBLEMS_FROM_CONTEST
        elif op == 5:
            for username in form[String.CONTEST_USERNAMES]:
                user = UserManager.get_user(username)
                if user is not None:
                    ContestManager.add_player_to_contest(int(form[String.CONTEST_ID]), user)
                else:
                    return ReturnCode.ERR_ADDS_USER_TO_CONTEST
            return ReturnCode.SUC_ADD_USERS_TO_CONTEST
        elif op == 6:
            contest_id = int(form[String.CONTEST_ID])
            contest = ContestManager.get_contest(contest_id)
            if contest is None:
                return ReturnCode.ERR_DEL_USERS_FROM_CONTEST
            for username in form[String.CONTEST_USERNAMES]:
                user = UserManager.get_user(username)
                if user is not None:
                    contest.players.remove(user)
            return ReturnCode.SUC_DEL_USERS_FROM_CONTEST
        else:
            return ReturnCode.ERR_BAD_DATA
    except KeyError:
        return ReturnCode.ERR_BAD_DATA
    except TypeError:
        return ReturnCode.ERR_BAD_DATA


# misc

max_pic_size = 10485760

@admin.route('/pic-url', methods=['POST'])
@require_admin
def pic_upload():
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
