from base64 import b64encode
from http.client import BAD_REQUEST
from secrets import token_bytes

from flask import Blueprint, Response, abort, g, request
from markupsafe import Markup

csrf_cookie_name = '__Host-acmoj-csrf'
csrf_input_name = '_acmoj-csrf'

def generate_token() -> str:
    return b64encode(token_bytes(12)).decode()

def csrf_input() -> Markup:
    token = g.csrf_token
    if token is None:
        token = generate_token()
        g.csrf_token = token
        g.should_set_csrf = True
    html = f'<input name="{csrf_input_name}" type="hidden" value="{token}">'
    return Markup(html)

def check_csrf():
    g.csrf_token = request.cookies.get(csrf_cookie_name)
    g.csrf = csrf_input
    if request.method != 'POST':
        return
    if request.headers.get('X-Acmoj-Is-Csrf', 'yes') != 'yes':
        return
    if request.form.get(csrf_input_name) != g.csrf_token:
        abort(BAD_REQUEST, 'CSRF 检查无法通过，请在浏览器中启用 Cookies。')

def set_csrf_cookies(resp: Response) -> Response:
    if 'should_set_csrf' in g:
        resp.set_cookie(csrf_cookie_name, g.csrf_token, secure=True, samesite='Lax', httponly=True)
    return resp

def setup_csrf(app: Blueprint):
    app.before_request(check_csrf)
    app.after_request(set_csrf_cookies)
