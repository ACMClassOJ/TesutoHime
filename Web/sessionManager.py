from userManager import UserManager
from flask import request
from utils import *


class SessionManager:
    def __init__(self):
        self.redis = redis_connect()
        self.prefix = RedisConfig.prefix + "session_"
        return

    def check_user_status(self) -> bool:  # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        rst = self.redis.get(self.prefix + str(lid))
        return rst != None

    def new_session(self, username: str, login_id: str):
        self.redis.set(self.prefix + login_id, username, ex = 86400 * 14)
        return

    def get_username(self) -> str:
        lid = request.cookies.get('Login_ID')
        rst = self.redis.get(self.prefix + str(lid))
        return rst if rst != None else ''

    def get_friendly_name(self) -> str:
        lid = request.cookies.get('Login_ID')
        rst = self.redis.get(self.prefix + str(lid))
        return UserManager().get_friendly_name(rst) if rst != None else ''

    def get_privilege(self) -> int:
        lid = request.cookies.get('Login_ID')
        rst = self.redis.get(self.prefix + str(lid))
        return UserManager().get_privilege(rst) if rst != None else -1


Login_Manager = SessionManager()
