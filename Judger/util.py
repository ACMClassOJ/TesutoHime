import logging
import os

# 在指定路径下创建一个日子文件，支持 info warning error 三种级别的日志
# usage:
#    logger.info('compile successfully')
#    logger.warning('')
#    logger.error('')

def logger_creator(path : str):
    #创建日志级别
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    #创建日志文件
    handler_dbug = logging.FileHandler(os.path.join(path, 'debug_log.txt'))
    handler_dbug.setLevel(logging.DEBUG)

    handler_info = logging.FileHandler(os.path.join(path, 'info_log.txt'))
    handler_info.setLevel(logging.INFO)

    handler_warn = logging.FileHandler(os.path.join(path, 'warning_log.txt'))
    handler_warn.setLevel(logging.WARNING)

    handler_erro = logging.FileHandler(os.path.join(path, 'error_log.txt'))
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
    
log = logger_creator("~") # cxy 2021 6 28 暂时使用桌面作为日志保存的地方
