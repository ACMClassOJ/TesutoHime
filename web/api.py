from functools import wraps
from http.client import (BAD_REQUEST, CREATED, FORBIDDEN,
                         INTERNAL_SERVER_ERROR, NO_CONTENT, UNAUTHORIZED)
from typing import NoReturn, Optional
from urllib.parse import parse_qsl, urlencode

from flask import (Blueprint, abort, g, jsonify, make_response, redirect,
                   request, url_for)
from sqlalchemy import select
from typing_extensions import TypeGuard
from werkzeug.exceptions import BadRequest, HTTPException

from commons.models import (AccessToken, Contest, Course, CourseTag,
                            JudgeRecordV2, Problem, Term, User)
from web.config import JudgeConfig, WebConfig
from web.const import api_scopes
from web.contest_manager import ContestManager
from web.course_manager import CourseManager
from web.judge_manager import JudgeManager
from web.oauth_manager import OauthManager
from web.problem_manager import ProblemManager
from web.utils import abort_json, db, paged_search_cursor, require_logged_in

api = Blueprint('api', __name__)

# helper functions

def token_is_valid(token: Optional[AccessToken]) -> TypeGuard[AccessToken]:
    return token is not None and g.time < token.expires_at and token.revoked_at is None

def api_get_user() -> Optional[User]:
    g.token = None
    auth_header = request.headers.get('Authorization')
    if auth_header is None: return None
    
    scheme, _, token = auth_header.partition(' ')
    scheme = scheme.lower()
    token = token.strip()

    if scheme == 'bearer':
        token = db.scalar(select(AccessToken).where(AccessToken.token == token))
        if not token_is_valid(token): return None
        g.token = token
        return token.user
    return None

'''
Ensures the current access token has the given scope. You should define
the scope in const.py first.
'''
def scope(scope: str):
    if scope not in api_scopes:
        raise ValueError(f'Invalid scope {scope}')
    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if g.token is None or scope not in g.token.scopes:
                abort_json(UNAUTHORIZED, f'this api call needs scope {scope}')
            return func(*args, **kwargs)
        return wrapped
    return wrapper

def next_url(cursor):
    if cursor is None: return None
    parsed_qs = parse_qsl(request.query_string.decode())
    parsed_qs = [(k, v) for k, v in parsed_qs if k != 'cursor']
    parsed_qs += [('cursor', cursor)]
    qs = urlencode(parsed_qs)
    return request.path + '?' + qs


@api.errorhandler(KeyError)
def fieldhandler(exc: KeyError):
    if isinstance(exc, BadRequest):
        resp = jsonify({ 'error': BAD_REQUEST, 'message': f'missing {exc.args[0]}'})
        resp.status_code = BAD_REQUEST
        return resp
    from web.web import errorhandler
    return errorhandler(exc)

@api.errorhandler(HTTPException)
def httphandler(exc: HTTPException):
    resp = jsonify({ 'error': exc.code, 'message': exc.description })
    resp.status_code = exc.code if exc.code is not None else INTERNAL_SERVER_ERROR
    return resp


# serializers

def contest_type_string(type: int) -> str:
    return ['contest', 'homework', 'exam'][type]


def problem_brief(problem: Problem):
    can_show = ProblemManager.can_show(problem)
    return {
        'id': problem.id,
        'title': problem.title if can_show else None,
        'url': url_for('.problem', problem=problem) if can_show else None,
        'submit_url': url_for('.problem_submit', problem=problem) if can_show else None,
        'html_url': url_for('web.problem', problem=problem) if can_show else None,
    }

def submission_brief(submission: JudgeRecordV2):
    can_show = JudgeManager.can_show(submission)
    return {
        'id': submission.id,
        'friendly_name': submission.user.friendly_name,
        'problem': problem_brief(submission.problem),
        'status': submission.status.name,
        'language': submission.language,
        'created_at': submission.created_at.isoformat(),
        'url': url_for('.submission', submission=submission) if can_show else None,
        'html_url': url_for('web.submission', submission=submission) if can_show else None,
    }

