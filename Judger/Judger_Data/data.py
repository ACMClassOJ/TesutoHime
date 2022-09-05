from datetime import datetime
import os, shutil, zipfile, json, sys
import boto3
from botocore.exceptions import ClientError
from typing import Tuple

from config import DataConfig
from .ProblemConfig import *
from collections import namedtuple

s3 = boto3.client(
    's3',
    endpoint_url=DataConfig.server,
    aws_access_key_id=DataConfig.access_key,
    aws_secret_access_key=DataConfig.secret_key,
)

def get_data_from_server(id: int):
    zip_filename = str(id) + '.zip'
    dir_path = os.path.join(DataConfig.cache_dir, str(id))
    zip_path = os.path.join(DataConfig.cache_dir, zip_filename)

    try:
        stat = os.stat(dir_path)
        extras = {
            'IfModifiedSince': datetime.fromtimestamp(stat.st_mtime),
        }
    except FileNotFoundError:
        extras = {}

    try:
        obj = s3.get_object(
            Bucket=DataConfig.bucket,
            Key=zip_filename,
            **extras,
        )
    except ClientError as e:
        # 304 Not Modified
        if e.response['Error']['Code'] == '304':
            return
        raise

    with open(zip_path, 'wb') as f:
        for chunk in obj['Body'].iter_chunks():
            f.write(chunk)
    last_modified = obj['LastModified'].timestamp()

    shutil.rmtree(dir_path, ignore_errors=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        zip_file.extractall(dir_path)
    os.utime(dir_path, (last_modified, last_modified))
    os.remove(zip_path)

def get_data(id: int) -> Tuple[ProblemConfig, str]:
    try:
        get_data_from_server(id)
        dir_path = os.path.join(DataConfig.cache_dir, str(id))
        with open(os.path.join(dir_path, 'config.json')) as f:
            pconfig: ProblemConfig = json.load(f, object_hook=lambda x: namedtuple('X', x.keys())(*x.values()))
        return pconfig, dir_path
    except Exception as e:
        print(e, file=sys.stderr)
        raise
