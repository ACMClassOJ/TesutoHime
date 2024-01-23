__all__ = ('SessionManager',)

from flask import request

from web.user_manager import UserManager
from web.utils import RedisConfig, redis_connect


class SessionManager:
    redis = redis_connect()
    prefix = RedisConfig.prefix + 'session_'

    @staticmethod
    def check_user_status() -> bool:  # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        return rst is not None

    @staticmethod
    def new_session(username: str, login_id: str):
        SessionManager.redis.set(SessionManager.prefix + login_id, username, ex = 86400 * 14)
        return

    @staticmethod
    def get_username() -> str:
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        return rst if rst is not None else ''

    @staticmethod
    def get_friendly_name() -> str:
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        if rst is None: return ''
        friendly_name = UserManager.get_friendly_name(rst)
        return friendly_name if friendly_name is not None else ''

    @staticmethod
    def get_privilege() -> int:
        lid = request.cookies.get('Login_ID')
        rst = SessionManager.redis.get(SessionManager.prefix + str(lid))
        if rst is None: return -1
        priv = UserManager.get_privilege(rst)
        return priv if priv is not None else -1
