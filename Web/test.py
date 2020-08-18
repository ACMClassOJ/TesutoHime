from userManager import UserManager

a = UserManager()

# a.addUser('u1', '123456', 'user1', '123', '3')
# a.ModifyUser('u1', '531', '', '' , '')
# a.ModifyUser('u1', '', 'u1', '' , '')
# a.ModifyUser('u1', '', '', '321' , '')
# a.ModifyUser('u1', '', '', '' , '2')
# a.ModifyUser('u1', '123456', 'user1', '123', '3')
print(a.CheckLogin('u1', '123'))
print(a.CheckLogin('u1', '321'))
print(a.CheckLogin('u2', '321'))
print(a.GetFriendlyName('u1'))
print(a.GetStudentID('u1'))
print(a.GetPrivilege('u1'))