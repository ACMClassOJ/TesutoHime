from pathlib import PosixPath
from urllib.parse import urljoin

from boto3 import client as s3_client
from botocore.utils import determine_content_length
from botocore.client import ClientError
from botocore.config import Config
from commons.task_typing import SourceLocation
from commons.util import asyncrun

from scheduler2.config import s3_connection, task_timeout_secs

cfg = Config(signature_version='s3v4')
s3 = s3_client('s3', **s3_connection, config=cfg)

def construct_url (host: str, bucket: str, key: str) -> str:
    return urljoin(host, f'{bucket}/{key}')

def sign_url_get (bucket: str, key: str, args: dict = {}):
    return s3.generate_presigned_url('get_object', {
        'Bucket': bucket,
        'Key': key,
        **args,
    }, ExpiresIn=task_timeout_secs * 5)

def sign_url_put (bucket: str, key: str):
    return s3.generate_presigned_url('put_object', {
        'Bucket': bucket,
        'Key': key,
    }, ExpiresIn=task_timeout_secs * 5)


async def download (bucket: str, key: str, path: PosixPath):
    await asyncrun(lambda: s3.download_file(bucket, key, str(path)))

async def upload (bucket: str, key: str, file: PosixPath):
    await asyncrun(lambda: s3.upload_file(str(file), bucket, key))

async def copy_file (src: SourceLocation, bucket: str, key: str):
    src_dict = {
        'Bucket': src.bucket,
        'Key': src.key,
    }
    await asyncrun(lambda: s3.copy_object(Bucket=bucket, Key=key,
        CopySource=src_dict))

async def upload_str (bucket: str, key: str, fileobj):
    await asyncrun(lambda: s3.put_object(Bucket=bucket, Key=key, Body=fileobj))

async def upload_obj (bucket: str, key: str, fileobj):
    length = determine_content_length(fileobj)
    if length is None:
        raise Exception(f'Unable to determine length of file {key}')
    try:
        await asyncrun(lambda: s3.upload_fileobj(fileobj, bucket, key))
    except ClientError:
        raise

    # From https://github.com/boto/botocore/pull/1990#issuecomment-1171401468
    # HOTFIX: patch to close session after upload if file being uploaded is empty
    # We can remove this when this PR is merged to boto3:
    # https://github.com/boto/botocore/pull/1990
    if length == 0:
        s3._endpoint.http_session._manager.clear()


async def remove_file (bucket: str, key: str):
    await asyncrun(lambda: s3.delete_object(Bucket=bucket, Key=key))

async def read_file (bucket: str, key: str) -> str:
    return await asyncrun(lambda:
        s3.get_object(Bucket=bucket, Key=key)['Body'].read().decode())
