__all__ = ('OldJudgeManager',)

from sqlalchemy import select, func

from web.utils import SqlSession
from commons.models import JudgeRecordV1


class OldJudgeManager:
    @staticmethod
    def query_judge(judge_id: int) -> JudgeRecordV1:  # for details
        with SqlSession(expire_on_commit=False) as db:
            stmt = select(JudgeRecordV1).where(JudgeRecordV1.id == judge_id)
            return db.scalar(stmt)

    @staticmethod
    def max_id():
        with SqlSession() as db:
            max_id = db.scalar(select(func.max(JudgeRecordV1.id)))
            if max_id is None: return -1
            return max_id
