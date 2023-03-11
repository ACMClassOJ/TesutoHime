### 建立数据库

数据库名称为OJ，root密码为Progynova。

```sql
UPDATE mysql.user SET authentication_string = PASSWORD ("Progynova") WHERE User = "root" AND Host="localhost";
UPDATE mysql.user SET plugin='mysql_native_password' WHERE user='root';
FLUSH PRIVILEGES;

CREATE DATABASE OJ;
USE OJ;
```

Create User:

```sql
CREATE USER 'oj'@'localhost' IDENTIFIED BY 'Progynova';
GRANT ALL PRIVILEGES ON database_name.* TO 'oj'@'localhost';
```

### 数据表格式：

#### Problem:

* ID: INT, auto_increment, PRIMARY KEY
* Title: TEXT
* Description: TEXT
* Input: TEXT
* Output: TEXT
* Example_Input: TEXT
* Example_Output: TEXT
* Data_Range: TEXT
* Release_Time: BIGINT // unix nano
* Flag_Count: INT DEFAULT 0// 在比赛或作业中的次数
* Problem_Type: INT DEFAULT 0 NOT NULL // 题目类型，0为代码，1为填选

```sql
CREATE TABLE Problem(ID INT NOT NULL AUTO_INCREMENT, Title TEXT, Description TEXT, Input Text, Output Text, Example_Input Text, Example_Output Text, Data_Range Text, Release_Time BIGINT, Flag_Count INT DEFAULT 0, PRIMARY KEY(ID))ENGINE=InnoDB AUTO_INCREMENT=1000 DEFAULT CHARSET=utf8mb4;
```

#### User:

* tempID auto_increment, PRIMARY KEY
* Username: VARCHAR(20), UNIQUE
* Student_ID: BIGINT
* Friendly_Name: TINYTEXT
* Password: TINYTEXT // sha-512 with salt
* Salt: INT
* Privilege: INT // 0: Normal User, 1: Admin(Normal User + Problem Edit), 2: Super(Problem Editor + User Modify + Judge Server Manually Add/Delete);

```sql
CREATE TABLE User(tempID INT NOT NULL AUTO_INCREMENT, Username VARCHAR(20), Student_ID BIGINT, Friendly_Name TINYTEXT, Password TINYTEXT, Salt INT, Privilege INT, PRIMARY KEY(tempID), UNIQUE KEY(Username))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Judge:

* ID: INT, auto_increment, PRIMARY KEY
* Code: MEDIUMTEXT
* User: TINYTEXT
* Problem_ID: INT
* Language: INT // 0 for C++, 1 for git, 2 for python3(Not Supported Yet)
* Status: INT // (Waiting, Running, AC、WA、CE、RE、TLE、MLE、Memory Leak、System Error)
* Score: INT DEFAULT -1
* Time: BIGINT // unix nano
* Time_Used: INT DEFAULT -1// ms
* Mem_Used: INT DEFAULT -1// Byte
* Detail: MEDIUMTEXT // may exceed 64 KB
* Share: BOOLEAN Default False

```sql
CREATE TABLE Judge(ID INT NOT NULL AUTO_INCREMENT, Code MEDIUMTEXT, User TINYTEXT, Problem_ID INT, Language INT, Status INT, Score INT DEFAULT -1, Time BIGINT, Time_Used INT DEFAULT -1, Mem_Used INT DEFAULT -1, Detail MEDIUMTEXT, PRIMARY KEY(ID), Share BOOLEAN DEFAULT FALSE)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Contest:

* ID: INT, auto_increment, PRIMARY KEY
* Name TINYTEXT
* Start_Time: BIGINT // unix nano
* End_Time: BIGINT // unix nano
* Type: INT // 0 for Contest and 1 for Homework

