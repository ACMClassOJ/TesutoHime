# 将 Web 模块迁移到新版本

## 更新/安装依赖

使用 `pip3` 更新/安装依赖

```sh
pip3 install -r web/requirements.txt
```

## 数据库迁移

数据库目前采用 [SQLAlchemy](https://www.sqlalchemy.org/) 进行管理，因此可以使用
SQLAlchemy 官方提供的工具 alembic 进行数据库迁移。

执行以下命令以升级数据库：

```sh
alembic upgrade head
```
