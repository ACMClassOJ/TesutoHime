from flask import Flask, request, render_template, redirect, make_response, abort, send_from_directory
from uuid import uuid4
import re
from typing import Optional
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
from const import Privilege, ReturnCode
from tracker import tracker

web = Flask('WEB')
web.register_blueprint(admin, url_prefix='/admin')
web.register_blueprint(api, url_prefix='/api')


def validate(username: Optional['str'] = None, password: Optional['str'] = None, friendly_name: Optional['str'] = None,
             student_id: Optional['str'] = None) -> int:
    username_reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    password_reg = '([a-zA-Z0-9_\!\@\#\$\%\^&\*\(\)]{6,30})$'
    friendly_name_reg = '([a-zA-Z0-9_]{1,60})$'
    student_id_reg = '([0-9]{12})$'
    if username is not None and re.match(username_reg, username) is None:
        return -1
    if password is not None and re.match(password_reg, password) is None:
        return -1
    if friendly_name is not None and re.match(friendly_name_reg, friendly_name) is None:
        return -1
    if student_id is not None and re.match(student_id_reg, student_id) is None:
        return -1
    if username is not None and not User_Manager.validate_username(username):
        return -1
    return 0


def readable_lang(lang: int) -> str:
    lang_str = {
        0: 'C++',
        1: 'Git',
        2: 'Verilog'
    }
    try:
        return lang_str[lang]
    except KeyError:
        return 'UNKNOWN'


@web.errorhandler(500)
def error_500():
    return "Internal Server Error: invalid Request"


@web.before_request
def log():
    if request.full_path.startswith(('/api', '/static')):
        return
    tracker.log()


