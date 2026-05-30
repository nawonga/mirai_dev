# Fail-safe Scenarios (Draft)

이 문서는 Jarvis의 정책 레이어가 어떤 상황에서 **보수적으로 거부**해야 하는지 정리합니다.
정식 규칙은 `OPERATING_RULES.md`가 우선입니다.

## 기본 원칙
- aqua-dcs 상태가 WARN/ERROR라면 제어 요청은 기본 거부
- 야간 시간대 제어 제한(필요 시)
- 연속 제어 요청은 rate-limit로 차단

## TODO
- 시간대/사용자별 정책 테이블 정의
- 거부 사유 표준화(사용자 TTS 메시지 + audit log 필드)
