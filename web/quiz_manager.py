import json
import os
import zipfile

from web.config import S3Config
from web.const import ReturnCode
from web.utils import s3_internal


class QuizManager:
    @staticmethod
    def get_json_from_data_service_by_id(config, id: int):
        key = f'{id}.zip'
        zip_path = os.path.join(config.cache_dir, key)
        s3_internal.download_file(S3Config.Buckets.problems, key, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip:
            with zip.open(f'{id}/quiz.json') as f:
                try:
                    main_json = json.loads(f.read())
                except json.JSONDecodeError:
                    return ReturnCode.ERR_QUIZ_JSON_DECODE
        return {**main_json, **ReturnCode.SUC_QUIZ_JSON_DECODE}