@web.route('/')
def index():
    return render_template('index.html', friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


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
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
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
    if unix_nano() > ed:
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
        return render_template('login.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    if not User_Manager.check_login(username, password):  # no need to avoid sql injection
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


@web.route('/register', methods=['GET', 'POST'])
def register():
    if WebConfig.Block_Register:
        abort(404)
    if request.method == 'GET':
        nxt = request.args.get('next')
        return render_template('register.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    friendly_name = request.form.get('friendly_name')
    student_id = request.form.get('student_id')
    val = validate(username, password, friendly_name, student_id)
    if val == 0:
        User_Manager.add_user(username, student_id, friendly_name, password, '0')
    return str(val)


@web.route('/problems')
def problem_list():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    page = request.args.get('page')
    page = int(page) if page is not None else 1
    max_page = int(
        (Problem_Manager.get_max_id() - 999 + WebConfig.Problems_Each_Page - 1) / WebConfig.Problems_Each_Page)
    page = max(min(max_page, page), 1)
    start_id = (page - 1) * WebConfig.Problems_Each_Page + 1 + 999
    end_id = page * WebConfig.Problems_Each_Page + 999
    problems = Problem_Manager.problem_in_range(start_id, end_id, unix_nano(),
                                                Login_Manager.get_privilege() >= Privilege.ADMIN)
    return render_template('problem_list.html', Problems=problems, Pages=gen_page(page, max_page),
                           friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/problem')
def problem_detail():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    problem_id = request.args.get('problem_id')
    if problem_id is None or int(problem_id) < 1000 or int(problem_id) > Problem_Manager.get_max_id():
        abort(404)  # No argument fed
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    in_contest = Problem_Manager.in_contest(problem_id) and Login_Manager.get_privilege() < Privilege.ADMIN
    return render_template('problem_details.html', ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           In_Contest=in_contest, friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/submit', methods=['GET', 'POST'])
def submit_problem():
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.full_path)
        if request.args.get('problem_id') is None:
            abort(404)
        problem_id = int(request.args.get('problem_id'))
        if Problem_Manager.get_release_time(
                problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
            abort(404)
        title = Problem_Manager.get_title(problem_id)
        in_contest = Problem_Manager.in_contest(id) and Login_Manager.get_privilege() < Privilege.ADMIN
        return render_template('problem_submit.html', Problem_ID=problem_id, Title=title, In_Contest=in_contest,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.full_path)
        problem_id = int(request.form.get('problem_id'))
        if Problem_Manager.get_release_time(
                problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
            return '-1'
        share = bool(request.form.get('shared', 0))  # 0 or 1
        if Problem_Manager.in_contest(
                id) and Login_Manager.get_privilege() < Privilege.ADMIN and share:  # invalid sharing
            return '-1'
        if problem_id < 1000 or problem_id > Problem_Manager.get_max_id():
            abort(404)
        if unix_nano() < Problem_Manager.get_release_time(
                int(problem_id)) and Login_Manager.get_privilege() < Privilege.ADMIN:
            return '-1'
        username = Login_Manager.get_username()
        lang = -1
        lang_request_str = str(request.form.get('lang'))
        if lang_request_str == 'cpp': 
            lang = 0
        elif lang_request_str == 'git':
            lang = 1
        elif lang_request_str == 'Verilog':
            lang = 2
        # cpp or git or Verilog
        user_code = request.form.get('code')
        if len(str(user_code)) > ProblemConfig.Max_Code_Length:
            return '-1'
        JudgeServer_Scheduler.Start_Judge(problem_id, username, user_code, lang, share)
        return '0'


@web.route('/rank')
def problem_rank():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    problem_id = request.args.get('problem_id')
    if problem_id is None:
        abort(404)
    sort_parameter = request.args.get('sort')
    record = Judge_Manager.search_ac(problem_id)
    if sort_parameter == 'memory':
        record = sorted(record, key=lambda x: x[3])
    elif sort_parameter == 'submit_time':
        record = sorted(record, key=lambda x: x[5])
    else:
        sort_parameter = 'time'
        record = sorted(record, key=lambda x: x[2])
    return render_template('problem_rank.html', Problem_ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           Data=record, Sorting=sort_parameter, friendlyName=Login_Manager.get_friendly_name(),
                           readable_lang=readable_lang, readable_time=readable_time,
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/discuss', methods=['GET', 'POST'])
def discuss():
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.full_path)
        problem_id = request.args.get('problem_id')
        if problem_id is None:
            abort(404)
        if Problem_Manager.in_contest(
                problem_id) and Login_Manager.get_privilege() < Privilege.ADMIN:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID=problem_id,
                                   Title=Problem_Manager.get_title(problem_id), Blocked=True,
                                   friendlyName=Login_Manager.get_friendly_name(),
                                   is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)  # Discussion Closed
        username = Login_Manager.get_username()  # for whether to display edit or delete
        privilege = Login_Manager.get_privilege()
        data = Discuss_Manager.get_discuss_for_problem(problem_id)
        discussion = []
        for ele in data:
            tmp = [ele[0], User_Manager.get_friendly_name(ele[1]), ele[2], readable_time(int(ele[3]))]
            if ele[1] == username or privilege == 2:  # ele[4]: editable?
                tmp.append(True)
            else:
                tmp.append(False)
            discussion.append(tmp)
        return render_template('problem_discussion.html', Problem_ID=problem_id,
                               Title=Problem_Manager.get_title(problem_id), Discuss=discussion,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        if not Login_Manager.check_user_status():
            return ReturnCode.ERR_USER_NOT_LOGGED_IN
        try:
            form = request.json
            action = form.get('action')  # post, edit, delete
            problem_id = form.get('problem_id')  # this argument must be given
            if action == 'post':
                text = form.get('text')
                username = Login_Manager.get_username()
                Discuss_Manager.add_discuss(problem_id, username, text)
                return ReturnCode.SUC
            if action == 'edit':
                discuss_id = form.get('discuss_id')
                text = form.get('text')
                username = Login_Manager.get_username()
                if username == Discuss_Manager.get_author(
                        discuss_id) or Login_Manager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                    Discuss_Manager.modify_discuss(discuss_id, text)
                    return ReturnCode.SUC
                else:
                    print('Access Dined in Discuss: Edit')
                    return ReturnCode.ERR_PERMISSION_DENIED
            if action == 'delete':
                discuss_id = form.get('discuss_id')
                username = Login_Manager.get_username()
                if username == Discuss_Manager.get_author(
                        discuss_id) or Login_Manager.get_privilege() >= Privilege.ADMIN:  # same user or administrator
                    Discuss_Manager.delete_discuss(discuss_id)
                    return ReturnCode.SUC
                else:
                    print('Access Dined in Discuss: Delete')
                    return ReturnCode.ERR_PERMISSION_DENIED
            else:  # what happened?
                return ReturnCode.ERR_BAD_DATA
        except KeyError:
            return ReturnCode.ERR_BAD_DATA
        except TypeError:
            return ReturnCode.ERR_BAD_DATA


@web.route('/status')
def status():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)

    page = request.args.get('page')
    arg_submitter = request.args.get('submitter')
    if arg_submitter == '':
        arg_submitter = None
    arg_problem_id = request.args.get('problem_id')
    if arg_problem_id == '':
        arg_problem_id = None
    arg_status = request.args.get('status')
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
    else:
        record = Judge_Manager.search_judge(arg_submitter, arg_problem_id, arg_status, arg_lang)
        max_page = int((len(record) + JudgeConfig.Judge_Each_Page - 1) / JudgeConfig.Judge_Each_Page)
        page = int(page) if page is not None else 1
        page = max(min(max_page, page), 1)
        end_id = len(record) - (page - 1) * JudgeConfig.Judge_Each_Page
        start_id = max(end_id - JudgeConfig.Judge_Each_Page + 1, 1)
        record = reversed(record[start_id - 1: end_id])
    data = []
    for ele in record:
        cur = {'ID': ele['ID'],
               'Friendly_Name': User_Manager.get_friendly_name(ele['Username']),
               'Problem_ID': ele['Problem_ID'],
               'Problem_Title': Problem_Manager.get_title(ele['Problem_ID']),
               'Status': ele['Status'],
               'Time_Used': ele['Time_Used'],
               'Mem_Used': ele['Mem_Used'],
               'Lang': readable_lang(ele['Lang']),
               'Visible': username == ele['Username'] or privilege == 2 or (
                       bool(ele['Share']) and not Problem_Manager.in_contest(ele['Problem_ID'])),
               'Time': readable_time(ele['Time'])}
        if is_admin:
            cur['Real_Name'] = Reference_Manager.Query_Realname(User_Manager.get_student_id(ele['Username']))
        data.append(cur)
    return render_template('status.html', Data=data, Pages=gen_page(page, max_page),
                           Args=dict(filter(lambda e: e[0] != 'page', request.args.items())),
                           is_Admin=is_admin, friendlyName=Login_Manager.get_friendly_name())


@web.route('/code')
def code():
    if not Login_Manager.check_user_status():  # not login
        return redirect('login?next=' + request.full_path)
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
        detail['Friendly_Name'] = User_Manager.get_friendly_name(detail['User'])
        detail['Problem_Title'] = Problem_Manager.get_title(detail['Problem_ID'])
        detail['Lang'] = readable_lang(detail['Lang'])
        detail['Time'] = readable_time(int(detail['Time']))
        data = None
        if detail['Detail'] != 'None':
            temp = json.loads(detail['Detail'])
            detail['Score'] = int(temp[1])
            data = temp[4:]
        else:
            detail['Score'] = 0
        return render_template('judge_detail.html', Detail=detail, Data=data,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/contest')
def contest():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    contest_id = request.args.get('contest_id')
    username = Login_Manager.get_username()
    if contest_id is None:  # display contest list
        contest_list = Contest_Manager.list_contest(0)
        data = []
        cur_time = unix_nano()
        for ele in contest_list:
            cur = {'ID': int(ele[0]),
                   'Title': str(ele[1]),
                   'Start_Time': readable_time(int(ele[2])),
                   'End_Time': readable_time(int(ele[3])),
                   'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
                   'Blocked': unix_nano() > int(ele[3])}
            if cur_time < int(ele[2]):
                cur['Status'] = 'Pending'
            elif cur_time > int(ele[3]):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            data.append(cur)
        return render_template('contest_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        contest_id = int(contest_id)
        start_time, end_time = Contest_Manager.get_time(contest_id)
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        problems = Contest_Manager.list_problem_for_contest(contest_id) if start_time <= unix_nano() or is_admin else []
        players = Contest_Manager.list_player_for_contest(contest_id)
        data = []
        for Player in players:
            tmp = [0, 0, User_Manager.get_friendly_name(Player)]
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
                tmp.append(Reference_Manager.Query_Realname(User_Manager.get_student_id(Player)))
            else:
                tmp.append("")
            tmp[1] //= 60
            data.append(tmp)

        cur_time = unix_nano()
        if cur_time < start_time:
            contest_status = 'Pending'
        elif cur_time > end_time:
            contest_status = 'Finished'
        else:
            contest_status = 'Going On'
        data = sorted(data, key=cmp_to_key(lambda x, y: y[0] - x[0] if x[0] != y[0] else x[1] - y[1]))
        title = Contest_Manager.get_title(contest_id)[0][0]
        return render_template('contest.html', id=contest_id, Title=title, Status=contest_status,
                               StartTime=readable_time(start_time), EndTime=readable_time(end_time), Problems=problems,
                               Data=data, len=len(players), len2=len(problems), is_Admin=is_admin,
                               Percentage=min(
                                   max(int(100 * float(unix_nano() - start_time) / float(end_time - start_time)), 0),
                                   100), friendlyName=Login_Manager.get_friendly_name())


@web.route('/homework')
def homework():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    contest_id = request.args.get('homework_id')
    username = Login_Manager.get_username()
    if contest_id is None:  # display contest list
        contest_list = Contest_Manager.list_contest(1)
        data = []
        cur_time = unix_nano()
        for ele in contest_list:
            cur = {'ID': int(ele[0]),
                   'Title': str(ele[1]),
                   'Start_Time': readable_time(int(ele[2])),
                   'End_Time': readable_time(int(ele[3])),
                   'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
                   'Blocked': unix_nano() > int(ele[3])}
            if cur_time < int(ele[2]):
                cur['Status'] = 'Pending'
            elif cur_time > int(ele[3]):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            data.append(cur)
        return render_template('homework_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        contest_id = int(contest_id)
        start_time, end_time = Contest_Manager.get_time(contest_id)
        problems = Contest_Manager.list_problem_for_contest(contest_id) if start_time <= unix_nano() else []
        players = Contest_Manager.list_player_for_contest(contest_id)
        data = []
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        for Player in players:
            tmp = [0, User_Manager.get_friendly_name(Player)]
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
                tmp.append(Reference_Manager.Query_Realname(User_Manager.get_student_id(Player)))
            else:
                tmp.append("")
            data.append(tmp)

        cur_time = unix_nano()
        if cur_time < start_time:
            contest_status = 'Pending'
        elif cur_time > end_time:
            contest_status = 'Finished'
        else:
            contest_status = 'Going On'
        title = Contest_Manager.get_title(contest_id)[0][0]
        return render_template('homework.html', id=contest_id, Title=title, Status=contest_status,
                               StartTime=readable_time(start_time), EndTime=readable_time(end_time), Problems=problems,
                               Players=players, Data=data, len=len(players), len2=len(problems), is_Admin=is_admin,
                               Percentage=min(
                                   max(int(100 * float(unix_nano() - start_time) / float(end_time - start_time)), 0),
                                   100), friendlyName=Login_Manager.get_friendly_name())


@web.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.full_path)
        return render_template('profile.html', friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    else:
        if not Login_Manager.check_user_status():
            return ReturnCode.ERR_USER_NOT_LOGGED_IN
        form = request.json
        try:
            ret = validate(password=form.get('password'), friendly_name=form.get('friendly_name'))
            if ret == 0:
                User_Manager.modify_user(Login_Manager.get_username(), None, form.get('friendly_name'), form.get(
                    'password'), None)
                return ReturnCode.SUC_MOD_USER

        except KeyError:
            return ReturnCode.ERR_BAD_DATA
        except TypeError:
            return ReturnCode.ERR_BAD_DATA


@web.route('/about')
def about():
    server_list = JudgeServer_Manager.Get_Server_List()
    return render_template('about.html', Server_List=server_list, friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/feed')
def feed():
    return render_template('feed.html', friendlyName=Login_Manager.get_friendly_name(),
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)


@web.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(web.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
