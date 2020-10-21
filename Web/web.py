from flask import Flask, request, render_template, redirect, make_response, abort, send_from_directory
from uuid import uuid4
import re
from sessionManager import Login_Manager
from userManager import User_Manager
from problemManager import Problem_Manager
from discussManager import Discuss_Manager
from judgeManager import Judge_Manager
from contestManager import Contest_Manager
from judgeServerScheduler import JudgeServer_Scheduler
from judgeServerManager import JudgeServer_Manager
from referenceManager import Reference_Manager
from config import LoginConfig, WebConfig, JudgeConfig, ProblemConfig
from utils import *
from admin import admin
from api import api
from functools import cmp_to_key
import json
import os
from const import Privilege

web = Flask('WEB')
web.register_blueprint(admin, url_prefix='/admin')
web.register_blueprint(api, url_prefix='/api')


@web.errorhandler(500)
def error_500():
    return "Internal Server Error: invalid Request"


@web.route('/')
def index():
    return render_template('index.html', friendlyName=Login_Manager.get_friendly_name())


@web.route('/index.html')
def index2():
    return redirect('/')


@web.route('/api/get_username', methods=['POST'])
def get_username():
    return Login_Manager.get_friendly_name()


@web.route('/api/get_detail', methods=['POST'])
def get_detail():
    if not Login_Manager.check_user_status():
        return '-1'
    problem_id = request.form.get('problem_id')
    if Problem_Manager.get_release_time(problem_id) > UnixNano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        return '-1'
    return json.dumps(Problem_Manager.get_problem(problem_id))


@web.route('/api/join', methods=['POST'])
def join_contest():
    if not Login_Manager.check_user_status():
        return '-1'
    arg = request.form.get('contest_id')
    if arg is None:
        return '-1'
    st, ed = Contest_Manager.get_time(arg)
    if UnixNano() > ed:
        return '-1'
    username = Login_Manager.get_username()
    if not Contest_Manager.check_player_in_contest(arg, username):
        Contest_Manager.add_player_to_contest(arg, username)
    return '0'


@web.route('/api/code', methods=['POST'])
def get_code():
    if not Login_Manager.check_user_status():
        return '-1'
    arg = request.form.get('submit_id')
    if arg is None:
        return '-1'
    if not str(request.form.get('submit_id')).isdigit():  # bad argument
        return '-1'
    run_id = int(request.form.get('submit_id'))
    if run_id < 0 or run_id > Judge_Manager.max_id():
        return '-1'
    detail = Judge_Manager.query_judge(run_id)
    if detail['User'] != Login_Manager.get_username() and Login_Manager.get_privilege() < Privilege.SUPER and (
            not detail['Share'] or Problem_Manager.in_contest(detail['Problem_ID'])):
        return '-1'
    return detail['Code']


@web.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        nxt = request.args.get('next')
        nxt = '/' if nxt is None else nxt
        return render_template('login.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name())
    username = request.form.get('username')
    password = request.form.get('password')
    if not User_Manager.Check_Login(username, password):  # no need to avoid sql injection
        return '-1'
    lid = str(uuid4())
    Login_Manager.new_session(username, lid)
    ret = make_response('0')
    ret.set_cookie(key='Login_ID', value=lid, max_age=LoginConfig.Login_Life_Time)
    return ret


@web.route('/logout')
def logout():
    if not Login_Manager.check_user_status():
        return redirect('/')
    ret = make_response(redirect('/'))
    ret.delete_cookie('Login_ID')
    return ret


def validate(username: str, password: str, friendly_name: str, student_id: str) -> int:
    username_reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    password_reg = '([a-zA-Z0-9_\!\@\#\$\%\^&\*\(\)]{6,30})$'
    friendly_name_reg = '([a-zA-Z0-9_]{1,60})$'
    student_id_reg = '([0-9]{12})$'
    if re.match(username_reg, username) is None:
        return -1
    if re.match(password_reg, password) is None:
        return -1
    if re.match(friendly_name_reg, friendly_name) is None:
        return -1
    if re.match(student_id_reg, student_id) is None:
        return -1
    return 0 if User_Manager.Validate_Username(username) else -1


@web.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        nxt = request.args.get('next')
        return render_template('register.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name())
    username = request.form.get('username')
    password = request.form.get('password')
    friendly_name = request.form.get('friendly_name')
    student_id = request.form.get('student_id')
    val = validate(username, password, friendly_name, student_id)
    if val == 0:
        User_Manager.Add_User(username, student_id, friendly_name, password, '0')
    return str(val)


@web.route('/problems')
def problem_list():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.url.split('/')[-1])
    page = request.args.get('page')
    page = int(page) if page is not None else 1
    max_page = int(
        (Problem_Manager.get_max_id() - 999 + WebConfig.Problems_Each_Page - 1) / WebConfig.Problems_Each_Page)
    page = max(min(max_page, page), 1)
    start_id = (page - 1) * WebConfig.Problems_Each_Page + 1 + 999
    end_id = page * WebConfig.Problems_Each_Page + 999
    problems = Problem_Manager.problem_in_range(start_id, end_id, UnixNano(),
                                                Login_Manager.get_privilege() >= Privilege.ADMIN)
    return render_template('problem_list.html', Problems=problems, Pages=Gen_Page(page, max_page),
                           friendlyName=Login_Manager.get_friendly_name())


@web.route('/problem')
def problem_detail():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.url.split('/')[-1])
    problem_id = request.args.get('problem_id')
    if problem_id is None or int(problem_id) < 1000 or int(problem_id) > Problem_Manager.get_max_id():
        return redirect('/')  # No argument fed
    if Problem_Manager.get_release_time(problem_id) > UnixNano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        return abort(404)
    in_contest = Problem_Manager.in_contest(problem_id) and Login_Manager.get_privilege() < Privilege.ADMIN
    return render_template('problem_details.html', ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           In_Contest=in_contest, friendlyName=Login_Manager.get_friendly_name())


