"""Personal_Service ↔ Mirai_brain 표준 JSON 계약 (OPERATING.md §3.3).

사용자 발화용 `message` 와 시스템 제어용 `data` 를 엄격히 분리한다.
추적자(request_id/plan_id/trace_id)는 모든 요청/응답에 보존한다.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RequestContext(BaseModel):
    """요청 컨텍스트 — 입력 모드, 로케일 등 보조 메타."""

    model_config = ConfigDict(extra="allow")

    input_mode: Literal["voice", "text"] | None = None
    locale: str | None = None


class CommandRequest(BaseModel):
    """POST /command 요청 envelope."""

    model_config = ConfigDict(extra="forbid")

    domain: Literal["personal_service"]
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)

    request_id: str
    plan_id: str | None = None
    trace_id: str | None = None

    source: str = "mirai_brain"
    requester: str | None = None
    context: RequestContext = Field(default_factory=RequestContext)


class CommandResponse(BaseModel):
    """POST /command 응답 envelope.

    - `message`: 사용자에게 그대로 들려줄 한국어 자연어.
    - `data`: 시스템 후처리용 구조화 데이터. operation/추적자는 여기에 반드시 보존.
    """

    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
