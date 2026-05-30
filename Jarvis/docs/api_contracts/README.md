# API Contracts

이 폴더의 문서는 Jarvis의 외부 **계약(Contract)** 입니다. 방향은 두 종류가 있습니다.

**Outbound (Jarvis → 외부 도메인, Jarvis가 요청자)**
- `aqua_dcs_api.md`

**Inbound (외부 → Jarvis, Jarvis가 서버)**
- `text_command_api.md` — 외부(iOS 단축어 등)가 텍스트 명령을 POST로 전달, STT 이후 Intent 파싱 단계에 주입