@web.route('/submit', methods=['GET', 'POST'])
def submit_problem():
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.url.split('/')[-1])
        if request.args.get('problem_id') is None:
            return abort(404)
        problem_id = int(request.args.get('problem_id'))
        if Problem_Manager.get_release_time(
                problem_id) > UnixNano() and Login_Manager.get_privilege() < Privilege.ADMIN:
            return abort(404)
        title = Problem_Manager.get_title(problem_id)
        in_contest = Problem_Manager.in_contest(id) and Login_Manager.get_privilege() < Privilege.ADMIN
        return render_template('problem_submit.html', Problem_ID=problem_id, Title=title, In_Contest=in_contest,
                               friendlyName=Login_Manager.get_friendly_name())
    else:
        if not Login_Manager.check_user_status():
            return redirect('login')
        problem_id = int(request.form.get('problem_id'))
        if Problem_Manager.get_release_time(
                problem_id) > UnixNano() and Login_Manager.get_privilege() < Privilege.ADMIN:
            return '-1'
        share = bool(request.form.get('shared', 0))  # 0 or 1
        if Problem_Manager.in_contest(
                id) and Login_Manager.get_privilege() < Privilege.ADMIN and share:  # invalid sharing
            return '-1'
        if problem_id < 1000 or problem_id > Problem_Manager.get_max_id():
            abort(404)
        if UnixNano() < Problem_Manager.get_release_time(
                int(problem_id)) and Login_Manager.get_privilege() < Privilege.ADMIN:
            return '-1'
        username = Login_Manager.get_username()
        lang = 0 if str(request.form.get('lang')) == 'cpp' else 1  # cpp or git
        user_code = request.form.get('code')
        if len(str(user_code)) > ProblemConfig.Max_Code_Length:
            return '-1'
        JudgeServer_Scheduler.Start_Judge(problem_id, username, user_code, lang, share)
        return '0'


@web.route('/rank')
def problem_rank():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.url.split('/')[-1])
    problem_id = request.args.get('problem_id')
    if problem_id is None:
        return redirect('/')
    sort_parameter = request.args.get('sort_param')
    if sort_parameter != 'time' and sort_parameter != 'memory' and sort_parameter != 'submit_time':
        sort_parameter = 'time'
    record = Judge_Manager.search_ac(problem_id)
    for i in range(0, len(record)):  # ID, User, Time_Used, Mem_Used, Language, Time
        record[i][2] = int(record[i][2])
        record[i][3] = int(record[i][3])
        record[i][5] = int(record[i][5])
    if sort_parameter == 'time':
        record = sorted(record, key=lambda x, y: x[2] < y[2])
    elif sort_parameter == 'memory':
        record = sorted(record, key=lambda x, y: x[3] < y[3])
    elif sort_parameter == 'memory':
        record = sorted(record, key=lambda x, y: x[5] < y[5])
    return render_template('problem_rank.html', Problem_ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           Data=record, friendlyName=Login_Manager.get_friendly_name())


