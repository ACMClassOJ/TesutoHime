from userManager import UserManager
from flask import request
from utils import UnixNano


class SessionManager:
    def __init__(self):
        self.mem = {}
        return

    def Check_User_Status(self) -> bool: # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        return lid in self.mem

    def New_Session(self, Username: str, Login_ID: str):
        self.mem[Login_ID] = Username
        return

    def Get_Username(self) -> str:
        lid = request.cookies.get('Login_ID')
        return self.mem[lid] if lid in self.mem else 'Nobody'

    def Get_FriendlyName(self) -> str:
        lid = request.cookies.get('Login_ID')
        if not (lid in self.mem):
            return 'Nobody'
        return UserManager().Get_Friendly_Name(self.mem[lid])

    def Get_Privilege(self) -> int:
        lid = request.cookies.get('Login_ID')
        if not (lid in self.mem):
            return -1 # lowest Privilege for Guests
        return UserManager().Get_Privilege(self.mem[lid])

Login_Manager = SessionManager()