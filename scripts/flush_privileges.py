from web.manager.user import UserManager
from scripts.db.env import *

username = input('username: ')
user = db.scalar(sa.select(User).where(User.username_lower == sa.func.lower(username)))
UserManager.flush_privileges(user)
