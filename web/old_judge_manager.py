__all__ = ('OldJudgeManager',)

from sqlalchemy import select, func

from web.utils import SqlSession
from commons.models import JudgeRecord


class OldJudgeManager:
    """
    * ID: INT, auto_increment, PRIMARY KEY
    * Code: TEXT
    * User: TINYTEXT
    * Problem_ID: INT
    * Language: INT
    * Status: INT
    * Score: INT
    * Time: BIGINT // unix nano
    * Time_Used: INT // ms
    * Mem_Used: INT // Byte
    * Detail: MEDIUMTEXT // may exceed 64 KB
    """

    @staticmethod
    def query_judge(judge_id: int) -> JudgeRecord:  # for details
        with SqlSession(expire_on_commit=False) as db:
            stmt = select(JudgeRecord).where(JudgeRecord.id == judge_id)
            return db.scalar(stmt)

    @staticmethod
    def max_id():
        with SqlSession() as db:
            max_id = db.scalar(select(func.max(JudgeRecord.id)))
            if max_id is None: return -1
            return max_id
