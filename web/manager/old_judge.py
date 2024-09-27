__all__ = ('OldJudgeManager',)

from typing import Optional

from sqlalchemy import func, select

from commons.models import JudgeRecordV1
from web.utils import db


class OldJudgeManager:
    @staticmethod
    def query_judge(judge_id: int) -> Optional[JudgeRecordV1]:  # for details
        stmt = select(JudgeRecordV1).where(JudgeRecordV1.id == judge_id)
        return db.scalar(stmt)

    @staticmethod
    def max_id():
        max_id = db.scalar(select(func.max(JudgeRecordV1.id)))
        if max_id is None: return -1
        return max_id
