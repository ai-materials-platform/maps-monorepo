"""서버 시스템 프롬프트와 정해진 거절 문구."""

REFUSAL_OFF_TOPIC = (
    "저는 재료공학과 MAPS 사용법에 관한 질문에만 답할 수 있어요. "
    "합금·열처리·물성·시험법이나 프로그램 사용에 대해 물어봐 주세요."
)
REFUSAL_BUDGET = "이번 달 챗봇 사용 한도에 도달했어요. 다음 달에 다시 이용해 주세요."
REFUSAL_LEAK = REFUSAL_OFF_TOPIC
