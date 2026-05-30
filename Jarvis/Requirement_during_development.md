# Requirement during development

## 2026-04-09

### Weather request defaults and response style
- Source note from prior conversation history provided by Jimi님:
  - Default region for weather requests when no region is explicitly specified:
    - `서울시 강동구 고덕동`
  - Weather response style should follow this pattern:
    - `오늘 고덕동(or 요청지역)은 맑고(흐리고, 비가 오고, 눈이 오고 등 상태), 최고 기온 OO도, 최저 기온 OO도 입니다.`
    - If applicable, add one of:
      - `일교차가 크겠습니다.`
      - `강추위가 예상됩니다.`
      - `몇시부터 몇시까지 비가(눈이) 오겠습니다.`
    - Rain probability rule:
      - `강수확률은 몇 %입니다` 는 **강수확률이 70% 이하일 때만** 말한다.

### Additional follow-up request (2026-04-09)
- Next implementation steps explicitly requested by Jimi님:
  1. Regenerate the weather stub cache using the default region `서울시 강동구 고덕동`.
  2. If possible, update the cache using real KMA weather data instead of stub data.
- Requirement persistence rule:
  - Development instructions like this should be written to `Requirement_during_development.md` and, when architectural/operational, also to `OPERATING_RULES.md`.

### Weather debugging note (2026-04-10)
- User-provided local reference for Gangdong AWS site:
  - Latitude: `37.5556`
  - Longitude: `127.1450`
  - AWS station code: `402 (강동)`
- DFS grid conversion from the provided lat/lon maps to:
  - `nx=63`
  - `ny=127`
- Previous setting `nx=62, ny=127` was likely one grid cell off.
- Important distinction:
  - `AWS 관측지점` data and `동네예보(getVilageFcst)` are not the same source.
  - If user compares against AWS observation or a different KMA product/publication time, forecast values may differ.
- Weather-related modifications should continue to be documented in Jarvis-local markdown files.
- Next parsing improvements approved by Jimi님:
  - Prefer `TMN/TMX` for daily low/high temperatures.
  - Use representative or maximum `POP` instead of minimum.
  - Determine daily condition from whole-day `PTY/SKY` distribution, not only the first slot.
  - Mark incomplete dates conservatively instead of over-asserting tomorrow forecasts.

### Why this file exists
- Development requirements given during chat can be lost from short-term runtime context.
- This file stores implementation-shaping requests that should remain visible during future development turns.
