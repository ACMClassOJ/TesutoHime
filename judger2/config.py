from base64 import b64decode
from shutil import which

from nacl.public import PublicKey, PrivateKey, Box
from redis import StrictRedis

from commons.config import load_config
from commons.task_typing import ResourceUsage

config = load_config('runner', 'v1')

runner_id: str = config['id']
relative_slowness: float = config['relative_slowness']
working_dir: str = config['working_dir']
cache_dir: str = config['cache_dir']
log_dir: str = config['log_dir']
cache_max_age_secs = 86400.0
cache_clear_interval_secs = 86400.0
private_key = PrivateKey(b64decode(config['private_key'].encode()))
worker_uid = int(config['worker_uid'])

web_public_key = PublicKey(b64decode(config['web_server']['public_key'].encode()))
web_box = Box(private_key=private_key, public_key=web_public_key)
web_base_url: str = config['web_server']['base_url']
heartbeat_interval_secs = 2.0

queues = config['redis']['queues']
task_queue_key: str = queues['tasks']
in_progress_key: str = queues['in_progress']
signals_key: str = queues['signals']
poll_timeout_secs = 10.0
async def redis_connect ():
    from judger2.util import asyncrun
    return await asyncrun(lambda:
        StrictRedis(**config['redis']['connection'], decode_responses=True)
    )

# env vars for task runner
task_envp = [
    'PATH=/usr/bin:/bin',
    'CI=true',
    'CI_ENV=testing',
    'ONLINE_JUDGE=true',
    'ACMOJ=true',
]

exec_file_name = 'code'

cxx = which('g++')
cxxflags = ['-fmaxerrors=10', '-O2', '-DONLINE_JUDGE', '-std=c++17']
cxx_file_name = 'code.cpp'
cxx_exec_name = exec_file_name

git_exec_name = exec_file_name

verilog = which('iverilog')
verilog_file_name = 'answer.v'
verilog_exec_name = exec_file_name
verilog_interpreter = which('vvp')

valgrind = which('valgrind')
valgrind_errexit_code = 250
valgrind_args = [
    '--tool=memcheck',
    '--leak-check=full',
    '--exit-on-first-error=yes',
    f'--error-exitcode={valgrind_errexit_code}',
    '--quiet',
]

checker_cmp_limits = ResourceUsage(
    time_msecs=10000,
    memory_bytes=67108864,
    file_count=-1,
    file_size_bytes=-1,
)
