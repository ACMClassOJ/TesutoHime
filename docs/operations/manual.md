手动操作指南
============

在 ACMOJ 的运维中，有一些操作需要运维组手动完成。

## 邮件列表处理

运维组应加入 acmclassoj@googlegroups.com 邮件列表。如果尚未加入，请联系前一任运维。

对于发送到此邮件列表的邮件，在回复时，**除包含密码等隐私信息外，应抄送邮件列表**，以告知其他运维。

## 重置密码

ACMOJ 暂时无法自助重置密码，重置密码需联系运维。运维接到重置密码请求后，应进行如下操作：

1. **确认待重置的用户。**

   密码重置请求应该至少包含学号或 jAccount 用户名（可以从 SJTU 邮箱地址中推断）；均没有表明的应拒绝请求。如果两者缺少其一，应通过适当的方法查询到缺失的信息。

   得到学号之后，列出学号对应的用户信息：

   ```sql
   select id, student_id, username, friendly_name from "user" where student_id = '501030910042';
   ```

   若有多个用户的，需向用户确认需要重置哪一个用户的密码。用户可能会在密码重置请求中表明其用户名，此时应检查提供的是用户名还是昵称；如果提供的是昵称而不是用户名，应在回复邮件中指明正确的用户名。

2. **进行身份验证。**

   众所周知，邮件发件地址是可以伪造的。在接到请求后，应回复一封邮件以进行身份验证。如果重置请求的发件地址不是交大邮箱，应回复到交大邮箱，同时向重置请求的发件地址回复一封邮件，提醒其查收交大邮箱。无需使用验证码；发送邮件时会自动生成一个 Message ID，回复中会自动包含这个 Message ID (In-Reply-To)，这样邮件客户端才能把这两封邮件联系起来。这个 Message ID 就可以起到验证码的作用。

   示例邮件：

   > <姓名>(同学|老师)：
   >
   > 您好！
   >
   > （原邮件内容）
   >
   > 如果您确实忘记了您的密码，请回复这封邮件以验证您的身份。
   >
   > （发件地址非 SJTU）我向您的交大邮箱发送了一封验证邮件，请登录 https://mail.sjtu.edu.cn/ 查收。
   >
   > （有多个用户）您有两个用户，用户名分别为「chengxin」和「yuntianming」。请问您要重置哪个帐户的密码？
   >
   > （认为昵称是用户名）您的用户名应为「chengxin」，「DX3906」是您的昵称。登录时请使用用户名，不要使用昵称。
   >
   > <运维组成员姓名>    
   > ACM Class OnlineJudge 运维组    
   > 1970 年 1 月 1 日

3. **进行密码重置。**

   登录管理界面即可修改密码；不需要修改的项留空即可。应将密码重置为随机数，并将重置后的密码发送到用户的交大邮箱。

   示例邮件：

   > <姓名>(同学|老师)：
   >
   > 您好！
   >
   > 您的密码已被重置为：
   >
   > QQLt4cUwYxAMeXfc1Zg3mg（实际回复时，请重新生成随机数，切勿直接使用此字符串）
   >
   > 请您登录 OJ 后，转到个人信息页修改密码。
   >
   > 感谢您使用 ACM Class OnlineJudge！
   >
   > <运维组成员姓名>    
   > ACM Class OnlineJudge 运维组    
   > 1970 年 1 月 1 日

## 管理班级

班级暂时需要手动创建，且没有 UI，只能通过 SQL 创建。创建班级后请将申请创建的老师或助教添加为管理员，同样需要通过 SQL 操作。

```sql
insert into term (name, start_time, end_time) values ('1970-1971-1', '1970-09-01 00:00:00', '1971-01-15 23:59:59');
insert into course_tag (name) values ('apex 实验室');
insert into course (name, description, tag_id, term_id) values ('课程名称', '课程描述', 42, 42);
insert into enrollment (user_id, course_id, admin) values ((select "user".id from "user" where username = 'admin'), 42, true);
insert into enrollment (user_id, course_id, admin) values ((select "user".id from "user" where username = 'student'), 42, false);
```

## 管理 OAuth 应用

OAuth 应用同样需要手动通过 SQL 创建。

```sql
insert into oauth_app (client_id, client_secret, redirect_uri, name, provider, scopes) values ('随机数', '随机数', 'https://redirect-host.example.com/redirect-path', '应用名称', '应用提供者', '{user:profile,submission:create,submission:read}');
```

实际使用的 redirect_uri 需以此处的 redirect_uri 开头，例如上述配置可以重定向到

- https://redirect-host.example.com/redirect-path
- https://redirect-host.example.com/redirect-path/sub/path?query

但不可以重定向到

- https://redirect-host.example.com/
- https://another-host.example.com/redirect-path
- https://subdomain.redirect-host.example.com/redirect-path
