from userManager import UserManager
from flask import request
import redis
import config


class SessionManager:
    def __init__(self):
        self.redis = redis.StrictRedis(host=config.RedisConfig.host, port=config.RedisConfig.port,
                                       db=config.RedisConfig.db)
        return

    def get(self, lid: str) -> str:
        ret = self.redis.get(str(lid))
        if ret == None:
            return ''
        return ret.decode('UTF-8')

    def check_user_status(self) -> bool:  # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        return bool(self.get(lid))

    def new_session(self, username: str, login_id: str):
        self.redis.set(login_id, username, ex=60 * 60 * 24 * 30)  # expire after 30 days
        return

    def get_username(self) -> str:
        lid = request.cookies.get('Login_ID')
        return self.get(lid)

    def get_friendly_name(self) -> str:
        lid = request.cookies.get('Login_ID')
        if not (self.get(lid)):
            return ''
        return UserManager().get_friendly_name(self.get(lid))

    def get_privilege(self) -> int:
        lid = request.cookies.get('Login_ID')
        if not (self.get(lid)):
            return -1  # lowest Privilege for Guests
        return UserManager().get_privilege(self.get(lid))


Login_Manager = SessionManager()