@web.route('/discuss', methods=['GET', 'POST'])
def discuss():  # todo: Debug discuss
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.url.split('/')[-1])
        problem_id = int(request.args.get('problem_id'))
        if problem_id is None:
            return redirect('/')
        if Problem_Manager.in_contest(
                problem_id) and Login_Manager.get_privilege() < Privilege.ADMIN:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID=problem_id,
                                   Title=Problem_Manager.get_title(problem_id), Blocked=True,
                                   friendlyName=Login_Manager.get_friendly_name())  # Discussion Closed
        username = Login_Manager.get_username()  # for whether to display edit or delete
        privilege = Login_Manager.get_privilege()
        data = Discuss_Manager.Get_Discuss_For_Problem(problem_id)
        discussion = []
        for ele in data:
            tmp = [ele[0], ele[1], Readable_Time(int(ele[2]))]
            if ele[0] == username or privilege == 2:  # ele[3]: editable?
                tmp.append(True)
            else:
                tmp.append(False)
            discussion.append(tmp)
        return render_template('problem_discussion.html', Title=Problem_Manager.get_title(problem_id),
                               Discuss=discussion, friendlyName=Login_Manager.get_friendly_name())
    else:
        if not Login_Manager.check_user_status():
            return redirect('login')
        action = request.form.get('action')  # post, edit, delete
        problem_id = int(request.form.get('problem_id'))  # this argument must be given
        if action == 'post':
            text = request.form.get('text')
            username = Login_Manager.get_username()
            Discuss_Manager.Add_Discuss(problem_id, username, text)
            return redirect('/discuss?problem_id=' + str(problem_id))
        if action == 'edit':
            discuss_id = int(request.form.get('id'))
            text = request.form.get('text')
            username = Login_Manager.get_username()
            if username == Discuss_Manager.Get_Author(
                    discuss_id) or Login_Manager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                Discuss_Manager.Modify_Discuss(discuss_id, text)
            else:
                print('Access Dined in Discuss: Edit')
            return redirect('/discuss?problem_id=' + str(problem_id))
        if action == 'delete':
            discuss_id = int(request.form.get('id'))
            username = Login_Manager.get_username()
            if username == Discuss_Manager.Get_Author(
                    discuss_id) or Login_Manager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                Discuss_Manager.Delete_Discuss(discuss_id)
            else:
                print('Access Dined in Discuss: Delete')
            return redirect('/discuss?problem_id=' + str(problem_id))
        else:  # what happened?
            return redirect('/discuss?problem_id=' + str(problem_id))


def fix_status_cur(cur):
    cur['Status'] = str(cur['Status'])
    cur['Lang'] = 'C++' if int(cur['Lang']) == 0 else 'Git'
    return cur


