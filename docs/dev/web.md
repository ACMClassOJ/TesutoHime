# Web 模块

*此文档只会介绍 web 中各部分的功能，但不会介绍具体细节。如需了解具体细节，请查看源代码及其中的注释。*

Web 模块相关代码位于 [`web/`](../../web/) 目录下。本文档中，除非特殊说明，否则所有涉及的文件都以 `web` 目录为基础。

Web 模块负责处理所有用户操作，包括查看数据、修改个人资料、上传数据、提交代码等操作。

用户数据、题面数据、提交数据、比赛数据等均储存在 PostgreSQL 数据库中（参见 [PostgreSQL 数据库](#postgresql-数据库)章节），并由 Web 模块管理。

Web 模块使用 [Flask](https://flask.palletsprojects.com/) 渲染网页、处理 HTTP 请求。

Web 模块使用 [Redis](https://redis.io/) 缓存数据、中转数据，关于具体内容，参见 [Redis 文档](redis.md)。

关于如何修改数据库，请参阅[修改数据库](#修改数据库)章节。

## HTTP 请求处理

*如需了解更多细节，请参阅 [Flask](https://flask.palletsprojects.com/) 文档。*

每个请求均会调用相应的函数（由函数前的修饰器指定，如 `@web.route('/index.html')` 表示对 `/OnlineJudge/index.html` 的请求）。

`web.py` 负责处理所有除 `/admin` 及其子页面以外的请求；`admin.py` 负责处理所有 `/admin` 及其子页面的请求。

## 页面渲染及模板

所有页面的渲染均由 `render_template` 函数 (`templating.py`) 完成。此函数会将 `web/templates/` 目录下的模板文件按照特定规则渲染出来。关于渲染规则，请参阅 Flask 文档中的 [Rendering Templates 部分](https://flask.palletsprojects.com/en/2.2.x/quickstart/#rendering-templates)。

另请注意，`web/templates/` 目录下的模板文件与网页的 URL 无关，而是由 `render_template` 函数的第一个参数决定。

## 用户文档生成

更改 `docs/user` 下的文档后，需要手动运行 `make user-docs` 生成 HTML 格式的用户文档。这一过程需要安装 Pandoc 工具。

## 前端日志记录

除了静态内容（如图片、CSS、JS 等）和发送的心跳包以外，所有前端请求均会被记录，`config.py` 文件下 `LogConfig` 类中的配置决定日志记录的方式、位置。

## 登录管理

登录管理由 `session_manager.py` 负责，可以提供真实登录状态、用户名、昵称、权限，及新增登录用户。登录状态数据由 Redis 管理，Redis 数据库中前缀包含 `session_` 的键均为登录状态。数据库中的数据的有效时间为 14 天。

## 用户数据管理

用户数据由 `user_manager.py` 负责。其可以创建用户、修改用户、删除用户、修改用户密码、获取用户数据、获取用户列表。用户数据由 PostgreSQL 管理（参见 PostgreSQL 数据库的[用户数据表](#account-表)章节）。

在用户数据管理中，用户名 (`username`) 是唯一且不变的。

### 用户密码

为尽可能确保用户密码安全，用户密码将会加上一个随机生成的 salt，然后使用 Argon2 算法加密。加密后的密码将会存储在数据库中。

### 用户权限

用户权限共有 3 种，

- `0`: 普通用户，可以修改自己的个人资料、提交代码、查看比赛数据等，不可以修改他人的个人资料、查看他人的非公开提交；
- `1`: 管理员，除普通用户的权限外，可以查看所有提交、创建比赛、修改比赛、删除比赛、新增题目、修改题目数据、删除题目，但不能修改他人的个人资料；
- `2`: 超级管理员，除管理员权限外，可以修改他人的个人资料。

### 实名数据管理

实名数据由 `realname_manager.py` 负责。其可以修改实名、获取实名数据。实名数据由 PostgreSQL 管理（参见 PostgreSQL 数据库的[实名数据表](#realname_reference-表)章节）。

## 比赛数据管理

比赛数据（这里比赛是广泛意义上的比赛，作业、考试、比赛都包含在内）由 `contest_manager.py` 负责。其可以创建比赛、修改比赛、删除比赛、修改参赛用户、获取比赛数据、获取比赛列表。比赛数据由 PostgreSQL 管理（参见 PostgreSQL 数据库的[比赛数据表](#contest-表)、[比赛题目表](#contest_problem-表)、[比赛用户表](#contest_player-表)章节）。

### 比赛类型

比赛类型共有 3 种，

- `0`: 比赛，统计每题得分及罚时，并据此排序；
- `1`: 作业，仅统计通过和不通过的提交；
- `2`: 考试，同一时刻非管理员用户只能报名同一场考试，在考试结束前暂时无法加入新的作业、比赛或考试，考试时非管理员用户只能查看自己在考试题目上的提交。

### 比赛数据缓存

比赛数据缓存由 `contest_cache.py` 负责，以前缀 `ranking-{type}-{id}` 存入 Redis 数据库，此缓存数据有效时间为 14s。

## 讨论数据管理

讨论数据由 `discuss_manager.py` 负责。其可以创建讨论、修改讨论、删除讨论、获取讨论数据。讨论数据由 PostgreSQL 管理（参见 PostgreSQL 数据库的[讨论数据表](#discussion-表)章节）。

## 题目数据管理

题目数据由 `problem_manager.py` 负责。其可以创建题目、修改题目、删除题目、获取题目数据、获取题目列表。题目数据中与题面相关的部分由 PostgreSQL 管理（参见 PostgreSQL 数据库的[题目数据表](#problem-表)章节）。题目数据中的数据包由 S3 服务管理，具体参见 [S3 服务](S3.md)文档。

此外，`QuizManager.py` 可以从 S3 服务上获取 json 数据。

当数据包有更新（或首次上传）时，此信息将会通过网络的形式传给 [Scheduler2 模块](scheduler2.md)。

关于数据包的格式，参见用户文档中的[数据包格式](../user/data_doc.md)。

## 评测数据管理

评测数据由 `judge_manager.py` 负责，其可以查询提交、为尚未评测的提交交给 [Scheduler2 模块](scheduler2.md)排程、中止 (abort) 评测、将评测标记为无效 (voided)、重新评测提交。数据参见 PostgreSQL 数据库的[评测数据表](#judge_record_v2-表)章节。

旧版评测数据由 `old_judge_manager.py` 负责。由于架构的不兼容性，目前仅可以查询提交，数据视为只读（数据参见 PostgreSQL 数据库的[旧评测数据表](#judge_record_v1-表)章节）。

## PostgreSQL 数据库

### 修改数据库

如需修改数据库，请先修改 `models.py`，然后执行（请将 message 替换为此次更新的描述）

```sh
alembic revision --autogenerate -m "message"
```

alembic 会自动对比数据库内容和当前 model 的差异，生成 migration script。

关于将修改应用到数据库，请参阅迁移文档的 [Web#迁移数据库](../migration/web.md#数据库迁移)部分。

### account 表

这个表本来应该叫 user，但是 pg 里 user 是关键字，就换了个名字。

*另请参见[用户数据管理](#用户数据管理)章节。*

- `id`: 用户 ID；
- `username`: 用户名；
- `student_id`: 学号；
- `friendly_name`: 昵称；
- `password`: 密码；
- `privilege`: 用户权限。

### realname_reference 表

*另请参见[实名数据管理](#实名数据管理)章节。*

- `id`: 条目 id；
- `student_id`: 学号；
- `real_name`: 实名。

### contest 表

比赛、考试和作业都是一种 contest。

*另请参见[比赛数据管理](#比赛数据管理)章节。*

- `id`: 比赛 id；
- `name`: 比赛名称；
- `start_time`: 比赛开始时间；
- `end_time`: 比赛结束时间；
- `type`: 比赛类型；
- `ranked`: 是否显示排名；
- `rank_penalty`: 是否计算罚时；
- `rank_partial_score`: 是否计算部分分。

### contest_problem 表

*另请参见[比赛数据管理](#比赛数据管理)章节。*

- `id`: 条目 id；
- `contest_id`: 题目所属比赛 id；
- `problem_id`: 题目 id。

### contest_player 表

*另请参见[比赛数据管理](#比赛数据管理)章节。*

- `id`: 条目 id；
- `contest_id`: 用户所属比赛 id；
- `username`: 用户名。

### discussion 表

*另请参见[讨论数据管理](#讨论数据管理)章节。*

- `id`: 讨论 id；
- `problem_id`: 题目 id；
- `username`: 用户名；
- `data`: 讨论内容；

### problem 表

*另请参见[题目数据管理](#题目数据管理)章节。*

- `id`: 题目 id；
- `title`: 题目标题；
- `description`: 题目描述；
- `input`: 输入格式；
- `output`: 输出格式；
- `example_input`: 样例输入；
- `example_output`: 样例输出；
- `data_range`: 数据范围；
- `release_time`: 发布时间；
- `problem_type`: 题目类型；
- `limits`: 时空限制。

### judge_record_v1 表

*在 Judger2 架构下，judge_record_v1 表是只读的，仅用于记录过去的提交数据。*

*另请参见[评测数据管理](#题目数据管理)章节。*

- `id`: 提交 id；
- `code`: 提交代码；
- `user`: 提交用户；
- `problem_id`: 提交题目；
- `language`: 提交语言；
- `status`: 评测状态；
- `score`: 评测得分；
- `time`: 提交时间；
- `time_msecs`: 评测耗时；
- `memory_kbytes`: 评测内存占用；
- `detail`: 评测详情；
- `public`: 是否公开。

### judge_record_v2 表

*另请参见[评测数据管理](#题目数据管理)章节。*

- `id`: 提交 ID；
- `public`: 是否公开；
- `language`: 提交语言；
- `username`: 提交用户；
- `problem_id`: 提交题目；
- `status`: 评测状态；
- `score`: 评测得分；
- `message`: 评测详情信息；
- `details`: 评测详情；
- `time_msecs`: 评测耗时 (ms)；
- `memory_bytes`: 评测内存占用 (bytes)。

### judge_runner_v2 表

- `id`: 评测机 ID；
- `name`: 评测机名称；
- `hardware`: 评测机硬件信息；
- `provider`: 评测机提供者；
- `visible`: 是否显示在关于页上。

### judge_server_v1 表（弃用）

- `id`: 评测机 id；
- `address`: 评测机 ip 地址；
- `secret_key`: 评测机密钥；
- `last_seen_time`: 最后一次心跳时间；
- `busy`: 评测机是否正在评测；
- `current_task`: 评测机正在评测的提交 id；
- `friendly_name`: 评测机名称；
- `detail`: 评测机硬件信息。

### alembic_version 表

- `version_num`: 版本号，用于记录数据库格式的版本。

## Web 与 Frontend 接口说明

- data 数组的第一维代表一个参赛用户，从 0 开始。
- data[i]['score'] 存储第 i 个用户的总得分。
- data[i]['penalty'] 存储第 i 个用户的总罚时。
- data[i]['ac_count'] 存储第 i 个用户的 AC 数量。
- data[i]['friendly_name'] 存储第 i 个用户的昵称。
- data[i]['problems'] 存储第 i 个用户各题的提交与通过情况。其中，
  - data[i]['problems'][j]['score'] 存储第 j 道题的得分。
  - data[i]['problems'][j]['count'] 存储第 j 道题的提交次数。
  - data[i]['problems'][j]['accepted'] 存储第 j 道题通过与否。
- data[i]['realname'] 存储第 i 个用户的真实姓名（Realname reference）。
- data[i]['student_id'] 存储第 i 个用户的学号。
- data[i]['username'] 存储第 i 个用户的用户名。
