### Judge_Server Scheduler Interface

#### Judge Server:

* http接口，用于接收评测请求：

  ```
  url/judge
  ```
  Post方式发送
  
  其中数据为：
  
  * Server_Secret：字符串，Web Server的API Key，由评测机上的Config文件预置，错误时拒绝评测。
  * Problem_ID：4位数字，表示题号。
  * Judge_ID：多位数字，表示该次评测ID。
  * Lang: 字符串，表示程序语言，为'C++'或'Git'(其他语言尚未实装)
  * Code：代码。
  
  若添加成功返回字符串'0'，否则返回字符串'-1'。
  
* http接口，用于查询是否正忙：

  ```
  url/isBusy
  ```
  Post方式发送
  
  其中数据为：

  * Server_Secret：意义同上。

  若忙成功返回字符串'1'，不忙返回字符串'0'，调用失败返回字符串'-1'。

* 心跳包发送：

  定期(时间定义于评测机上Config文件)向Web服务器发送当前评测机在线信息。

  具体方式定义于Web服务器段。

* 评测结果发送：

  向Web服务器发送评测结果。

  具体方式定义于Web服务器段。

#### Web Server

* http接口，用于接收评测机心跳包。

  ```
  url/heartBeat
  ```
  Post方式发送
  
  其中数据为：

  * Server_Secret：字符串，用于标识评测机身份。

  这个API应被评测机定期调用以标识自身在线。

  Web服务器返回'0'，表示接受成功。

* http接口，用于接收评测结果：

  ```
  url/pushResult
  ```
  Post方式发送
  
  其中数据为：

  * Server_Secret：字符串，用于标识评测机身份。
  * Judge_ID：多位数字，本次评测的ID。
  * Result：字符串，为json格式的评测结果。

  Web服务器返回'0'，表示接受成功。

#### 数据交换Json格式：

众所周知，Python3自带json编码。

我们要将以下格式的类压为Json。

```python
class Result:
     def __init__(self):
      	self.Status=...;(状态)
        self.Score=...;(分数:pts)
      	self.Time_Used = ...;(时间:ms)
        self.Mem_Used = ...;(内存：Byte)
        self.Details = [[id(数字), result(AC、WA、CE、RE、TLE、MLE、RE、CE、Memory Leak、System Error), score(pts), time(ms), mem(Byte), disk(kb, -1当不存在), 错误提示信息(如CE信息和WA的对比,RE的系统输出,ML时的valgrind结果)]*n(多个)];
        self.Config = Problem_Config(一个题目配置文件的实例)
class Problem_Config:
      def __init__(self):
        self.Groups = [[group_ID(测试点组的id), group_Name(测试组名), group_Score(测试组全部通过的分数), [Test Point List(存储测试点的id列表)]]] 
        self.Details = [[id, dependency, time_Limit, mem_Limit, disk_Limit] * n] # 存储每个测试点的3项限制, dependency为依赖测试，当且仅当dependency正常评测，才正常评测当前测试点。
```

在评分器中，也利用以上两个结构体计算本题分数。（当然Result.Score不可能给出）　

**所有的http操作通过自签名的证书保证SSL加密(你现在可以先按照不加密http做，之后再改)**

**注意通过Post提交请求可能需要url转义**