@web.route('/status')
def status():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.url.split('/')[-1])

    page = request.args.get('page')
    arg_submitter = request.args.get('submitter', None)
    arg_problem_id = request.args.get('problem_id', None)
    arg_status = request.args.get('status', None)
    if arg_status == '-1':
        arg_status = None
    arg_lang = request.args.get('lang')
    if arg_lang == '-1':
        arg_lang = None
    username = Login_Manager.get_username()
    privilege = Login_Manager.get_privilege()
    is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN

    if arg_submitter is None and arg_problem_id is None and arg_status is None and arg_lang is None:
        page = int(page) if page is not None else 1
        max_page = int((Judge_Manager.max_id() + JudgeConfig.Judge_Each_Page - 1) / JudgeConfig.Judge_Each_Page)
        page = max(min(max_page, page), 1)
        end_id = Judge_Manager.max_id() - (page - 1) * JudgeConfig.Judge_Each_Page
        start_id = end_id - JudgeConfig.Judge_Each_Page + 1
        record = Judge_Manager.judge_in_range(start_id, end_id)
        data = []
        for ele in record:
            cur = {'ID': ele['ID'],
                   'Friendly_Name': User_Manager.Get_Friendly_Name(ele['Username']),
                   'Problem_ID': ele['Problem_ID'],
                   'Problem_Title': Problem_Manager.get_title(ele['Problem_ID']),
                   'Status': ele['Status'], 'Time_Used': ele['Time_Used'],
                   'Mem_Used': ele['Mem_Used'],
                   'Lang': ele['Lang'],
                   'Visible': username == ele['Username'] or privilege == 2 or (
                           bool(ele['Share']) and not Problem_Manager.in_contest(ele['Problem_ID'])),
                   'Time': Readable_Time(ele['Time'])}
            if is_admin:
                cur['Real_Name'] = Reference_Manager.Query_Realname(User_Manager.Get_Student_ID(ele['Username']))
            data.append(fix_status_cur(cur))
        return render_template('status.html', Data=data, Pages=Gen_Page(page, max_page), is_Admin=is_admin,
                               friendlyName=Login_Manager.get_friendly_name())
    else:
        record = Judge_Manager.search_judge(arg_submitter, arg_problem_id, arg_status, arg_lang)
        max_page = int((len(record) + JudgeConfig.Judge_Each_Page - 1) / JudgeConfig.Judge_Each_Page)
        page = int(page) if page is not None else 1
        page = max(min(max_page, page), 1)
        end_id = len(record) - (page - 1) * JudgeConfig.Judge_Each_Page
        start_id = max(end_id - JudgeConfig.Judge_Each_Page + 1, 1)
        record = reversed(record[start_id - 1: end_id])
        data = []
        for ele in record:  # ID, User, Problem_ID, Time, Time_Used, Mem_Used, Status, Language
            cur = {'ID': ele[0],
                   'Friendly_Name': User_Manager.Get_Friendly_Name(ele[1]),
                   'Problem_ID': ele[2],
                   'Problem_Title': Problem_Manager.get_title(ele[2]),
                   'Status': ele[6],
                   'Time_Used': ele[4],
                   'Mem_Used': ele[5],
                   'Lang': ele[7],
                   'Visible': username == ele[1] or privilege == 2 or (
                           bool(ele[8]) and not Problem_Manager.in_contest(ele[2])),
                   'Time': Readable_Time(ele[3])}
            data.append(fix_status_cur(cur))
        return render_template('status.html', Data=data, Pages=Gen_Page(page, max_page), Submitter=arg_submitter,
                               Problem_ID=arg_problem_id, friendlyName=Login_Manager.get_friendly_name())


@web.route('/code')
def code():
    if not Login_Manager.check_user_status():  # not login
        return redirect('login?next=' + request.url.split('/')[-1])
    if not str(request.args.get('submit_id')).isdigit():  # bad argument
        abort(404)
    run_id = int(request.args.get('submit_id'))
    if run_id < 0 or run_id > Judge_Manager.max_id():
        abort(404)
    detail = Judge_Manager.query_judge(run_id)
    if detail['User'] != Login_Manager.get_username() and Login_Manager.get_privilege() < Privilege.SUPER and (
            not detail['Share'] or Problem_Manager.in_contest(detail['Problem_ID'])):
        return abort(403)
    else:
        detail['Friendly_Name'] = User_Manager.Get_Friendly_Name(detail['User'])
        detail['Problem_Title'] = Problem_Manager.get_title(detail['Problem_ID'])
        detail['Lang'] = 'C++' if detail['Lang'] == 0 else 'Git'
        detail['Time'] = Readable_Time(int(detail['Time']))
        data = None
        if detail['Detail'] != 'None':
            temp = json.loads(detail['Detail'])
            detail['Score'] = int(temp[1])
            data = temp[4:]
        else:
            detail['Score'] = 0
        return render_template('judge_detail.html', Detail=detail, Data=data,
                               friendlyName=Login_Manager.get_friendly_name())


