import os, zipfile, json
from config import S3Config
from utils import s3_internal
from const import ReturnCode
import json

class QuizManager:
    def get_json_from_data_service_by_id(self, config, id: int):
        key = f'{id}.zip'
        zip_path = os.path.join(config.cache_dir, key)
        s3_internal.download_file(S3Config.Buckets.problems, key, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip:
            with zip.open('quiz.json') as f:
                try:
                    main_json = json.loads(f.read())
                except json.JSONDecodeError:
                    return ReturnCode.ERR_QUIZ_JSON_DECODE
        return {**main_json, **ReturnCode.SUC_QUIZ_JSON_DECODE}
       
Quiz_Manager = QuizManager()