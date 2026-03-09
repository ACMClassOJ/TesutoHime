from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from redis.asyncio import Redis

from commons.task_typing import ResourceUsage
from commons.util import RedisQueues


class ConfigRedisConnection(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=6379, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    db: int = Field(default=0, ge=0)


class ConfigRedis(BaseModel):
    prefix: str = "task:"
    connection: ConfigRedisConnection


class ConfigCache(BaseModel):
    max_age_secs: float = 86400.0
    clear_interval_secs: float = 86400.0


class ConfigTask(BaseModel):
    envp: list[str] = Field(
        default=[
            "PATH=/usr/bin:/bin",
            "CI=true",
            "CI_ENV=testing",
            "ONLINE_JUDGE=true",
            "ACMOJ=true",
        ]
    )
    exec_file_name: str = "code"
    timeout_secs: int = Field(default=3600, ge=1)
    heartbeat_interval_secs: float = Field(default=2.0, gt=0)
    poll_timeout_secs: int = Field(default=10, ge=1)


class ConfigGitSsh(BaseModel):
    private_key: str


class ConfigGit(BaseModel):
    ssh: ConfigGitSsh
    flags: list[str] = Field(
        default=[
            "--depth",
            "1",
            "--recurse-submodules",
            "--shallow-submodules",
            "--no-local",
        ]
    )
    exec_name: str = "code"


class ConfigCxx(BaseModel):
    flags: list[str] = Field(default=["-fmax-errors=10", "-O2", "-DONLINE_JUDGE", "-std=c++20"])
    file_name: str = "main.cpp"
    exec_name: str = "code"


class ConfigVerilog(BaseModel):
    file_name: str = "main.v"
    exec_name: str = "code"


class ConfigCompiler(BaseModel):
    cxx: ConfigCxx = Field(default_factory=ConfigCxx)
    verilog: ConfigVerilog = Field(default_factory=ConfigVerilog)
    git: ConfigGit | None = None


class ConfigValgrind(BaseModel):
    errexit_code: int = 250

    @property
    def args(self):
        return [
            "--tool=memcheck",
            "--leak-check=full",
            "--exit-on-first-error=yes",
            f"--error-exitcode={self.errexit_code}",
            "--quiet",
        ]


class ConfigChecker(BaseModel):
    cmp_limits: ResourceUsage = Field(
        default=ResourceUsage(
            time_msecs=10000,
            memory_bytes=1073741824,
            file_count=-1,
            file_size_bytes=-1,
        )
    )


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore", env_nested_delimiter="_", yaml_file=["runner.yml", "runner.yaml"]
    )

    runner_config: Literal["v3"]
    id: int | str
    group: str = "default"
    relative_slowness: float = Field(default=1.0, gt=0)
    working_dir: Path
    cache_dir: Path
    log_dir: Path
    worker_uid: int = Field(ge=0)
    redis: ConfigRedis
    cache: ConfigCache = Field(default_factory=ConfigCache)
    task: ConfigTask = Field(default_factory=ConfigTask)
    git: ConfigGit
    compiler: ConfigCompiler = Field(default_factory=ConfigCompiler)
    valgrind: ConfigValgrind = Field(default_factory=ConfigValgrind)
    checker: ConfigChecker = Field(default_factory=ConfigChecker)

    @property
    def queues(self) -> RedisQueues:
        runner_info = RedisQueues.RunnerInfo(str(self.id), self.group)
        return RedisQueues(self.redis.prefix, runner_info)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            YamlConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            init_settings,
            file_secret_settings,
        )


config: Config = Config()  # type: ignore

redis = Redis(
    host=config.redis.connection.host,
    port=config.redis.connection.port,
    username=config.redis.connection.username,
    password=config.redis.connection.password,
    db=config.redis.connection.db,
    decode_responses=True,
    health_check_interval=30,
    socket_connect_timeout=5,
    socket_keepalive=True,
)
