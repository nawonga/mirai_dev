"""Intent Layer — 로컬 rule-based 파서 + Mirai_brain 핸드오버.

Local-First(OPERATING.md §6): 인사·시간·날짜·종료 등 즉시 처리 가능한 단순 의도는
로컬 규칙으로 바로 해결하고, 데이터가 필요하거나 모호/복합인 의도만 Mirai_brain으로 넘긴다.

단독 테스트(마이크 없이):
    PYTHONPATH=src python -m jarvis.intent "지금 몇 시야?"
    PYTHONPATH=src python -m jarvis.intent "오늘 날씨 어때?"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from jarvis import mirai_brain

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


@dataclass
class Intent:
    name: str                      # 예: time.now, greeting, system.stop, handover.pending, unknown
    route: str                     # local | mirai_brain | home_iot | aqua_dcs | personal_service
    entities: dict = field(default_factory=dict)
    confidence: float = 0.0
    resolved_by: str = "local"     # local | mirai_brain | mirai_brain_stub ...
    reply: str | None = None       # 로컬에서 즉시 만들 수 있는 응답(있으면 그대로 발화)


def _normalize(text: str) -> str:
    """공백/문장부호 제거하고 한글·영숫자만 남긴다(키워드 매칭용)."""
    return re.sub(r"[^\w가-힣]", "", text or "").lower()


def parse_local(text: str) -> Intent | None:
    """로컬 규칙으로 해결 가능한 의도면 Intent 반환, 아니면 None."""
    low = _normalize(text)
    if not low:
        return None

    # 대화 세션 종료 — wake 복귀. 잘못된 응답 후 사용자가 향단이를 wake 대기로 돌려보낼 때.
    # device "꺼줘"와 충돌 피하려 한정적 키워드만.
    if any(k in low for k in (
        "너아니야", "너아닌데", "내가아니야",
        "들어가", "들어가있어", "들어가있어라",
        "조용히", "조용히해", "쉿", "쉬어", "시끄러",
        "가만히있어", "가만있어",
    )):
        return Intent("system.sleep", "local", confidence=0.9, reply="네 알겠습니다.")

    # 영구 종료 (현재 systemd Restart=always 로 자동 복귀하지만 의미 분리 유지)
    if any(k in low for k in ("그만", "종료", "중지", "스톱", "끝내")):
        return Intent("system.stop", "local", confidence=0.9, reply="네, 종료할게요.")

    # 인사
    if any(k in low for k in ("안녕", "반가", "하이", "헬로")):
        return Intent("greeting", "local", confidence=0.9,
                      reply="안녕하세요! 저는 페퍼입니다. 무엇을 도와드릴까요?")

    # 감사
    if any(k in low for k in ("고마", "감사", "땡큐")):
        return Intent("thanks", "local", confidence=0.9, reply="천만에요!")

    # 시간
    if ("몇시" in low) or ("시간" in low and any(k in low for k in ("지금", "알려", "뭐", "몇"))):
        now = datetime.now()
        ampm = "오전" if now.hour < 12 else "오후"
        h12 = now.hour % 12 or 12
        return Intent("time.now", "local", entities={"hour": now.hour, "minute": now.minute},
                      confidence=0.9, reply=f"지금은 {ampm} {h12}시 {now.minute}분이에요.")

    # 날짜/요일
    if any(k in low for k in ("며칠", "날짜", "무슨요일", "요일", "오늘날짜")):
        d = datetime.now()
        return Intent("date.today", "local",
                      entities={"date": d.strftime("%Y-%m-%d"), "weekday": _WEEKDAYS[d.weekday()]},
                      confidence=0.9,
                      reply=f"오늘은 {d.month}월 {d.day}일 {_WEEKDAYS[d.weekday()]}요일이에요.")

    return None


def parse(text: str, context: dict | None = None) -> Intent:
    """Local-First로 파싱. 로컬 미해결 시 Mirai_brain으로 핸드오버."""
    local = parse_local(text)
    if local is not None:
        return local

    data = mirai_brain.resolve(text, context)
    return Intent(
        name=data.get("intent", "unknown"),
        route=data.get("route", "mirai_brain"),
        entities=data.get("entities", {}),
        confidence=float(data.get("confidence", 0.0)),
        resolved_by=data.get("resolved_by", "mirai_brain"),
        reply=data.get("message"),
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Intent 파서 단독 테스트")
    ap.add_argument("text", nargs="+", help="분류할 문장")
    args = ap.parse_args(argv)
    text = " ".join(args.text)

    intent = parse(text)
    print(f"입력 : {text!r}")
    print(f"의도 : {intent.name}  (route={intent.route}, by={intent.resolved_by}, "
          f"conf={intent.confidence})")
    print(f"엔티티: {intent.entities}")
    print(f"응답 : {intent.reply!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
