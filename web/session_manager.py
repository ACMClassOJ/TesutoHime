__all__ = ('SessionManager',)

from flask import request

from web.user_manager import UserManager
from web.utils import RedisConfig, redis_connect


class SessionManager:
    redis = redis_connect()
    prefix = RedisConfig.prefix + 'session_'

    def check_user_status() -> bool:  # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        return rst != None

    def new_session(username: str, login_id: str):
        SessionManager.redis.set(SessionManager.prefix + login_id, username, ex = 86400 * 14)
        return

    def get_username() -> str:
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        return rst if rst != None else ''

    def get_friendly_name() -> str:
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        return UserManager.get_friendly_name(rst) if rst != None else ''

    def get_privilege() -> int:
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        return UserManager.get_privilege(rst) if rst != None else -1