```sql
CREATE TABLE Contest(ID INT NOT NULL AUTO_INCREMENT, Name TINYTEXT, Start_Time BIGINT, End_Time BIGINT, Type INT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Contest_Problem:

* tempID: INT, auto_increment, PRIMARY KEY // useless
* Belong: INT // Contest it belongs to
* Problem_ID: INT

```sql
CREATE TABLE Contest_Problem(tempID INT NOT NULL AUTO_INCREMENT, Belong INT, Problem_ID INT, PRIMARY KEY(tempID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Contest_Player:

* tempID: INT, auto_increment, PRIMARY KEY // useless
* Belong: INT // Contest it belongs to
* Username: TINYTEXT // User

如何查询比赛中提交？比赛->用户+题目->组合查提交(反正mysql非常快对不对)

```sql
CREATE TABLE Contest_Player(tempID INT NOT NULL AUTO_INCREMENT, Belong INT, Username TINYTEXT, PRIMARY KEY(tempID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Discuss:

* ID: INT, auto_increment, PRIMARY KEY
* Problem_ID: INT
* Username: TINYTEXT
* Data: TEXT
* Time: BIGINT

```sql
CREATE TABLE Discuss(ID INT NOT NULL AUTO_INCREMENT, Problem_ID INT, Username TINYTEXT, Data Text, Time BIGINT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Judge_Server

* ID: INT, auto_increment, PRIMARY KEY
* Address: TINYTEXT
* Secret_Key: TINYTEXT // uuid4
* Last_Seen_Time: BIGINT 0
* Busy: BOOLEAN 0
* Current_Task: INT
* Friendly_Name: TINYTEXT
* Detail: TINYTEXT([CPU]\n[Provider])

```sql
CREATE TABLE Judge_Server(ID INT NOT NULL AUTO_INCREMENT, Address TINYTEXT, Secret_Key TINYTEXT, Last_Seen_Time BIGINT DEFAULT 0, Busy BOOLEAN DEFAULT FALSE, Current_Task INT DEFAULT -1, Friendly_Name TINYTEXT, Detail TINYTEXT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### Realname_Reference

* ID: INT, auto_increment, PRIMARY KEY
* Student_ID: TINYTEXT
* Real_Name: TINYTEXT

```sql
CREATE TABLE Realname_Reference(ID INT NOT NULL AUTO_INCREMENT, Student_ID TINYTEXT, Real_Name TINYTEXT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

```sql
UPDATE mysql.user SET authentication_string = PASSWORD ("Progynova") WHERE User = "root" AND Host="localhost";
UPDATE mysql.user SET plugin='mysql_native_password' WHERE user='root';
FLUSH PRIVILEGES;

CREATE DATABASE OJ;
USE OJ;

CREATE TABLE Problem(ID INT NOT NULL AUTO_INCREMENT, Title TEXT, Description TEXT, Input Text, Output Text, Example_Input Text, Example_Output Text, Data_Range Text, Release_Time BIGINT, Flag_Count INT DEFAULT 0, PRIMARY KEY(ID))ENGINE=InnoDB AUTO_INCREMENT=1000 DEFAULT CHARSET=utf8mb4;
CREATE TABLE User(tempID INT NOT NULL AUTO_INCREMENT, Username VARCHAR(20), Student_ID BIGINT, Friendly_Name TINYTEXT, Password TINYTEXT, Salt INT, Privilege INT, PRIMARY KEY(tempID), UNIQUE KEY(Username))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Judge(ID INT NOT NULL AUTO_INCREMENT, Code TEXT, User TINYTEXT, Problem_ID INT, Language INT, Status INT, Score INT DEFAULT -1, Time BIGINT, Time_Used INT DEFAULT -1, Mem_Used INT DEFAULT -1, Detail MEDIUMTEXT, PRIMARY KEY(ID), Share BOOLEAN DEFAULT FALSE)ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Contest(ID INT NOT NULL AUTO_INCREMENT, Name TINYTEXT, Start_Time BIGINT, End_Time BIGINT, Type INT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Contest_Problem(tempID INT NOT NULL AUTO_INCREMENT, Belong INT, Problem_ID INT, PRIMARY KEY(tempID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Contest_Player(tempID INT NOT NULL AUTO_INCREMENT, Belong INT, Username TINYTEXT, PRIMARY KEY(tempID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Discuss(ID INT NOT NULL AUTO_INCREMENT, Problem_ID INT, Username TINYTEXT, Data Text, Time BIGINT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Judge_Server(ID INT NOT NULL AUTO_INCREMENT, Address TINYTEXT, Secret_Key TINYTEXT, Last_Seen_Time BIGINT DEFAULT 0, Busy BOOLEAN DEFAULT FALSE, Current_Task INT DEFAULT -1, Friendly_Name TINYTEXT, Detail TINYTEXT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE Realname_Reference(ID INT NOT NULL AUTO_INCREMENT, Student_ID TINYTEXT, Real_Name TINYTEXT, PRIMARY KEY(ID))ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```