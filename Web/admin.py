from flask import request, render_template, Blueprint, abort, Response, stream_with_context
import requests
from requests.models import Request
from const import *
from sessionManager import Login_Manager
from userManager import User_Manager
from problemManager import Problem_Manager
from contestManager import Contest_Manager
from requests import post
from requests.exceptions import RequestException
from config import DataConfig, PicConfig
import json
import hashlib

admin = Blueprint('admin', __name__, static_folder='static')


# TODO(Pioooooo): validate data
def _validate_user_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    # TODO: validate username
    op = int(form[String.TYPE])
    if 0 <= op < 2:
        # TODO: validate
        return None
    return None


def _validate_problem_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    op = int(form[String.TYPE])
    if 1 <= op < 3:
        # TODO: validate ID
        return None
    if 0 <= op < 2:
        # TODO: validate
        return None
    return None


def _validate_contest_data(form):
    if String.TYPE not in form:
        return ReturnCode.ERR_BAD_DATA
    op = int(form[String.TYPE])
    if 1 <= op < 6:
        # TODO: validate contest ID
        return None
    if 0 <= op < 2:
        # TODO: validate
        return None
    elif 3 <= op < 5:
        # TODO: validate problem ID
        return None
    elif 5 <= op < 6:
        # TODO: validate username
        return None
    return None


@admin.route('/')
def index():
    privilege = Login_Manager.get_privilege()
    if privilege < Privilege.ADMIN:
        abort(404)
    return render_template('admin.html', privilege=privilege, Privilege=Privilege, is_Admin=True,
                           friendlyName=Login_Manager.get_friendly_name())


@admin.route('/user', methods=['post'])
def user_manager():
    if Login_Manager.get_privilege() < Privilege.SUPER:
        abort(404)
    form = request.json
    # err = _validate_user_data(form)
    # if err is not None:
    #     return err
    try:
        op = int(form[String.TYPE])
        if op == 0:
            User_Manager.add_user(form[String.USERNAME], int(form[String.STUDENT_ID]), form[String.FRIENDLY_NAME],
                                  form[String.PASSWORD], form[String.PRIVILEGE])
            return ReturnCode.SUC_ADD_USER
        elif op == 1:
            User_Manager.modify_user(form[String.USERNAME], form.get(String.STUDENT_ID, None),
                                     form.get(String.FRIENDLY_NAME, None), form.get(String.PASSWORD, None),
                                     form.get(String.PRIVILEGE, None))
            return ReturnCode.SUC_MOD_USER
        elif op == 2:
            User_Manager.delete_user(form[String.USERNAME])
            return ReturnCode.SUC_DEL_USER
        else:
            return ReturnCode.ERR_BAD_DATA
    except KeyError:
        return ReturnCode.ERR_BAD_DATA
    except TypeError:
        return ReturnCode.ERR_BAD_DATA


@admin.route('/problem', methods=['post'])
def problem_manager():
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    form = request.json
    # err = _validate_problem_data(form)
    # if err is not None:
    #     return err
    try:
        op = int(form[String.TYPE])
        if op == 0:
            Problem_Manager.add_problem(int(form[String.PROBLEM_ID]), form.get(String.TITLE, None),
                                        form.get(String.DESCRIPTION, None), form.get(String.INPUT, None),
                                        form.get(String.OUTPUT, None), form.get(String.EXAMPLE_INPUT, None),
                                        form.get(String.EXAMPLE_OUTPUT, None), form.get(String.DATA_RANGE, None),
                                        form.get(String.RELEASE_TIME, None), form.get(String.PROBLEM_TYPE, None))
            return ReturnCode.SUC_ADD_PROBLEM
        elif op == 1:
            Problem_Manager.modify_problem(int(form[String.PROBLEM_ID]), form.get(String.TITLE, None),
                                           form.get(String.DESCRIPTION, None), form.get(String.INPUT, None),
                                           form.get(String.OUTPUT, None), form.get(String.EXAMPLE_INPUT, None),
                                           form.get(String.EXAMPLE_OUTPUT, None), form.get(String.DATA_RANGE, None),
                                           form.get(String.RELEASE_TIME, None), form.get(String.PROBLEM_TYPE, None))
            return ReturnCode.SUC_MOD_PROBLEM
        elif op == 2:
            Problem_Manager.delete_problem(form[String.PROBLEM_ID])
            return ReturnCode.SUC_DEL_PROBLEM
        else:
            return ReturnCode.ERR_BAD_DATA
    except KeyError:
        return ReturnCode.ERR_BAD_DATA
    except TypeError:
        return ReturnCode.ERR_BAD_DATA


