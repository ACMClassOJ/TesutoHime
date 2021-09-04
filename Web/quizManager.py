import os, shutil, requests, zipfile, json, sys
from config import QuizTempDataConfig
from collections import namedtuple
from const import ReturnCode
import json

class QuizManager:
    def get_json_from_data_service_by_id(self, config, id: int):
        r = requests.get(config.server + '/' + config.key + '/' + str(id) + '.zip', stream=True)
        with open(config.cache_dir + '/' + str(id) + '.zip', 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        shutil.rmtree(config.cache_dir + '/' + str(id), ignore_errors=True)
        with zipfile.ZipFile(config.cache_dir + '/' + str(id) + '.zip', 'r') as zip_file:
            zip_file.extractall(config.cache_dir)
        os.remove(config.cache_dir + '/' + str(id) + '.zip')
        with open(config.cache_dir + '/' + str(id) + '/quiz.json') as f:
            try:
                main_json = json.loads(f.read())
            except json.JSONDecodeError:
                return ReturnCode.ERR_QUIZ_JSON_DECODE
        return {**main_json, **ReturnCode.SUC_QUIZ_JSON_DECODE}
       
Quiz_Manager = QuizManager()