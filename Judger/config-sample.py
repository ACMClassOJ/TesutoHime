class DataConfig:
    server = 'http://192.168.1.233:8080/'         #data_service_url，数据服务地址，可以是内网
    key = '233'                                   #data_service_key，数据服务密钥
    cache_dir = '/home/rbq/TesutoHime_data_cache' #judger_cache_dir，数据会被缓存本地的哪个文件夹

Path = '/work'
My_Web_Server_Secret = "crazy_cloud"        #web_secret，与web服务器通信用密钥，由web给出
Master_Server_Secret = "Progynova"          #judger_secret，web向judger请求通信时用密钥，需告知web
                                            #建议生成随机字符串构成一个较强的密钥
busyFlag = '/work/busyFlag'                 
Web_Server = "http://192.168.1.233:5000/OnlineJudge/api"
                                            #web_url，web服务器url/api，可以是内网，一定要有http://
Heart_Beat_Period = 3000                    #judger向web发送心跳包间隔，单位ms，生产环境建议半分钟以上减小网络压力
API_port = 8000                             #judger_port，judger与web通信时judger所用端口
Judge_Result_Resend_Period = 1000
Performance_Rate = 1                        # real_run_time/oj_standard_time，用于平衡不同机器之间运行速度差距