def problemset_tojson(contest: Contest):
    problems = []
    if ContestManager.problems_visible(contest):
        problems = [problem_brief(x) for x in contest.problems]
    can_join = ContestManager.can_join(contest)
    return {
        'id': contest.id,
        'course': course_tojson(contest.course),
        'name': contest.name,
        'description': contest.description,
        'allowed_languages': contest.allowed_languages,
        'start_time': contest.start_time.isoformat(),
        'end_time': contest.end_time.isoformat(),
        'type': contest_type_string(contest.type),
        'problems': problems,
        'url': url_for('.problemset', contest=contest),
        'join_url': url_for('.problemset_join', contest=contest) if can_join else None,
        'quit_url': url_for('.problemset_quit', contest=contest) if can_join else None,
        'html_url': url_for('web.problemset', contest=contest),
    }

def course_tag_tojson(tag: Optional[CourseTag]):
    if tag is None: return None
    return {
        'id': tag.id,
        'name': tag.name,
    }

def term_tojson(term: Optional[Term]):
    if term is None: return None
    return {
        'id': term.id,
        'name': term.name,
        'start_time': term.start_time.isoformat(),
        'end_time': term.end_time.isoformat(),
    }

def course_tojson(course: Course):
    can_join = CourseManager.can_join(course)
    return {
        'id': course.id,
        'name': course.name,
        'description': course.description,
        'tag': course_tag_tojson(course.tag),
        'term': term_tojson(course.term),
        'url': url_for('.course', course=course),
        'join_url': url_for('.course_join', course=course) if can_join else None,
        'quit_url': url_for('.course_quit', course=course) if can_join else None,
        'html_url': url_for('web.course', course=course),
    }


# routes

@api.route('/')
def index():
    return redirect(url_for('web.help', page='api'))


# routes: user

def abort_oauth(error: str, description: str) -> NoReturn:
    res = jsonify({ 'error': error, 'error_description': description })
    res.status_code = BAD_REQUEST
    abort(res)

@api.route('/oauth/token', methods=['POST'])
def oauth_token():
    try:
        grant_type = request.form['grant_type']
        client_id = request.form['client_id']
        client_secret = request.form['client_secret']
        redirect_uri = request.form.get('redirect_uri')
        code = request.form['code']
    except KeyError as e:
        abort_oauth('invalid request', f'missing {e.args[0]}')

    if grant_type != 'authorization_code':
        abort_oauth('unsupported_grant_type', 'invalid grant_type')
    app = OauthManager.get_app(client_id)
    if app is None or app.client_secret != client_secret:
        abort_oauth('invalid_client', 'invalid client_id or client_secret')
    res = OauthManager.use_code(app, redirect_uri, code)
    if res is None:
        abort_oauth('invalid_grant', 'invalid code')
    user_id, scopes = res
    try:
        token = OauthManager.create_access_token(app, user_id, scopes)
    except ValueError:
        abort_oauth('invalid_scope', 'invalid scope')
    resp = jsonify({
        'access_token': token.token,
        'token_type': 'bearer',
        'expires_in': (token.expires_at - g.time).total_seconds(),
        'scope': ' '.join(scopes),
    })
    resp.headers['Cache-Control'] = 'no-store'
    resp.headers['Pragma'] = 'no-cache'
    return resp

@api.route('/user/profile')
@scope('user:profile')
def user_profile():
    return jsonify({
        'username': g.user.username,
        'friendly_name': g.user.friendly_name,
        'student_id': g.user.student_id,
    })

@api.route('/user/courses')
@scope('course:read')
def user_courses():
    return jsonify({
        'courses': [course_tojson(x) for x in g.user.courses],
    })

@api.route('/user/problemsets')
@scope('problemset:read')
def user_problemsets():
    contests = ContestManager.get_contests_for_user(g.user, include_admin=True, include_unofficial=True)
    return jsonify({
        'problemsets': [problemset_tojson(x) for x in contests],
    })


# routes: problem

@api.route('/problem/')
@scope('problem:read')
def problem_list():
    res = paged_search_cursor(WebConfig.Problems_Each_Page, ProblemManager.ProblemSearch)
    problems = [problem_brief(p) for p in res.entities]
    return jsonify({
        'problems': problems,
        'next': next_url(res.cursor),
    })

