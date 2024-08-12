from functools import wraps
from http.client import BAD_REQUEST, CREATED, FORBIDDEN, NO_CONTENT, UNAUTHORIZED
from typing import NoReturn, Optional
from typing_extensions import TypeGuard

from flask import Blueprint, abort, g, jsonify, make_response, redirect, request, url_for
from sqlalchemy import select
from werkzeug.exceptions import BadRequest

from commons.models import AccessToken, JudgeRecordV2, Problem, User
from web.const import api_scopes
from web.judge_manager import JudgeManager
from web.oauth_manager import OauthManager
from web.utils import db

api = Blueprint('api', __name__)

def token_is_valid(token: Optional[AccessToken]) -> TypeGuard[AccessToken]:
    return token is not None and g.time < token.expires_at and token.revoked_at is None

def api_get_user() -> Optional[User]:
    g.token = None
    auth = request.authorization
    if auth is None: return None
    if auth.type == 'bearer':
        token = db.scalar(select(AccessToken).where(AccessToken.token == auth.token))
        if not token_is_valid(token): return None
        g.token = token
        return token.user
    return None

def abort_json(code: int, message: str) -> NoReturn:
    resp = jsonify({ 'error': code, 'message': message })
    resp.status_code = code
    abort(resp)

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


@api.errorhandler(KeyError)
def fieldhandler(exc: KeyError):
    if isinstance(exc, BadRequest):
        resp = jsonify({ 'error': BAD_REQUEST, 'message': f'missing {exc.args[0]}'})
        resp.status_code = BAD_REQUEST
        return resp
    from web.web import errorhandler
    return errorhandler(exc)


@api.route('/')
def index():
    return redirect(url_for('web.help', page='api'))


@api.route('/oauth/token', methods=['POST'])
def oauth_token():
    client_id = request.form['client_id']
    client_secret = request.form['client_secret']
    redirect_uri = request.form.get('redirect_uri')
    code = request.form['code']

    app = OauthManager.get_app(client_id)
    if app is None or app.client_secret != client_secret:
        abort_json(UNAUTHORIZED, 'invalid client_id or client_secret')
    res = OauthManager.use_code(app, redirect_uri, code)
    if res is None:
        abort_json(UNAUTHORIZED, 'invalid code')
    user_id, scopes = res
    token = OauthManager.create_access_token(app, user_id, scopes)
    return jsonify({
        'access_token': token.token,
        'scopes': scopes,
        'expires_at': token.expires_at.isoformat(),
    })

@api.route('/user')
@scope('user:read')
def user():
    return jsonify({
        'username': g.user.username,
        'friendly_name': g.user.friendly_name,
        'student_id': g.user.student_id,
    })

@api.route('/problem/<problem:problem>/submit', methods=['POST'])
@scope('submission:create')
def problem_submit(problem: Problem):
    public = request.form.get('public', 'false') == 'true'
    lang = request.form['lang']
    code = request.form['code']

    if not JudgeManager.can_create(problem, public, lang, code):
        abort_json(BAD_REQUEST, 'unable to create submission')
    submission = JudgeManager.create_submission(public=public, language=lang, user=g.user, problem_id=problem.id, code=code)
    resp = jsonify({ 'id': submission.id })
    resp.status_code = CREATED
    resp.headers.set('Location', url_for('.submission', submission=submission))
    return resp

@api.route('/submission/<submission:submission>')
@scope('submission:read')
def submission(submission: JudgeRecordV2):
    details = JudgeManager.get_details(submission)
    res = {
        'details': details,
        'status': submission.status.name,
        'should_show_score': JudgeManager.should_show_score(submission),
        'code_url': JudgeManager.sign_code_url(submission),
        'friendly_name': submission.user.friendly_name,
    }
    keys = ['id', 'public', 'language', 'problem_id', 'score', 'message', 'time_msecs', 'memory_bytes']
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
