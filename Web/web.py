from flask import Flask, request, render_template, redirect
from uuid import uuid4
import re
from sessionManager import Login_Manager
from userManager import User_Manager
from problemManager import Problem_Manager
from discussManager import Discuss_Manager
from judgeManager import Judge_Manager
from contestManager import Conetst_Manager
from config import LoginConfig, WebConfig, JudgeConfig
from utils import *

web = Flask('WEB')

@web.route('/')
def index():
    return render_template('index.html', Friendly_Username = Login_Manager.Get_FriendlyName())

@web.route('/login', methods=['GET', 'POST'])
def Login():
    if request.method == 'GET':
        next = request.args.get('next')
        next = '/' if next == None else next
        if Login_Manager.Check_User_Status():
            return render_template('login.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Logged_In = True, Next = next) # display 'Plsease Logout First'
        return render_template('login.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Logged_In = False, Next = next)
    Username = request.form.get('username')
    Password = request.form.get('password')
    Next = request.form.get('next') # return this argument to ME
    if not User_Manager.Check_Login(Username, Password): # no need to avoid sql injection
        return render_template('login_failure.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Next = next, Inputed_Username = Username, Inputed_Password = Password) # implement it with js.
    lid = str(uuid4())
    Login_Manager.New_Session(Username, lid)
    ret = redirect(Next)
    ret.set_cookie(key = 'Login_ID', value = lid, max_age = LoginConfig.Login_Life_Time)
    return ret

def Validate(Username: str, Password: str, Friendly_Name: str, Student_ID: str) -> bool:
    Username_Reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    Password_Reg = '([a-zA-Z0-9_\!\@\#\$\%\^&\*\(\)]{6,30})$'
    Friendly_Name_Reg = '([a-zA-Z0-9_]{1,60})$'
    Student_ID_Reg = '([0-9]{12})$'
    if re.match(Username_Reg, Username) == None:
        return False
    if re.match(Password_Reg, Password) == None:
        return False
    if re.match(Friendly_Name_Reg, Friendly_Name) == None:
        return False
    if re.match(Student_ID_Reg, Student_ID) == None:
        return False
    return User_Manager.Validate_Username(Username)

@web.route('/register', methods=['GET', 'POST'])
def Register():
    if request.method == 'GET':
        if Login_Manager.Check_User_Status():
            return render_template('register.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Logged_In = True, Next = next) # display 'Plsease Logout First'
        return render_template('register.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Logged_In = False, Next = next)
    Username = request.form.get('username')
    Password = request.form.get('password')
    Friendly_Name = request.form.get('friendly_name')
    Student_ID = request.form.get('student_id')
    if not Validate(Username, Password, Friendly_Name, Student_ID):
        return render_template('register_failure.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Inputed_Username = Username, Inputed_Password = Password, Inputed_Friendly_Name = Friendly_Name, Inputed_Student_ID = Student_ID)
    User_Manager.Add_User(Username, Student_ID, Friendly_Name, Password, '0')
    return render_template('register_complete.html', Friendly_Username = Login_Manager.Get_FriendlyName())

@web.route('/problems')
def Problem_List():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Page = request.args.get('page')
    Page = int(Page) if Page != None else 1
    max_Page = int((Problem_Manager.Get_Max_ID() - 999 + WebConfig.Problems_Each_Page - 1) / WebConfig.Problems_Each_Page)
    Page = max(min(max_Page, Page), 1)
    startID = (Page - 1) * WebConfig.Problems_Each_Page + 1 + 999
    endID = Page * WebConfig.Problems_Each_Page + 999
    Problems = Problem_Manager.Problem_In_Range(startID, endID, UnixNano())
    return render_template('problem_list.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Problems = Problems, Pages = Gen_Page(Page, max_Page))

@web.route('/problem')
def Problem_Detail():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    id = request.args.get('problem_id')
    if id == None:
        return redirect('/') # No argument fed
    Detail = Problem_Manager.Get_Problem(id)
    In_Contest = Problem_Manager.In_Contest(id) and Login_Manager.Get_Privilege() <= 0
    return render_template('problem_details.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Detial = Detail, In_Contest = In_Contest)

@web.route('/submit', methods=['GET', 'POST'])
def Submit_Problem():
    if request.method == 'GET':
        if not Login_Manager.Check_User_Status():
            return redirect('login?next=' + request.url)
        Problem_ID = int(request.args.get('problem_id'))
        Title = Problem_Manager.Get_Title(Problem_ID)
        Username = Login_Manager.Get_Username()
        return render_template('problem_submit.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Problem_ID = Problem_ID, Title = Title)
    else:
        if not Login_Manager.Check_User_Status():
            return redirect('login')
        Problem_ID = int(request.form.get('problem_id'))
        Username = Login_Manager.Get_Username()
        Lang = 0 if str(request.form.get('lang')) == 'cpp' else 1
        Code = request.form.get('code')
        print("At TODO")
        # todo: start Judge & Judge_Server Scheduler
        return redirect('/status')

@web.route('/rank')
def Problem_Rank(): # Todo: Problem Rank
    return 'Todo'

@web.route('/discuss', methods=['GET', 'POST'])
def Discuss():
    if request.method == 'GET':
        if not Login_Manager.Check_User_Status():
            return redirect('login?next=' + request.url)
        Problem_ID = int(request.args.get('problem_id'))
        if Problem_ID == None:
            return redirect('/')
        if Problem_Manager.In_Contest(Problem_ID) and Login_Manager.Get_Privilege() <= 0: # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Problem_ID = Problem_ID, Blocked = True) # Discussion Closed
        Username = Login_Manager.Get_Username() # for whether to display edit or delete
        Privilge = Login_Manager.Get_Privilege()
        Discuss = Discuss_Manager.Get_Discuss_For_Problem(Problem_ID)
        return render_template('problem_discussion.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Problem_ID = Problem_ID, Username = Username, Privilge = Privilge, Discuss = Discuss)
    else:
        if not Login_Manager.Check_User_Status():
            return redirect('login')
        Action = request.form.get('action') # post, edit, delete
        Problem_ID = int(request.form.get('problem_id')) # this argument must be given
        if Action == 'post':
            Text = request.form.get('text')
            Username = Login_Manager.Get_Username()
            Discuss_Manager.Add_Discuss(Problem_ID, Username, Text)
            return redirect('/discuss?problem_id=' + Problem_ID)
        if Action == 'edit':
            Discuss_ID = int(request.form.get('id'))
            Text = request.form.get('text')
            Username = Login_Manager.Get_Username()
            if Username == Discuss_Manager.Get_Author(Discuss_ID) or Login_Manager.Get_Privilege() > 0: # same user or administrator
                Discuss_Manager.Modify_Discuss(Discuss_ID, Text)
            else:
                print('Access Dined in Discuss: Edit')
            return redirect('/discuss?problem_id=' + Problem_ID)
        if Action == 'delete':
            Discuss_ID = int(request.form.get('id'))
            Username = Login_Manager.Get_Username()
            if Username == Discuss_Manager.Get_Author(Discuss_ID) or Login_Manager.Get_Privilege() > 0: # same user or administrator
                Discuss_Manager.Delete_Discuss(Discuss_ID)
            else:
                print('Access Dined in Discuss: Delete')
            return redirect('/discuss?problem_id=' + Problem_ID)
        else: # what happened?
            return redirect('/discuss?problem_id=' + Problem_ID)

@web.route('/status')
def Status(): # todo: Search: use other function to build page?
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Page = request.args.get('page')
    Page = int(Page) if Page != None else 1
    max_Page = int((Judge_Manager.Max_ID() + JudgeConfig.Judge_Each_Page - 1) / JudgeConfig.Judge_Each_Page)
    Page = max(min(max_Page, Page), 1)
    endID = Judge_Manager.Max_ID() - (Page - 1) * JudgeConfig.Judge_Each_Page
    startID = endID - JudgeConfig.Judge_Each_Page + 1
    print('id = ', startID, endID)
    Record = Judge_Manager.Judge_In_Range(startID, endID)
    Username = Login_Manager.Get_Username()
    Privilege = Login_Manager.Get_Privilege()
    Data = []
    for ele in Record:
        cur = {}
        cur['ID'] = ele['ID']
        cur['Friendly_Name'] = User_Manager.Get_Friendly_Name(ele['Username'])
        cur['Problem_ID'] = ele['Problem_ID']
        cur['Problem_Title'] = Problem_Manager.Get_Title(ele['Problem_ID'])
        cur['Status'] = ele['Status']
        cur['Time_Used'] = ele['Time_Used']
        cur['Mem_Used'] = ele['Mem_Used']
        cur['Lang'] = ele['Lang']
        cur['Visible'] = Username == ele['Username'] or Privilege == 2 # Same User or login as Super Admin
        cur['Time'] = Readable_Time(ele['Time'])
        Data.append(cur)
    return render_template('status.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Data = Data, Pages = Gen_Page(Page, max_Page))


@web.route('/code')
def Code(): # todo: View Judge Detail
    return 'Todo'

@web.route('/contest')
def Contest(): # todo: debug Contest and homework
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Contest_ID = request.args.get('contest_id')
    if Contest_ID == None: # display contest list
        List = Conetst_Manager.List_Contest(0)
        Data = []
        curTime = UnixNano()
        for ele in List:
            cur = {}
            cur['ID'] = int(ele[0])
            cur['Title'] = str(ele[1])
            cur['Start_Time'] = Readable_Time(int(ele['Start_Time']))
            cur['End_Time'] = Readable_Time(int(ele['End_Time']))
            if curTime < int(ele['Start_Time']):
                cur['Status'] = 'Pending'
            elif curTime > int(ele['End_Time']):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            Data.append(cur)
        return render_template('contest_list.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Data = Data)
    else:
        Contest_ID = int(Contest_ID)
        StartTime, Endtime = Conetst_Manager.Get_Time(Contest_ID)
        Problems = Conetst_Manager.List_Player_For_Contest(Contest_ID)
        Players = Conetst_Manager.List_Player_For_Contest(Contest_ID)
        Data = []
        for Player in Players:
            tmp = [0, 0, ]
            for Problem in Problems:
                Submits = Judge_Manager.Get_Contest_Judge(int(Problem), Player, StartTime, Endtime)
                maxScore = 0
                isAC = False
                Submit_Time = 0
                for Submit in Submits:
                    maxScore = max(maxScore, int(Submit[2]))
                    Submit_Time += 1
                    if Submit[1] == 'AC':
                        isAC = True
                        tmp[1] += int(Submit[3]) - StartTime + (Submit_Time - 1) * 1200
                tmp[0] += maxScore
                tmp.append([isAC, Submit_Time]) # AC try time or failed times
            Data.append(tmp)
        Data = sorted(Data, key = lambda x, y: x[1] < y[1] if x[0] == y[0] else x[0] > y[0])
        return render_template('contest.html', Friendly_Username = Login_Manager.Get_FriendlyName(), StartTime = StartTime, Endtime = Endtime, Problems = Problems, Players = Players, Data = Data)

@web.route('/homework')
def Homework():
    if not Login_Manager.Check_User_Status():
        return redirect('login?next=' + request.url)
    Contest_ID = request.args.get('contest_id')
    if Contest_ID == None: # display contest list
        List = Conetst_Manager.List_Contest(1)
        Data = []
        curTime = UnixNano()
        for ele in List:
            cur = {}
            cur['ID'] = int(ele[0])
            cur['Title'] = str(ele[1])
            cur['Start_Time'] = Readable_Time(int(ele['Start_Time']))
            cur['End_Time'] = Readable_Time(int(ele['End_Time']))
            if curTime < int(ele['Start_Time']):
                cur['Status'] = 'Pending'
            elif curTime > int(ele['End_Time']):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            Data.append(cur)
        return render_template('homework_list.html', Friendly_Username = Login_Manager.Get_FriendlyName(), Data = Data)
    else:
        Contest_ID = int(Contest_ID)
        StartTime, Endtime = Conetst_Manager.Get_Time(Contest_ID)
        Problems = Conetst_Manager.List_Player_For_Contest(Contest_ID)
        Players = Conetst_Manager.List_Player_For_Contest(Contest_ID)
        Data = []
        for Player in Players:
            tmp = [0, ]
            for Problem in Problems:
                Submits = Judge_Manager.Get_Contest_Judge(int(Problem), Player, StartTime, Endtime)
                isAC = False
                for Submit in Submits:
                    if Submit[1] == 'AC':
                        isAC = True
                if isAC:
                    tmp[0] += 1
                tmp.append([isAC]) # AC try time or failed times
            Data.append(tmp)
        return render_template('homework.html', Friendly_Username = Login_Manager.Get_FriendlyName(), StartTime = StartTime, Endtime = Endtime, Problems = Problems, Players = Players, Data = Data)

@web.route('/about')
def About():
    return 'Hua Q~'