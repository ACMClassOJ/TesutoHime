from flask import Flask, Blueprint, request, render_template, redirect, make_response, abort, send_from_directory
from uuid import uuid4
import re
from typing import Optional
from sessionManager import Login_Manager
from userManager import User_Manager
from problemManager import Problem_Manager
from quizManager import Quiz_Manager
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
from contestCache import Contest_Cache

web = Blueprint('web', __name__, static_folder='static', template_folder='templates')
web.register_blueprint(admin, url_prefix='/admin')
web.register_blueprint(api, url_prefix='/api')


def validate(username: Optional['str'] = None, password: Optional['str'] = None, friendly_name: Optional['str'] = None,
             student_id: Optional['str'] = None) -> int:
    username_reg = '([a-zA-Z][a-zA-Z0-9_]{0,19})$'
    password_reg = '([a-zA-Z0-9_\!\@\#\$\%\^&\*\(\)]{6,30})$'
    friendly_name_reg = '([a-zA-Z0-9_]{1,60})$'
    student_id_reg = '([0-9]{12})$'
    if username is not None and re.match(username_reg, username) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_USERNAME
    if password is not None and re.match(password_reg, password) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_PASSWD
    if friendly_name is not None and re.match(friendly_name_reg, friendly_name) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_FRIENDLY_NAME
    if student_id is not None and re.match(student_id_reg, student_id) is None:
        return ReturnCode.ERR_VALIDATE_INVALID_STUDENT_ID
    if username is not None and not User_Manager.validate_username(username):
        print("12121")
        return ReturnCode.ERR_VALIDATE_USERNAME_EXISTS
    return ReturnCode.SUC_VALIDATE


def readable_lang(lang: int) -> str:
    lang_str = {
        0: 'C++',
        1: 'Git',
        2: 'Verilog',
        3: 'Quiz'
    }
    try:
        return lang_str[lang]
    except KeyError:
        return 'UNKNOWN'

"""
    The exam visibility part.
"""

def problem_in_exam(problem_id):
    # in exam means: 1. user is not admin. 2. the problem is in a running exam.
    # this is mainly for closing the discussion & rank part
    exam_id, is_exam_started = Contest_Manager.get_unfinished_exam_info_for_player(Login_Manager.get_username(), unix_nano())
    
    if exam_id == -1 or is_exam_started == False:
        return False

    return Login_Manager.get_privilege() < Privilege.ADMIN and Contest_Manager.check_problem_in_contest(exam_id, problem_id)


def is_code_visible(code_owner, problem_id, shared):
    # check whether the code is visible

    # admin always visible
    if Login_Manager.get_privilege() >= Privilege.ADMIN:
        return True
    
    username = Login_Manager.get_username()
    # exam first
    exam_id, is_exam_started = Contest_Manager.get_unfinished_exam_info_for_player(username, unix_nano())

    if exam_id != -1 and is_exam_started:
        # if the user is in a running exam, he can only see his own problems in exam.
        return code_owner == username and Contest_Manager.check_problem_in_contest(exam_id, problem_id)
    else:
        # otherwise, the user can see his own and shared problems
        return code_owner == username or shared

@web.errorhandler(500)
def error_500():
    return "Internal Server Error: invalid Request"


@web.before_request
def log():
    if request.full_path.startswith(('/OnlineJudge/static', '/OnlineJudge/api/heartBeat')) or request.full_path.endswith(('.js', '.css', '.ico')):
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


@web.route('/api/get_problem_id_autoinc', methods=['POST'])
def get_problem_id_autoinc():
    return str(Problem_Manager.get_max_id() + 1)

@web.route('/api/get_contest_id_autoinc', methods=['POST'])
def get_contest_id_autoinc():
    return str(Contest_Manager.get_max_id() + 1)

@web.route('/api/get_detail', methods=['POST'])
def get_detail():
    if not Login_Manager.check_user_status():
        return '-1'
    problem_id = request.form.get('problem_id')
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        return '-1'
    return json.dumps(Problem_Manager.get_problem(problem_id))

@web.route('/api/get_contest_detail', methods=['POST'])
def get_contest_detail():
    if not Login_Manager.check_user_status():
        return '-1'
    contest_id = request.form.get('contest_id')
    return json.dumps(Contest_Manager.get_contest(contest_id))

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
    if not is_code_visible(detail['User'], detail['Problem_ID'], detail['Share']):
        return '-1'
    return detail['Code']


