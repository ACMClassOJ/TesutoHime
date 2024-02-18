# Scripts

*此文档是对项目 scripts/ 目录下的部分实用工具的使用文档。这些工具目前仅能被服务器管理员使用。*

所有的文件均需要在 Web 服务器的项目根目录下执行。并保证设置了如下的环境变量 `DB`。(在生产环境中，这个环境变量已经写在了 `.bashrc` 中，无需手动设置。)

```sh
export DB='postgresql+psycopg2://ojweb@/oj'
```

## 目录

- [add_runner.py](#add_runnerpy): 向数据库中添加评测机;
- [db/init.py](#dbinitpy): 初始化数据库;

## add_runner.py

向数据库中添加评测机。

执行：

```sh
python3 -m scripts.add_runner
```

按照提示操作即可。

## db/init.py

初始化数据库。

执行：

```sh
python3 -m scripts.db.init
```

按照提示操作即可。
