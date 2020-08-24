import os, shutil, requests, zipfile, json
from .ProblemConfig import *
from collections import namedtuple


def try_cache(config, id: int) -> int:
    try:
        f = open(config.cache_dir + '/' + str(id) + '.timestamp')
        local_timestamp = int(f.read())
        f.close()
    except FileNotFoundError:
        local_timestamp = 0
    try:
        r = requests.get(config.server + '/' + config.key + '/' + str(id) + '.timestamp')
        timestamp = int(r.text)
    except:
        timestamp = -1
    if timestamp > local_timestamp:
        return 1
    if timestamp == -1 and local_timestamp == 0:
        return -1
    return 0


def get_data_from_server(config, id: int):
    r = requests.get(config.server + '/' + config.key + '/' + str(id) + '.zip', stream=True)
    with open(config.cache_dir + '/' + str(id) + '.zip', 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    shutil.rmtree(config.cache_dir + '/' + str(id), ignore_errors=True)
    with zipfile.ZipFile(config.cache_dir + '/' + str(id) + '.zip', 'r') as zip_file:
        zip_file.extractall(config.cache_dir)
    os.remove(config.cache_dir + '/' + str(id) + '.zip')
    rt = requests.get(config.server + '/' + config.key + '/' + str(id) + '.timestamp')
    with open(config.cache_dir + '/' + str(id) + '.timestamp', 'w') as ft:
        ft.write(rt.text)


def get_data(config, id: int) -> (ProblemConfig, str):
    r = try_cache(config, id)
    if r == 1:
        get_data_from_server(config, id)
    if r == -1:
        raise Exception("Can't get data")
    f = open(config.cache_dir + '/' + str(id) + '/config.json')
    pconfig: ProblemConfig = json.loads(f.read(), object_hook=lambda x: namedtuple('X', x.keys())(*x.values()))
    f.close()
    return pconfig, config.cache_dir + '/' + str(id)
