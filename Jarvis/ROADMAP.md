# Roadmap

이 문서는 Jarvis가 앞으로 어떤 순서로 성숙해갈지에 대한 **의도/방향**을 기록합니다.
구현 세부와 실행 방법은 `MILESTONES.md`, `RECOVERY_GUIDE.md`를 참고합니다.

---

## M2 (현재) — 대화 루프/상태머신 안정화
- [ ] wake → greet → record → STT → intent → respond → repeat 루프 장시간 안정성(예: 24h) 검증
- [ ] 마이크/오디오 장치 점유 충돌 제거(arecord/pvrecorder/pw-play)
- [ ] 타임아웃/취소/재시도 정책 정의
- [ ] 잡음 환경에서 STT 품질 개선(전처리, VAD, 녹음 길이 전략)

## M3 — Intent/Router 확장 + LLM fallback 규칙 고도화
- [ ] 로컬 intent coverage 확대(도움/help, 상태조회, 간단 제어)
- [ ] Gemini fallback 사용 조건 명확화(unknown에만, 안전 관련 질문 제한 등)
- [ ] LLM 호출 실패/지연 시 graceful degrade

## M4 — 도메인 실동작 연결 (aqua-dcs / home_iot)
- [ ] aqua-dcs REST API 계약 문서화 + 클라이언트 구현
- [ ] 정책(안전/권한/레이트리밋) 강제 적용 후 제어 요청 수행
- [ ] 결과/거부 사유 audit log 100% 기록

## M5 — 서비스화/운영
- [ ] systemd 서비스화 + auto-restart
- [ ] 로그 로테이션/보관 전략
- [ ] 장애 복구 플레이북
