__all__ = ("SessionManager", "TempSessionManager")

from uuid import uuid4
from flask import Response, after_this_request, request
from commons.models import User
from web.config import LoginConfig
from web.manager.user import UserManager
from web.utils import RedisConfig, redis_connect


class SessionImpl:
    redis = redis_connect()

    def __init__(self, prefix: str, session_cookie_name: str, timeout: int):
        self.prefix = prefix
        self.session_cookie_name = session_cookie_name
        self.timeout = timeout

    def redis_key(self, session_id: str) -> str:
        return self.prefix + session_id

    def get_session_id(self) -> str | None:
        return request.cookies.get(self.session_cookie_name)

    def get_session_value(self) -> str | None:
        session_id = self.get_session_id()
        if not session_id:
            return None
        return self.redis.get(self.redis_key(session_id))

    def logout(self) -> None:
        session_id = self.get_session_id()
        if session_id:
            self.redis.delete(self.redis_key(session_id))

    def new_session(self, value: str) -> None:
        session_id = str(uuid4())
        self.redis.set(self.redis_key(session_id), value, ex=self.timeout)

        def set_cookie(response: Response):
            response.set_cookie(
                key=self.session_cookie_name,
                value=session_id,
                max_age=self.timeout,
            )
            return response

        after_this_request(set_cookie)


class SessionManager:
    handler = SessionImpl(
        prefix=RedisConfig.prefix + "session:",
        session_cookie_name="acmoj-session",
        timeout=LoginConfig.Login_Life_Time,
    )

    @classmethod
    def current_user(cls) -> User | None:
        user_id = cls.handler.get_session_value()
        if not user_id:
            return None
        return UserManager.get_user(int(user_id))

    @classmethod
    def switch_user(cls, user: User):
        session_id = cls.handler.get_session_id()
        assert session_id is not None
        cls.handler.new_session(str(user.id))

    @classmethod
    def new_session(cls, user: User) -> None:
        cls.handler.new_session(str(user.id))

    @classmethod
    def logout(cls) -> None:
        cls.handler.logout()


class TempSessionManager:
    handler = SessionImpl(
        prefix=RedisConfig.prefix + "temp-session:",
        session_cookie_name="acmoj-temp-session",
        timeout=60 * 5,
    )

    @classmethod
    def current_student_id(cls) -> str | None:
        return cls.handler.get_session_value()

    @classmethod
    def new_session(cls, student_id: str) -> None:
        cls.handler.new_session(student_id)

    @classmethod
    def logout(cls) -> None:
        cls.handler.logout()
