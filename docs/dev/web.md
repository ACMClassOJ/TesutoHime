# Web 模块

*此文档只会介绍 web 中各部分的功能，但不会介绍具体细节。如需了解具体细节，请查看源代码及其中的注释。*

Web 模块相关代码位于 [`web/`](../../web/) 目录下。本文档中，除非特殊说明，否则所有涉及的文件都以 `web` 目录为基础。

Web 模块负责处理所有用户操作，包括查看数据、修改个人资料、上传数据、提交代码等操作。

用户数据、题面数据、提交数据、比赛数据等均储存在 MySQL 数据库中（参见 [MySQL 数据库](#mysql-数据库)章节），并由 Web 模块管理。

Web 模块使用 [Flask](https://flask.palletsprojects.com/) 渲染网页、处理 HTTP 请求。

Web 模块使用 [Redis](https://redis.io/) 缓存数据、中转数据，关于具体内容，参见 [Redis 文档](redis.md)。

## HTTP 请求处理

*如需了解更多细节，请参阅 [Flask](https://flask.palletsprojects.com/) 文档。*

每个请求均会调用相应的函数（由函数前的修饰器指定，如 `@web.route('/index.html')` 表示对 `/OnlineJudge/index.html` 的请求）。

`web.py` 负责处理所有除 `/admin` 及其子页面以外的请求；`admin.py` 负责处理所有 `/admin` 及其子页面以外的请求。

## 页面渲染及模板

所有页面的渲染均由 `render_template` 函数 (`templating.py`) 完成。此函数会将 `web/templates/` 目录下的模板文件按照特定规则渲染出来。关于渲染规则，请参阅 Flask 文档中的 [Rendering Templates 部分](https://flask.palletsprojects.com/en/2.2.x/quickstart/#rendering-templates)。

另请注意，`web/templates/` 目录下的模板文件与网页的 URL 无关，而是由 `render_template` 函数的第一个参数决定。

## 前端日志记录

除了静态内容（如图片、CSS、JS 等）和发送的心跳包以外，所有前端请求均会被记录，`config.py` 文件下 `LogConfig` 类中的配置决定日志记录的方式、位置。

## 登录管理

登录管理由 `session_manager.py` 负责，可以提供真实登录状态、用户名、昵称、权限，及新增登录用户。登录状态数据由 Redis 管理，Redis 数据库中前缀包含 `session_` 的键均为登录状态。数据库中的数据的有效时间为 14 天。

## 用户数据管理

用户数据由 `user_manager.py` 负责。其可以创建用户、修改用户、删除用户、修改用户密码、获取用户数据、获取用户列表。用户数据由 mysql 管理（参见 MySQL 数据库的[用户数据表](#user-表)章节）。

在用户数据管理中，用户名 (`Username`) 是唯一且不变的。

### 用户密码

为尽可能确保用户密码安全，用户密码将会加上一个随机生成的 salt，然后使用 `SHA-512` 算法加密。加密后的密码将会存储在数据库中。

### 用户权限

用户权限共有 3 中，

- `0`: 普通用户，可以修改自己的个人资料、提交代码、查看比赛数据等，不可以修改他人的个人资料、查看他人的非公开提交；
- `1`: 管理员，除普通用户的权限外，可以查看所有提交、创建比赛、修改比赛、删除比赛、新增题目、修改题目数据、删除题目，但不能修改他人的个人资料；
- `2`: 超级管理员，除管理员权限外，可以修改他人的个人资料。

### 实名数据管理

实名数据由 `reference_manager.py` 负责。其可以修改实名、获取实名数据。实名数据由 MySQL 管理（参见 MySQL 数据库的[实名数据表](#realname_reference-表)章节）。

## 比赛数据管理

比赛数据（这里比赛是广泛意义上的比赛，作业、考试、比赛都包含在内）由 `contest_manager.py` 负责。其可以创建比赛、修改比赛、删除比赛、修改参赛用户、获取比赛数据、获取比赛列表。比赛数据由 MySQL 管理（参见 MySQL 数据库的[比赛数据表](#contest-表)、[比赛题目表](#contest_problem-表)、[比赛用户表](#contest_player-表)章节）。

### 比赛类型

比赛类型共有 3 种，

- `0`: 比赛，统计每题得分及罚时，并据此排序；
- `1`: 作业，仅统计通过和不通过的提交；
- `2`: 考试，同一时刻非管理员用户只能报名同一场考试，在考试结束前暂时无法加入新的作业、比赛或考试，考试时非管理员用户只能查看自己在考试题目上的提交。

### 比赛数据缓存

比赛数据缓存由 `contest_cache.py` 负责，以前缀 `ranking-{type}-{id}` 存入 Redis 数据库，此缓存数据有效时间为 14s。

## 讨论数据管理

讨论数据由 `discuss_manager.py` 负责。其可以创建讨论、修改讨论、删除讨论、获取讨论数据。讨论数据由 MySQL 管理（参见 MySQL 数据库的[讨论数据表](#discussion-表)章节）。

## 题目数据管理

题目数据由 `problem_manager.py` 负责。其可以创建题目、修改题目、删除题目、获取题目数据、获取题目列表。题目数据中与题面相关的部分由 MySQL 管理（参见 MySQL 数据库的[题目数据表](#problem-表)章节）。题目数据中的数据包由 S3 服务管理，具体参见 [S3 服务](S3.md)文档。

此外，`QuizManager.py` 可以从 S3 服务上获取 json 数据。

当数据包有更新（或首次上传）时，此信息将会通过网络的形式传给 [Scheduler2 模块](scheduler2.md)。

关于数据包的格式，参见用户文档中的[数据包格式](../user/data_doc.md)。

## 评测数据管理

评测数据由 `judge_manager.py` 负责，其可以查询提交、为尚未评测的提交交给 [Scheduler2 模块](scheduler2.md)排程、中止 (abort) 评测、将评测标记为无效 (voided)、重新评测提交。数据参见 MySQL 数据库的[评测数据表](#judge_records2-表)章节。

旧版评测数据由 `old_judge_manager.py` 负责。由于架构的不兼容性，目前仅可以查询提交，数据视为只读（数据参见 MySQL 数据库的[旧评测数据表](#judge-表)章节）。

## MySQL 数据库

### User 表

*另请参见[用户数据管理](#用户数据管理)章节。*

- `tempID`: 用户 ID；
- `Username`: 用户名；
- `Friendly_Name`: 昵称；
- `Password`: 密码；
- `Salt`: 密码 salt；
- `Privilege`: 用户权限。

### Realname_Reference 表

*另请参见[实名数据管理](#实名数据管理)章节。*

- `ID`: 条目 ID；
- `Student_ID`: 学号；
- `Real_Name`: 实名。

### Contest 表

*另请参见[比赛数据管理](#比赛数据管理)章节。*

- `ID`: 比赛 ID；
- `Name`: 比赛名称；
- `Start_Time`: 比赛开始时间；
- `End_Time`: 比赛结束时间；
- `type`: 比赛类型。

### Contest_Problem 表

*另请参见[比赛数据管理](#比赛数据管理)章节。*

- `tempID`: 条目 ID；
- `Belong`: 题目所属比赛 ID；
- `Problem_ID`: 题目 ID。

### Contest_Player 表

*另请参见[比赛数据管理](#比赛数据管理)章节。*

- `tempID`: 条目 ID；
- `Belong`: 用户所属比赛 ID；
- `Username`: 用户名。

### Discussion 表

*另请参见[讨论数据管理](#讨论数据管理)章节。*

- `ID`: 讨论 ID；
- `Problem_ID`: 题目 ID；
- `Username`: 用户名；
- `Data`: 讨论内容；
- `Time`: 发布时间。

### Problem 表

*另请参见[题目数据管理](#题目数据管理)章节。*

- `ID`: 题目 ID；
- `Title`: 题目标题；
- `Description`: 题目描述；
- `Input`: 输入格式；
- `Output`: 输出格式；
- `Example_Input`: 样例输入；
- `Example_Output`: 样例输出；
- `Date_Range`: 数据范围；
- `Release_Time`: 发布时间；
- `Problem_Type`: 题目类型；
- `Limit`: 时空限制。

### Judge 表

*在 Judger2 架构下，Judge 表是只读的，仅用于记录过去的提交数据。*

*另请参见[评测数据管理](#题目数据管理)章节。*

- `ID`: 提交 ID；
- `Code`: 提交代码；
- `User`: 提交用户；
- `Problem_ID`: 提交题目；
- `Language`: 提交语言；
- `Status`: 评测状态；
- `Score`: 评测得分；
- `Time`: 提交时间；
- `Time_Used`: 评测耗时；
- `Memory_Used`: 评测内存占用；
- `Detail`: 评测详情；
- `Share`: 是否公开。

### judge_records2 表

*另请参见[评测数据管理](#题目数据管理)章节。*

- `id`: 提交 ID；
- `public`: 是否公开；
- `language`: 提交语言；
- `created`: 提交时间；
- `username`: 提交用户；
- `problem_id`: 提交题目；
- `status`: 评测状态；
- `score`: 评测得分；
- `message`: 评测详情信息；
- `details`: 评测详情；
- `time_msec`: 评测耗时 (ms)；
- `memory_bytes`: 评测内存占用 (bytes)。

### judge_runners2 表

- `id`: 评测机 ID；
- `name`: 评测机名称；
- `hardware`: 评测机硬件信息；
- `provider`: 评测机提供者。

### Judge_Server 表（弃用）

- `ID`: 评测机 ID；
- `Address`: 评测机 IP 地址；
- `Secret_Key`: 评测机密钥；
- `Last_Seen_Time`: 最后一次心跳时间；
- `Busy`: 评测机是否正在评测；
- `Current_Task`: 评测机正在评测的提交 ID；
- `Friendly_Name`: 评测机名称；
- `Detail`: 评测机硬件信息。

### version 表

- `version`: 版本号，用于记录数据库格式的版本。

## Web 与 Frontend 接口说明

### contest.html

- data 数组的第一维代表一个参赛用户，从 0 开始。
- data[i]['score']存储第 i 个用户的总得分。
- data[i]['penalty']存储第 i 个用户的总罚时。
- data[i]['friendly_name']存储第 i 个用户的昵称。
- data[i]['problems'] 存储第 i 个用户各题的提交与通过情况。其中，
  - data[i]['problems'][j]['score'] 存储第 j 道题的得分。
  - data[i]['problems'][j]['count'] 存储第 j 道题的提交次数。
  - data[i]['problems'][j]['accepted'] 存储第 j 道题通过与否。
- data[i]['realname'] 存储第 i 个用户的真实姓名（Realname reference）。
- data[i]['student_id'] 存储第 i 个用户的学号。
- data[i]['username'] 存储第 i 个用户的用户名。

### homework.html

- data 数组的第一维代表一个参赛用户，从 0 开始。
- data[i]['ac_count']存储第 i 个用户的 AC 数量。
- data[i]['friendly_name']存储第 i 个用户的昵称。
- data[i]['problems'] 存储第 i 个用户各题的提交与通过情况。其中，
  - data[i]['problems'][j]['accepted'] 存储第 j 道题通过与否。
  - data[i]['problems'][j]['count'] 存储第 j 道题的提交次数。
- data[i]['realname'] 存储第 i 个用户的真实姓名（Realname reference）。
- data[i]['student_id'] 存储第 i 个用户的学号。
- data[i]['username'] 存储第 i 个用户的用户名。