@admin.route('/contest', methods=['post'])
def contest_manager():
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    form = request.json
    # err = _validate_contest_data(form)
    # if err is not None:
    #     return err
    try:
        op = int(form[String.TYPE])
        if op == 0:
            Contest_Manager.create_contest(form[String.CONTEST_NAME], int(form[String.START_TIME]),
                                           int(form[String.END_TIME]),
                                           int(form[String.CONTEST_TYPE]))
            return ReturnCode.SUC_ADD_CONTEST
        elif op == 1:
            Contest_Manager.modify_contest(int(form[String.CONTEST_ID]), form.get(String.CONTEST_NAME, None),
                                           int(form.get(String.START_TIME, None)), int(form.get(String.END_TIME, None)),
                                           int(form.get(String.CONTEST_TYPE, None)))
            return ReturnCode.SUC_MOD_CONTEST
        elif op == 2:
            Contest_Manager.delete_contest(int(form[String.CONTEST_ID]))
            return ReturnCode.SUC_DEL_CONTEST
        elif op == 3:
            for problemId in form[String.CONTEST_PROBLEM_IDS]:
                Contest_Manager.add_problem_to_contest(int(form[String.CONTEST_ID]), int(problemId))
            return ReturnCode.SUC_ADD_PROBLEMS_TO_CONTEST
        elif op == 4:
            for problemId in form[String.CONTEST_PROBLEM_IDS]:
                Contest_Manager.delete_problem_from_contest(int(form[String.CONTEST_ID]), int(problemId))
            return ReturnCode.SUC_DEL_PROBLEMS_FROM_CONTEST
        elif op == 5:
            for username in form[String.CONTEST_USERNAMES]:
                Contest_Manager.add_player_to_contest(int(form[String.CONTEST_ID]), username)
            return ReturnCode.SUC_ADD_USERS_TO_CONTEST
        elif op == 6:
            for username in form[String.CONTEST_USERNAMES]:
                Contest_Manager.delete_player_from_contest(int(form[String.CONTEST_ID]), username)
            return ReturnCode.SUC_DEL_USERS_FROM_CONTEST
        else:
            return ReturnCode.ERR_BAD_DATA
    except KeyError:
        return ReturnCode.ERR_BAD_DATA
    except TypeError:
        return ReturnCode.ERR_BAD_DATA


@admin.route('/data', methods=['POST'])
def data_upload():
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    if 'file' in request.files:
        f = request.files['file']
        try:
            r = post(DataConfig.server + '/' + DataConfig.key + '/upload.php', files={'file': (f.filename, f)})
            return {'e': 0, 'msg': r.content.decode('utf-8')}
        except RequestException:
            return ReturnCode.ERR_NETWORK_FAILURE
    return ReturnCode.ERR_BAD_DATA


@admin.route('/data_download', methods=['POST'])
def data_download():
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    id = request.form['id']
    try:
        r = requests.get(DataConfig.server + '/' + DataConfig.key + '/' + str(id) + '.zip', stream=True)
        resp = Response(stream_with_context(r.iter_content(chunk_size = 512)), content_type = 'application/octet-stream')
        resp.headers["Content-disposition"] = 'attachment; filename=' + str(id) +'.zip'
        return resp
    except RequestException:
        return ReturnCode.ERR_NETWORK_FAILURE


@admin.route('/pic', methods=['POST'])
def pic_upload():
    if Login_Manager.get_privilege() < Privilege.ADMIN:
        abort(404)
    if 'file' in request.files:
        f = request.files['file']
        try:
            hasher = hashlib.md5()
            hasher.update(f.filename.encode('utf-8'))
            filenamehashed = str(hasher.hexdigest()) + f.filename[f.filename.rindex("."):].lower()
            r = post(PicConfig.server + '/' + PicConfig.key + '/upload.php', files={'file': (filenamehashed, f)})
            response_text = r.content.decode('utf-8')
            notify_text = 'Unknown Error'
            if response_text == '0':
                ret_notify = ReturnCode.SUC_PIC_SERVICE_UPLOAD
                ret_notify['link'] = PicConfig.server + '/' + filenamehashed
                return ret_notify
            elif response_text == '-500':
                return ReturnCode.ERR_PIC_SERIVCE_TOO_BIG
            elif response_text == '-501':
                return ReturnCode.ERR_PIC_SERIVCE_WRONG_EXT
            elif response_text == '-502':
                return ReturnCode.ERR_PIC_SERIVCE_SYSTEM_ERROR
        except RequestException:
            return ReturnCode.ERR_NETWORK_FAILURE
    return ReturnCode.ERR_BAD_DATA

