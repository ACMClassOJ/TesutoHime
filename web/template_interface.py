from commons.models import JudgeRecord2


class RowJudgeStatus(JudgeRecord2):
	def __init__(self) -> None:
		super().__init__()
	real_name: str
	visible: bool
