from userManager import UserManager
from flask import request


class SessionManager:
    def __init__(self):
        self.mem = {}
        return

    def check_user_status(self) -> bool:  # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        return lid in self.mem

    def new_session(self, username: str, login_id: str):
        self.mem[login_id] = username
        return

    def get_username(self) -> str:
        lid = request.cookies.get('Login_ID')
        return self.mem[lid] if lid in self.mem else ''

    def get_friendly_name(self) -> str:
        lid = request.cookies.get('Login_ID')
        if not (lid in self.mem):
            return ''
        return UserManager().get_friendly_name(self.mem[lid])

    def get_privilege(self) -> int:
        lid = request.cookies.get('Login_ID')
        if not (lid in self.mem):
            return -1  # lowest Privilege for Guests
        return UserManager().get_privilege(self.mem[lid])


Login_Manager = SessionManager()