@web.route('/api/quiz', methods=['POST'])
def get_quiz():
    if not Login_Manager.check_user_status():
        return ReturnCode.ERR_USER_NOT_LOGGED_IN
    problem_id = request.form.get('problem_id')
    if problem_id is None:
        return ReturnCode.ERR_BAD_DATA
    if not str(problem_id).isdigit():  # bad argument
        return ReturnCode.ERR_BAD_DATA
    problem_id = int(problem_id)
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        return ReturnCode.ERR_PERMISSION_DENIED
    problem_type = Problem_Manager.get_problem_type(problem_id)
    if problem_type != 1:
        return ReturnCode.ERR_PROBLEM_NOT_QUIZ
    quiz_json = Quiz_Manager.get_json_from_data_service_by_id(QuizTempDataConfig, problem_id)
    if quiz_json['e'] == 0:
        for i in quiz_json["problems"]:
            i["answer"] = ""
    return json.dumps(quiz_json)


@web.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        nxt = request.args.get('next')
        nxt = '/' if nxt is None else nxt
        return render_template('login.html', Next=nxt, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
    username = request.form.get('username')
    password = request.form.get('password')
    if username.endswith("mirror"):
        return ReturnCode.ERR_LOGIN_MIRROR
    if not User_Manager.check_login(username, password):  # no need to avoid sql injection
        return ReturnCode.ERR_LOGIN
    lid = str(uuid4())
    username = User_Manager.get_username(username)
    Login_Manager.new_session(username, lid)
    ret = make_response(ReturnCode.SUC_LOGIN)
    ret.set_cookie(key='Login_ID', value=lid, max_age=LoginConfig.Login_Life_Time)
    return ret


@web.route('/logout')
def logout():
    if not Login_Manager.check_user_status():
        return redirect('/OnlineJudge/')
    ret = make_response(redirect('/OnlineJudge/'))
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
    if val == ReturnCode.SUC_VALIDATE:
        User_Manager.add_user(username, student_id, friendly_name, password, '0')
        return ReturnCode.SUC_REGISTER
    else:
        return val


@web.route('/problems')
def problem_list():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    is_admin = bool(Login_Manager.get_privilege() >= Privilege.ADMIN)
    page = request.args.get('page')
    page = int(page) if page is not None else 1

    problem_id = request.args.get('problem_id')
    if problem_id == '':
        problem_id = None
    problem_name_keyword = request.args.get('problem_name_keyword')
    if problem_name_keyword == '':
        problem_name_keyword = None
    problem_type = request.args.get('problem_type')
    if problem_type == '-1' or problem_type == '':
        problem_type = None    
    contest_id = request.args.get('contest_id')
    if contest_id == '':
        contest_id = None        

    if problem_id is None and problem_name_keyword is None and problem_type is None and contest_id is None:
        problem_count_all = 0
        problem_count_under_11000 = 0
        if is_admin:
            problem_count_all = int(Problem_Manager.get_problem_count_admin())
            problem_count_under_11000 = (Problem_Manager.get_problem_count_under_11000_admin())
        else:
            problem_count_all = int(Problem_Manager.get_problem_count(unix_nano()))
            problem_count_under_11000 = (Problem_Manager.get_problem_count_under_11000(unix_nano()))
        max_page = int(problem_count_all / WebConfig.Problems_Each_Page)
        if problem_count_all % WebConfig.Problems_Each_Page != 0:
            max_page += 1
        latest_page_under_11000 = int(int(problem_count_under_11000 / WebConfig.Problems_Each_Page))
        if problem_count_under_11000 % WebConfig.Problems_Each_Page != 0:
            latest_page_under_11000 += 1
        page = max(min(max_page, page), 1)
        problems = Problem_Manager.problem_in_page_autocalc(page, WebConfig.Problems_Each_Page, unix_nano(),
                                                    Login_Manager.get_privilege() >= Privilege.ADMIN)

        return render_template('problem_list.html', Problems=problems, 
                            Pages=gen_page_for_problem_list(page, max_page, latest_page_under_11000),
                            Args=dict(),
                            friendlyName=Login_Manager.get_friendly_name(),
                            is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)

    problems = Problem_Manager.search_problem(unix_nano(), is_admin, problem_id, problem_name_keyword, problem_type, contest_id)
    max_page = int (len(problems) / WebConfig.Problems_Each_Page)
    page = max(min(max_page, page), 1)
    start_index = (page - 1) * WebConfig.Problems_Each_Page
    end_index = min(len(problems), page * WebConfig.Problems_Each_Page)
    return render_template('problem_list.html', Problems=problems[start_index:end_index],
                            Pages=gen_page_for_problem_list(page, max_page, 1),    
                            Args=dict(filter(lambda e: e[0] != 'page', request.args.items())),
                            friendlyName=Login_Manager.get_friendly_name(),
                            is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)                        

@web.route('/problem')
def problem_detail():
    if not Login_Manager.check_user_status():
        return redirect('login?next=' + request.full_path)
    problem_id = request.args.get('problem_id')
    if problem_id is None or int(problem_id) < 1000 or (int(problem_id) > Problem_Manager.get_max_id() and int(problem_id) < 11000) or int(problem_id) > Problem_Manager.get_real_max_id():
        abort(404)  # No argument fed
    if Problem_Manager.get_release_time(problem_id) > unix_nano() and Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    
    in_exam = problem_in_exam(problem_id)

    return render_template('problem_details.html', ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           In_Exam=in_exam, friendlyName=Login_Manager.get_friendly_name(),
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
        problem_type = Problem_Manager.get_problem_type(problem_id)
        in_exam = problem_in_exam(problem_id)
        if problem_type == 0:
            return render_template('problem_submit.html', Problem_ID=problem_id, Title=title, In_Exam=in_exam,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN)
        elif problem_type == 1:
            return render_template('quiz_submit.html', Problem_ID=problem_id, Title=title, In_Exam=in_exam,
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
        
        if problem_id < 1000 or (problem_id > Problem_Manager.get_max_id() and problem_id < 11000) or problem_id > Problem_Manager.get_real_max_id():
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
        elif lang_request_str == 'quiz':
            lang = 3
        # cpp or git or Verilog or quiz
        if lang == 3:
            user_code = json.dumps(request.form.to_dict())
        else:
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
    record = list(Judge_Manager.search_ac(problem_id))
    for i in range(len(record)):
        record[i] = list(record[i])
        record[i].append(User_Manager.get_friendly_name(record[i][1]))
        record[i].append(Reference_Manager.Query_Realname(User_Manager.get_student_id(record[i][1])))
    if sort_parameter == 'memory':
        record = sorted(record, key=lambda x: x[3])
    elif sort_parameter == 'submit_time':
        record = sorted(record, key=lambda x: x[5])
    else:
        sort_parameter = 'time'
        record = sorted(record, key=lambda x: x[2])
    
    in_exam = problem_in_exam(problem_id)
    
    return render_template('problem_rank.html', Problem_ID=problem_id, Title=Problem_Manager.get_title(problem_id),
                           Data=record, Sorting=sort_parameter, friendlyName=Login_Manager.get_friendly_name(),
                           readable_lang=readable_lang, readable_time=readable_time,
                           is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN,
                           In_Exam=in_exam)


@web.route('/discuss', methods=['GET', 'POST'])
def discuss():
    if request.method == 'GET':
        if not Login_Manager.check_user_status():
            return redirect('login?next=' + request.full_path)
        problem_id = request.args.get('problem_id')
        if problem_id is None:
            abort(404)
        
        in_exam = problem_in_exam(problem_id)

        if in_exam:  # Problem in Contest or Homework and Current User is NOT administrator
            return render_template('problem_discussion.html', Problem_ID=problem_id,
                                   Title=Problem_Manager.get_title(problem_id), Blocked=True,
                                   friendlyName=Login_Manager.get_friendly_name(),
                                   is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN,
                                   In_Exam=True)  # Discussion Closed
        username = Login_Manager.get_username()  # for whether to display edit or delete
        privilege = Login_Manager.get_privilege()
        data = Discuss_Manager.get_discuss_for_problem(problem_id)
        discussion = []
        for ele in data:
            tmp = [ele[0], User_Manager.get_friendly_name(ele[1]), ele[2], readable_time(int(ele[3]))]
            if ele[1] == username or privilege >= Privilege.SUPER:  # ele[4]: editable?
                tmp.append(True)
            else:
                tmp.append(False)
            discussion.append(tmp)
        return render_template('problem_discussion.html', Problem_ID=problem_id,
                               Title=Problem_Manager.get_title(problem_id), Discuss=discussion,
                               friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=Login_Manager.get_privilege() >= Privilege.ADMIN,
                               In_Exam=False)
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
                if Login_Manager.get_privilege() >= Privilege.ADMIN:    # administrator
                    Discuss_Manager.add_discuss(problem_id, username, text)
                    return ReturnCode.SUC
                else:
                    print('Access Dined in Discuss: Add')
                    return ReturnCode.ERR_PERMISSION_DENIED
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

    exam_id, is_exam_started = Contest_Manager.get_unfinished_exam_info_for_player(username, unix_nano())
    # if not None, only problems in here are visible to user
    exam_visible_problems = None

    # only change the visibility when the exam started
    if exam_id != -1 and is_exam_started: 
        exam_visible_problems = list()
        exam_problems_raw = Contest_Manager.list_problem_for_contest(exam_id)
        for raw_tuple in exam_problems_raw:
            exam_visible_problems.append(raw_tuple[0])

    for ele in record:
        cur = {'ID': ele['ID'],
               'Username': ele['Username'],
               'Friendly_Name': User_Manager.get_friendly_name(ele['Username']),
               'Problem_ID': ele['Problem_ID'],
               'Problem_Title': Problem_Manager.get_title(ele['Problem_ID']),
               'Status': ele['Status'],
               'Time_Used': ele['Time_Used'],
               'Mem_Used': ele['Mem_Used'],
               'Lang': readable_lang(ele['Lang']),
               'Visible': 
                       # This visible check is more effient than call "is_code_visible" each time.

                       # admin: always visible
                       is_admin or (
                           # user's own problem: username == ele['Username']
                           # shared problems are always banned if exam_visible_problems is None (this means user in exam)
                           (username == ele['Username'] or (exam_visible_problems is None and bool(ele['Share']))) 
                           # and exam visible check for problems
                           and (exam_visible_problems is None or ele['Problem_ID'] in exam_visible_problems)
                       )
                       ,
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
    if not is_code_visible(detail['User'], detail['Problem_ID'], detail['Share']):
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
        contest_list = Contest_Manager.list_contest_and_exam()
        data = []
        cur_time = unix_nano()
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        exam_id, _ = Contest_Manager.get_unfinished_exam_info_for_player(username, cur_time)
        # here exam_id is an *arbitary* unfinished exam in which the player is in 

        # Blocked: indicate whether the join button should be disabled because time is over
        # Joined: indicate whether the user has joined the contest, join button should also be disabled
        # Exam_Blocked: indicate that the user is in an *arbitary* exam, so even if there are available contests, join button should be disabled
        for ele in contest_list:
            cur = {'ID': int(ele[0]),
                   'Title': str(ele[1]),
                   'Start_Time': readable_time(int(ele[2])),
                   'End_Time': readable_time(int(ele[3])),
                   'Joined': Contest_Manager.check_player_in_contest(ele[0], username),
                   'Blocked': unix_nano() > int(ele[3]),
                   'Exam_Blocked': (exam_id != -1 and ele[4] == 2 and exam_id != int(ele[0]))}
            if cur_time < int(ele[2]):
                cur['Status'] = 'Pending'
            elif cur_time > int(ele[3]):
                cur['Status'] = 'Finished'
            else:
                cur['Status'] = 'Going On'
            data.append(cur)
        
        return render_template('contest_list.html', Data=data, friendlyName=Login_Manager.get_friendly_name(),
                               is_Admin=is_admin)
    elif not contest_id.isdigit():
        abort(404)
    else:
        contest_id = int(contest_id)
        if contest_id < 0 or contest_id > Contest_Manager.get_max_id():
            abort(404)  # No argument fed
        start_time, end_time = Contest_Manager.get_time(contest_id)
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        problems = Contest_Manager.list_problem_for_contest(contest_id)
        problems_visible = is_admin or unix_nano() >= start_time
        players = Contest_Manager.list_player_for_contest(contest_id)

        rankings = Contest_Cache.get(contest_id)
        if len(rankings) == 0:
            rankings = [
                {
                    'score': 0,
                    'penalty': 0,
                    'nickname': User_Manager.get_friendly_name(username),
                    'problems': [
                        {
                            'score': 0,
                            'count': 0,
                            'accepted': False,
                        } for _ in problems
                    ],
                    'realname': Reference_Manager.Query_Realname(User_Manager.get_student_id(username)),
                    'username': username,
                } for username in players
            ]
            username_to_num = dict(map(lambda entry: [regularize_string(entry[1]), entry[0]], enumerate(players)))
            problem_to_num = dict(map(lambda entry: [entry[1][0], entry[0]], enumerate(problems)))

            submits = Judge_Manager.get_contest_judge(problems, start_time, end_time)
            for submit in submits:
                [ _submit_id, username, problem_id, status, score, submit_time ] = submit

                if regularize_string(username) not in username_to_num:
                    continue

                rank = username_to_num[regularize_string(username)]
                problem_index = problem_to_num[problem_id]
                user_data = rankings[rank]
                problem = user_data['problems'][problem_index]

                if problem['accepted'] == True:
                    continue
                max_score = problem['score']
                # FIXME: magic number 2 for AC
                is_ac = int(status) == 2
                submit_count = problem['count']

                if int(score) > max_score:
                    user_data['score'] -= max_score
                    max_score = int(score)
                    user_data['score'] += max_score

                submit_count += 1

                if is_ac:
                    user_data['penalty'] += (int(submit_time) - start_time + (submit_count - 1) * 1200) // 60

                problem['score'] = max_score
                problem['count'] = submit_count
                problem['accepted'] = is_ac

            Contest_Cache.put(contest_id, rankings)    

        cur_time = unix_nano()
        if cur_time < start_time:
            contest_status = 'Pending'
        elif cur_time > end_time:
            contest_status = 'Finished'
        else:
            contest_status = 'Going On'
        rankings = sorted(rankings, key=cmp_to_key(lambda x, y: y['score'] - x['score'] if x['score'] != y['score'] else x['penalty'] - y['penalty']))
        title = Contest_Manager.get_title(contest_id)[0][0]

        time_elapsed = float(unix_nano() - start_time)
        time_overall = float(end_time - start_time)
        percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)

        return render_template(
            'contest.html',
            id=contest_id,
            Title=title,
            Status=contest_status,
            StartTime=readable_time(start_time),
            EndTime=readable_time(end_time),
            Problems=problems,
            problems_visible=problems_visible,
            rankings=rankings,
            is_Admin=is_admin,
            Percentage=percentage,
            friendlyName=Login_Manager.get_friendly_name(),
            enumerate=enumerate,
        )


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
    elif not contest_id.isdigit():
        abort(404)
    else:
        contest_id = int(contest_id)
        start_time, end_time = Contest_Manager.get_time(contest_id)
        is_admin = Login_Manager.get_privilege() >= Privilege.ADMIN
        problems = Contest_Manager.list_problem_for_contest(contest_id)
        problems_visible = is_admin or unix_nano() >= start_time
        players = Contest_Manager.list_player_for_contest(contest_id)

        data = Contest_Cache.get(contest_id)

        if len(data) == 0:  
            data = [
                {
                    'score': 0,
                    'nickname': User_Manager.get_friendly_name(username),
                    'problems': [
                        {
                            'accepted': False,
                            'count': 0,
                        } for _ in problems
                    ],
                    'realname': Reference_Manager.Query_Realname(User_Manager.get_student_id(username)),
                    'username': username,
                } for username in players
            ]
            username_to_num = dict(map(lambda entry: [regularize_string(entry[1]), entry[0]], enumerate(players)))
            problem_to_num = dict(map(lambda entry: [entry[1][0], entry[0]], enumerate(problems)))

            submits = Judge_Manager.get_contest_judge(problems, start_time, end_time)

            for submit in submits:
                [ _submit_id, username, problem_id, status, _score, _submit_time ] = submit

                if regularize_string(username) not in username_to_num:
                    continue

                user_num = username_to_num[regularize_string(username)]
                problem_index = problem_to_num[problem_id]
                user_data = data[user_num]
                problem = user_data['problems'][problem_index]

                if problem['accepted'] == True:
                    continue

                # FIXME: magic number 2 for AC
                if int(status) == 2:
                    problem['accepted'] = True
                    user_data['score'] += 1

                problem['count'] += 1

            Contest_Cache.put(contest_id, data)    

        cur_time = unix_nano()
        if cur_time < start_time:
            contest_status = 'Pending'
        elif cur_time > end_time:
            contest_status = 'Finished'
        else:
            contest_status = 'Going On'
        title = Contest_Manager.get_title(contest_id)[0][0]

        time_elapsed = float(unix_nano() - start_time)
        time_overall = float(end_time - start_time)
        percentage = min(max(int(100 * time_elapsed / time_overall), 0), 100)

        return render_template(
            'homework.html',
            id=contest_id,
            Title=title,
            Status=contest_status,
            StartTime=readable_time(start_time),
            EndTime=readable_time(end_time),
            Problems=problems,
            problems_visible=problems_visible,
            Players=players,
            data=data,
            is_Admin=is_admin,
            Percentage=percentage,
            friendlyName=Login_Manager.get_friendly_name(),
            enumerate=enumerate,
        )

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
            if ret == ReturnCode.SUC_VALIDATE:
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


@web.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(web.root_path, 'static'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')

oj = Flask('WEB')
oj.register_blueprint(web, url_prefix='/OnlineJudge')
oj.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400

