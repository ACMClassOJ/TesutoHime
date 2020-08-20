from userManager import UserManager
from flask import request
from utils import UnixNano
from config import Login_Config

class SessionManager:
    def __init__(self):
        self.mem = {}
        self.startTime = {}
        return

    def Check_User_Status(self) -> bool: # to check whether current user has logged in properly
        lid = request.cookies.get('Login_ID')
        self.Check_Pool()
        return lid in self.mem

    def New_Session(self, Username: str, Login_ID: str):
        self.mem[Login_ID] = Username
        self.startTime[Login_ID] = UnixNano()
        return

    def Check_Pool(self):
        to_Delete = []
        nowTime = UnixNano()
        for id, time in self.startTime:
            if time + Login_Config.Login_Life_Time > nowTime:
                to_Delete.append(id)
        for id in to_Delete:
            del self.mem[id]
            del self.startTime[id]
        return

    def Get_Username(self) -> str:
        lid = request.cookies.get('Login_ID')
        self.Check_Pool()
        return self.mem[lid] if lid in self.mem else 'Nobody'

    def Get_FriendlyName(self) -> str:
        lid = request.cookies.get('Login_ID')
        self.Check_Pool()
        if not (lid in self.mem):
            return 'Nobody'
        return UserManager().Get_Friendly_Name(self.mem['Login_ID'])

    def Get_Privilege(self) -> int:
        lid = request.cookies.get('Login_ID')
        self.Check_Pool()
        if not (lid in self.mem):
            return 0 # lowest Privilege for Guests
        return UserManager().Get_Privilege(self.mem['Login_ID'])

Login_Manager = SessionManager()