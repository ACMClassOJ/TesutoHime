from judgeManager import work_file

import logging
import os

# 在指定路径下创建一个日子文件，支持 info warning error 三种级别的日志
# usage:
#    logger.info('compile successfully')
#    logger.warning('')
#    logger.error('')

def logger_creator(path : str):
    if not os.path.exists(path):
        os.makedirs(path)
    #创建日志级别
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    #创建日志文件
    file = os.path.join(path, 'debug_log.txt')
    open(file, 'a').close()
    handler_dbug = logging.FileHandler(file)
    handler_dbug.setLevel(logging.DEBUG)

    file = os.path.join(path, 'info_log.txt')
    open(file, 'a').close()
    handler_info = logging.FileHandler(file)
    handler_info.setLevel(logging.INFO)

    file = os.path.join(path, 'warning_log.txt')
    open(file, 'a').close()
    handler_warn = logging.FileHandler(file)
    handler_warn.setLevel(logging.WARNING)

    file = os.path.join(path, 'error_log.txt')
    open(file, 'a').close()
    handler_erro = logging.FileHandler(file)
    handler_erro.setLevel(logging.ERROR)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)

    #定义日志格式
    formatter = logging.Formatter('%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s')
    handler_info.setFormatter(formatter)
    handler_warn.setFormatter(formatter)
    handler_erro.setFormatter(formatter)
    handler_dbug.setFormatter(formatter)
    console.setFormatter(formatter)

    #添加到日志记录器中
    logger.addHandler(handler_dbug)
    logger.addHandler(handler_info)
    logger.addHandler(handler_warn)
    logger.addHandler(handler_erro)
    logger.addHandler(console)

    return logger

log_path = work_file('log/')

log = logger_creator(log_path) # cxy 2021 6 28 暂时使用桌面作为日志保存的地方
