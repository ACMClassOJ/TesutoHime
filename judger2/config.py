from shutil import which

from commons.task_typing import ResourceUsage
from commons.util import RedisQueues, load_config
from redis.asyncio import Redis

config = load_config('runner', 'v1')

runner_id: str = config['id']
relative_slowness: float = config['relative_slowness']
working_dir: str = config['working_dir']
cache_dir: str = config['cache_dir']
log_dir: str = config['log_dir']
cache_max_age_secs = 86400.0
cache_clear_interval_secs = 86400.0
worker_uid = int(config['worker_uid'])

heartbeat_interval_secs = 2.0
task_timeout_secs = 3600

queues = RedisQueues(config['redis']['prefix'], runner_id)
poll_timeout_secs = 10
redis = Redis(
    **config['redis']['connection'],
    decode_responses=True,
    health_check_interval=30,
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
cxxflags = ['-fmax-errors=10', '-O2', '-DONLINE_JUDGE', '-std=c++17']
cxx_file_name = 'main.cpp'
cxx_exec_name = exec_file_name

git_exec_name = exec_file_name
gitflags = ['--depth', '1', '--recurse-submodules', '--no-local']

verilog = which('iverilog')
verilog_file_name = 'main.v'
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

diff = which('diff')

checker_cmp_limits = ResourceUsage(
    time_msecs=10000,
    memory_bytes=1073741824,
    file_count=-1,
    file_size_bytes=-1,
)
