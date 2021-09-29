from utils import unix_nano

class ContestCache:

    expire_time = 14
    
    # table: contest_id -> [time(int), data(list)]

    def __init__(self):
        self.table = dict()

    def expire(self):
        expire_list = []
        for contest_id_in_table in self.table:
            if unix_nano() - self.table[contest_id_in_table][0] > self.expire_time:
                expire_list.append(contest_id_in_table)

        for expire_id in expire_list:
            self.table.pop(expire_id)

    def get(self, contest_id: int):
        if contest_id in self.table:
            return self.table[contest_id][1]

        return []

    def put(self, contest_id: int, data: list):
        self.table[contest_id] = [unix_nano(), data]

Contest_Cache = ContestCache()