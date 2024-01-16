# 从 MySQL 迁移到 PostgreSQL

## 备份数据

```sh
mariadb-dump oj > backup-mysql.sql
```

## 迁移 MySQL 到 4d92921b834b

```sh
alembic upgrade 4d92921b834b
```

## 安装 PostgreSQL

（假设操作系统为 Debian 或 Ubuntu）

```sh
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo tee /usr/share/keyrings/pgdg.asc > /dev/null
sudo sh -c 'echo "deb [signed-by=/usr/share/keyrings/pgdg.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
sudo apt-get update
sudo apt install postgresql
sudo systemctl enable --now postgresql
```

## 创建用户与数据库

使用 `sudo -u postgres psql` 打开一个 psql root shell，执行

```sql
-- 用户名与 Unix 用户名相同
CREATE USER "username";
CREATE DATABASE "acmoj" OWNER "username";
```

## 安装 psycopg2 driver

```sh
cd /path/to/TesutoHime
pip3 install -r web/requirements.txt
```

## 进行迁移

PostgreSQL 的连接 URL 为

```
postgresql+psycopg2://username@/dbname
```

进行迁移：

```sh
python3 -m scripts.db.mysql_to_pg.migrate
export DB='postgresql+psycopg2://acmoj@/acmoj'
alembic upgrade head
```

## 备份数据

```
pg_dump acmoj > backup-pg.sql
```

## 更改配置

web/config.py 中的数据库配置格式有变，参见 config_template.py

更改 .bashrc 中的 DB= 设置

## 关闭 MySQL

```sh
sudo systemctl disable --now mariadb
```
