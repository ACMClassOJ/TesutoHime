### 数据表格式：

#### Problem:

* ID: INT, auto_increment, PRIMARY KEY
* Description: TEXT
* Input: TEXT
* Output: TEXT
* Example_Input: TEXT
* Example_Output: TEXT
* Data_Range: TEXT
* Release_Time: BIGINT // unix nano
* Flag_Count: INT // 在比赛或作业中的次数

#### User:

* tempID auto_increment, PRIMARY KEY
* Username: TINYTEXT
* Student_ID: BIGINT
* Friendly_Name: TINYTEXT
* Password: TINYTEXT // sha-512 with salt
* Salt: INT
* Privilege: INT

#### Judge:

* ID: INT, auto_increment, PRIMARY KEY
* Code: TEXT
* User: INT
* Result: INT
* Score: INT
* Time: BIGINT // unix nano
* Detail: MEDIUMTEXT // may exceed 64 KB

#### Contest:

* ID: INT, auto_increment, PRIMARY KEY
* Start_Time: BIGINT // unix nano
* End_Time: BIGINT // unix nano
* Type: INT // Contest or Homework

#### Contest_Problem:

* tempID: INT, auto_increment, PRIMARY KEY // useless
* Belong: INT // Contest it belongs to
* Problem_ID: INT

#### Contest_Player:

* tempID: INT, auto_increment, PRIMARY KEY // useless
* Belong: INT // Contest it belongs to
* Username: TINYTEXT // User

如何查询比赛中提交？比赛->用户+题目->组合查提交(反正mysql非常快对不对)

#### Discuss:

* ID: INT, auto_increment, PRIMARY KEY
* Problem_ID: INT
* Username: TINYTEXT
* Data: TEXT