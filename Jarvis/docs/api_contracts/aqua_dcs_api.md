# aqua-dcs API Contracts (Draft)

Jarvis ↔ aqua-dcs 통합은 **API 계약이 깨지면 시스템이 붕괴**합니다.
이 문서는 Jarvis 관점에서 필요한 최소 계약을 정의합니다.

> NOTE: 실제 엔드포인트/스키마는 aqua-dcs 리포지토리 문서와 일치해야 합니다.

---

## Base URL
`config/settings.yaml`:

```yaml
integrations:
  aqua_dcs:
    base_url: "http://jm-pi:8000"
```

---

## Control request (example)

### POST /control/request

요청 바디(예시):

```json
{
  "requester": "jarvis",
  "user": "<human user>",
  "reason": "voice command",
  "ts": "2026-02-23T06:00:00Z",
  "action": "increase_flow",
  "params": {}
}
```

필수 원칙:
- Jarvis는 **요청자(requester)**
- 안전 판단은 aqua-dcs/정책 레이어에서 보수적으로 처리
- 모든 결과(승인/거절/실패)는 Jarvis storage audit log에 남김
