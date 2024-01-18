from dataclasses import dataclass
from pathlib import PosixPath

from commons.task_typing import ResourceUsage
from commons.util import RedisQueues, load_config
from redis.asyncio import Redis

config = load_config('scheduler', 'v2')

working_dir = PosixPath(config['working_dir'])
cache_dir = PosixPath(config['cache_dir'])
log_dir = PosixPath(config['log_dir'])

host = config['host']
port = int(config['port'])
web_base_url = config['web']['base_url']
web_auth = config['web']['auth']

s3_connection = config['s3']['connection']

@dataclass
class S3Buckets:
    problems: str
    artifacts: str
s3_buckets = S3Buckets(**config['s3']['buckets'])


def plan_key(problem_id: str) -> str:
    return f'plans/{problem_id}.json'


problem_config_filename = 'config.json'
quiz_filename = 'quiz.json'

redis_queues = RedisQueues(config['redis']['prefix'])
redis = Redis(
    **config['redis']['connection'],
    decode_responses=True,
    health_check_interval=30,
    socket_connect_timeout=5,
    socket_keepalive=True,
)


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
    file_count=unlimited,
    file_size_bytes=0,
)

default_check_limits = ResourceUsage(
    time_msecs=10 * Secs,
    memory_bytes=1 * GiB,
    file_count=unlimited,
    file_size_bytes=unlimited,
)

task_timeout_secs = 3600 # 1 hour
task_retries = 3
task_retry_interval_secs = 10
task_concurrency_per_account = 4

request_retries = 10
request_retry_interval_secs = 2

runner_heartbeat_interval_secs = 2.0
