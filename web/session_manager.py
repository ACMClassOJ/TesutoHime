__all__ = ('SessionManager',)

from typing import Optional

from flask import request

from commons.models import User
from web.user_manager import UserManager
from web.utils import RedisConfig, redis_connect


class SessionManager:
    redis = redis_connect()
    session_cookie_name = 'acmoj-session'
    prefix = RedisConfig.prefix + 'session:'

    @classmethod
    def redis_key(cls, session_id: str) -> str:
        return cls.prefix + session_id

    @classmethod
    def current_user(cls) -> Optional[User]:
        session_id = request.cookies.get(cls.session_cookie_name)
        if session_id is None: return None
        user_id = cls.redis.get(cls.redis_key(session_id))
        if user_id is None: return None
        return UserManager.get_user(int(user_id))

    @classmethod
    def switch_user(cls, user: User):
        session_id = request.cookies.get(cls.session_cookie_name)
        assert session_id is not None
        cls.new_session(user, session_id)

    @classmethod
    def logout(cls) -> None:
        session_id = request.cookies.get(cls.session_cookie_name)
        if session_id is None: return
        cls.redis.delete(cls.redis_key(session_id))

    @classmethod
    def new_session(cls, user: User, session_id: str) -> None:
        cls.redis.set(cls.redis_key(session_id), str(user.id), ex=86400 * 14)