@api.route('/problem/<problem:problem>')
@scope('problem:read')
def problem(problem: Problem):
    res = {}
    keys = ['id', 'title', 'description', 'input', 'output', 'example_input', 'example_output', 'data_range', 'languages_accepted', 'allow_public_submissions']
    for key in keys:
        res[key] = getattr(problem, key)
    return jsonify(res)


# routes: submission

@api.route('/problem/<problem:problem>/submit', methods=['POST'])
@scope('submission:create')
def problem_submit(problem: Problem):
    public = request.form.get('public', 'false') == 'true'
    language = request.form['language']
    code = request.form['code']

    if not JudgeManager.can_create(problem, public, language, code):
        abort_json(BAD_REQUEST, 'unable to create submission')
    submission = JudgeManager.create_submission(public=public, language=language, user=g.user, problem_id=problem.id, code=code)
    resp = jsonify({ 'id': submission.id })
    resp.status_code = CREATED
    resp.headers.set('Location', url_for('.submission', submission=submission))
    return resp

@api.route('/submission/')
@scope('submission:read')
def submission_list():
    res = paged_search_cursor(JudgeConfig.Judge_Each_Page, JudgeManager.SubmissionSearch)
    submissions = [submission_brief(s) for s in res.entities]
    return jsonify({
        'submissions': submissions,
        'next': next_url(res.cursor),
    })

@api.route('/submission/<submission:submission>')
@scope('submission:read')
def submission(submission: JudgeRecordV2):
    details = JudgeManager.get_details(submission)
    res = {
        'problem': problem_brief(submission.problem),
        'details': details,
        'status': submission.status.name,
        'should_show_score': JudgeManager.should_show_score(submission),
        'friendly_name': submission.user.friendly_name,
        'created_at': submission.created_at.isoformat(),
        'code_url': JudgeManager.sign_code_url(submission),
        'abort_url': url_for('.submission_abort', submission=submission) if g.can_abort else None,
        'html_url': url_for('web.submission', submission=submission),
    }
    keys = ['id', 'public', 'language', 'score', 'message', 'time_msecs', 'memory_bytes']
    for key in keys:
        res[key] = getattr(submission, key)
    return jsonify(res)

@api.route('/submission/<submission:submission>/abort', methods=['POST'])
@scope('submission:write')
def submission_abort(submission: JudgeRecordV2):
    if not g.can_abort:
        abort_json(FORBIDDEN, 'cannot abort')
    JudgeManager.abort_judge(submission)
    return make_response('', NO_CONTENT)


# routes: problemset

@api.route('/problemset/<contest:contest>')
@scope('problemset:read')
def problemset(contest: Contest):
    return jsonify(problemset_tojson(contest))

@api.route('/problemset/<contest:contest>/join', methods=['POST'])
@scope('problemset:membership')
def problemset_join(contest: Contest):
    ContestManager.join(contest)
    return make_response('', NO_CONTENT)

@api.route('/problemset/<contest:contest>/quit', methods=['POST'])
@scope('problemset:membership')
def problemset_quit(contest: Contest):
    ContestManager.quit(contest)
    return make_response('', NO_CONTENT)


# routes: course

@api.route('/course/')
@require_logged_in
def course_list():
    res = paged_search_cursor(WebConfig.Courses_Each_Page, CourseManager.CourseSearch)
    courses = [course_tojson(s) for s in res.entities]
    return jsonify({
        'courses': courses,
        'next': next_url(res.cursor),
    })

@api.route('/course/<course:course>')
def course(course: Course):
    return jsonify(course_tojson(course))

@api.route('/course/<course:course>/join', methods=['POST'])
@scope('course:membership')
def course_join(course: Course):
    CourseManager.join(course)
    return make_response('', NO_CONTENT)

@api.route('/course/<course:course>/quit', methods=['POST'])
@scope('course:membership')
def course_quit(course: Course):
    CourseManager.quit(course)
    return make_response('', NO_CONTENT)

@api.route('/course/<course:course>/problemsets')
def course_problemset_list(course: Course):
    return {
        'problemsets': [problemset_tojson(c) for c in course.contests],
    }
