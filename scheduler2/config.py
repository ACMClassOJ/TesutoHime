from base64 import b64decode
from dataclasses import dataclass
from pathlib import PosixPath
from nacl.public import PublicKey, PrivateKey, Box
from redis import StrictRedis
from commons.task_typing import ResourceUsage

from commons.util import load_config

config = load_config('scheduler', 'v1')

working_dir = PosixPath(config['working_dir'])
cache_dir = PosixPath(config['cache_dir'])
log_dir = PosixPath(config['log_dir'])
private_key = PrivateKey(b64decode(config['private_key'].encode()))

s3_connection = config['s3']['connection']

@dataclass
class S3Buckets:
    problems: str
    submissions: str
    artifacts: str
s3_buckets = S3Buckets(**config['s3']['buckets'])

@dataclass
class S3Hosts:
    public: str
    internal: str
s3_hosts = S3Hosts(**config['s3']['hosts'])


problem_config_filename = 'config.json'

Secs = 1000
KiB = 1024
MiB = 1024 ** 2
GiB = 1024 ** 3
unlimited = -1

default_compile_limits = ResourceUsage(
    time_msecs=30 * Secs,
    memory_bytes=1 * GiB,
    file_count=unlimited,
    file_size_bytes=unlimited,
)

default_run_limits = ResourceUsage(
    time_msecs=1 * Secs,
    memory_bytes=512 * MiB,
    file_count=0,
    file_size_bytes=0,
)

default_check_limits = ResourceUsage(
    time_msecs=10 * Secs,
    memory_bytes=1 * GiB,
    file_count=unlimited,
    file_size_bytes=unlimited,
)
