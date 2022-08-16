from base64 import b64decode
from shutil import which

from nacl.public import PublicKey, PrivateKey, Box
from redis import StrictRedis
import yaml


def load_config () -> dict:
    with open('config.yml', 'r') as f:
        config = yaml.load(f, yaml.Loader)

    if not 'runner-config' in config:
        raise Exception('Config file is not valid runner config. Check your config.yml.')

    config_version = config['runner-config']
    program_version = 'v1'

    if config_version != program_version:
        raise Exception(f'config.yml has wrong version, has {config_version}, expecting {program_version}')

    return config

config = load_config()

runner_id: str = config['id']
relative_slowness: float = config['relative-slowness']
working_dir: str = config['working-dir']
cache_dir: str = config['cache-dir']
cache_max_age_secs = 86400.0
cache_clear_interval_secs = 86400.0
private_key = PrivateKey(b64decode(config['private-key'].encode()))
worker_uid = int(config['worker-uid'])

web_public_key = PublicKey(b64decode(config['web-server']['public-key'].encode()))
web_box = Box(private_key=private_key, public_key=web_public_key)
web_base_url: str = config['web-server']['base-url']
heartbeat_interval_secs = 2.0

queues = config['redis']['queues']
task_queue_key: str = queues['tasks']
in_progress_key: str = queues['in-progress']
signals_key: str = queues['signals']
poll_timeout_secs = 10.0
async def redis_connect ():
    from util import asyncrun
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