@web.route('/contest')
def contest():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.url.split('/')[-1])
    contest_id = request.args.get('contest_id')
    username = Login_Manager.get_username()
    if contest_id is None:  # display contest list
        contest_list = Contest_Manager.list_contest(0)
        data = []
        cur_time = UnixNano()
        for ele in contest_list:
            cur = {'ID': int(ele[0]),
                   'Title': str(ele[1]),
                   'Start_Time': Readable_Time(int(ele[2])),
                   'End_Time': Readable_Time(int(ele[3])),
                   'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
                   'Blocked': UnixNano() > int(ele[3])}
            if cur_time < int(ele[2]):
                cur['Status'] = 'Pending'
            elif cur_time > int(ele[3]):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            data.append(cur)
        return render_template('contest_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name())
    else:
        contest_id = int(contest_id)
        start_time, end_time = Contest_Manager.get_time(contest_id)
        problems = Contest_Manager.list_problem_for_contest(contest_id)
        players = Contest_Manager.list_player_for_contest(contest_id)
        data = []
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        for Player in players:
            tmp = [0, 0, User_Manager.Get_Friendly_Name(Player)]
            for Problem in problems:
                submits = Judge_Manager.get_contest_judge(int(Problem[0]), Player[0], start_time, end_time)
                max_score = 0
                is_ac = False
                submit_time = 0
                if submits is not None:
                    for Submit in submits:
                        max_score = max(max_score, int(Submit[2]))
                        submit_time += 1
                        if int(Submit[1]) == 2:
                            is_ac = True
                            tmp[1] += int(Submit[3]) - start_time + (submit_time - 1) * 1200
                            break
                tmp[0] += max_score
                tmp.append([max_score, submit_time, is_ac])  # AC try time or failed times
            if is_admin:
                tmp.append(Reference_Manager.Query_Realname(User_Manager.Get_Student_ID(Player)))
            else:
                tmp.append("")
            tmp[1] //= 60
            data.append(tmp)

        cur_time = UnixNano()
        if cur_time < start_time:
            contest_status = 'Pending'
        elif cur_time > end_time:
            contest_status = 'Finished'
        else:
            contest_status = 'Going On'
        data = sorted(data, key=cmp_to_key(lambda x, y: y[0] - x[0] if x[0] != y[0] else x[1] - y[1]))
        title = Contest_Manager.get_title(contest_id)[0][0]
        return render_template('contest.html', id=contest_id, Title=title, Status=contest_status,
                               StartTime=Readable_Time(start_time), EndTime=Readable_Time(end_time), Problems=problems,
                               Data=data, len=len(players), len2=len(problems), is_Admin=is_admin,
                               Percentage=min(
                                   max(int(100 * float(UnixNano() - start_time) / float(end_time - start_time)), 0),
                                   100), friendlyName=Login_Manager.get_friendly_name())


@web.route('/homework')
def homework():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.url.split('/')[-1])
    contest_id = request.args.get('homework_id')
    username = Login_Manager.get_username()
    if contest_id is None:  # display contest list
        contest_list = Contest_Manager.list_contest(1)
        data = []
        cur_time = UnixNano()
        for ele in contest_list:
            cur = {'ID': int(ele[0]),
                   'Title': str(ele[1]),
                   'Start_Time': Readable_Time(int(ele[2])),
                   'End_Time': Readable_Time(int(ele[3])),
                   'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
                   'Blocked': UnixNano() > int(ele[3])}
            if cur_time < int(ele[2]):
                cur['Status'] = 'Pending'
            elif cur_time > int(ele[3]):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            data.append(cur)
        return render_template('homework_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name())
    else:
        contest_id = int(contest_id)
        start_time, end_time = Contest_Manager.get_time(contest_id)
        problems = Contest_Manager.list_problem_for_contest(contest_id)
        players = Contest_Manager.list_player_for_contest(contest_id)
        data = []
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        for Player in players:
            tmp = [0, User_Manager.Get_Friendly_Name(Player)]
            for Problem in problems:
                submits = Judge_Manager.get_contest_judge(int(Problem[0]), Player[0], start_time, end_time)
                is_ac = False
                try_time = 0
                if submits is not None:
                    for Submit in submits:
                        try_time += 1
                        if int(Submit[1]) == 2:
                            is_ac = True
                            break
                if is_ac:
                    tmp[0] += 1
                tmp.append([is_ac, try_time])  # AC try time or failed times
            if is_admin:
                tmp.append(Reference_Manager.Query_Realname(User_Manager.Get_Student_ID(Player)))
            else:
                tmp.append("")
            data.append(tmp)

        cur_time = UnixNano()
        if cur_time < start_time:
            contest_status = 'Pending'
        elif cur_time > end_time:
            contest_status = 'Finished'
        else:
            contest_status = 'Going On'
        title = Contest_Manager.get_title(contest_id)[0][0]
        return render_template('homework.html', id=contest_id, Title=title, Status=contest_status,
                               StartTime=Readable_Time(start_time), EndTime=Readable_Time(end_time), Problems=problems,
                               Players=players, Data=data, len=len(players), len2=len(problems), is_Admin=is_admin,
                               Percentage=min(
                                   max(int(100 * float(UnixNano() - start_time) / float(end_time - start_time)), 0),
                                   100), friendlyName=Login_Manager.get_friendly_name())


@web.route('/about')
def about():
    server_list = JudgeServer_Manager.Get_Server_List()
    return render_template('about.html', Server_List=server_list, friendlyName=Login_Manager.get_friendly_name())


@web.route('/feed')
def feed():
    return render_template('feed.html', friendlyName=Login_Manager.get_friendly_name())


@web.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(web.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
