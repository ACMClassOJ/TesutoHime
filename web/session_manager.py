__all__ = ('SessionManager',)

from typing import Optional

from flask import request

from commons.models import User
from web.user_manager import UserManager
from web.utils import RedisConfig, redis_connect


class SessionManager:
    redis = redis_connect()
    prefix = RedisConfig.prefix + 'session_'

    @classmethod
    def current_user(cls) -> Optional[User]:
        session_id = request.cookies.get('Login_ID')
        user_id = cls.redis.get(cls.prefix + str(session_id))
        if user_id is None: return None
        return UserManager.get_user(int(user_id))

    @classmethod
    def logout(cls) -> None:
        session_id = request.cookies.get('Login_ID')
        cls.redis.delete(cls.prefix + str(session_id))

    @classmethod
    def new_session(cls, user: User, login_id: str) -> None:
        cls.redis.set(cls.prefix + login_id, str(user.id), ex = 86400 * 14)
