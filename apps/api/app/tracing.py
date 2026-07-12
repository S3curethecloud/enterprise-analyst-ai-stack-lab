from __future__ import annotations

from typing import Any

from apps.api.app.contracts import TraceEvent, TraceRecord


class TraceRecorder:
    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self._events: list[TraceEvent] = []

    def add(self, event_type: str, details: dict[str, Any] | None = None) -> TraceEvent:
        event = TraceEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            details=details or {},
        )
        self._events.append(event)
        return event

    def build(self) -> TraceRecord:
        return TraceRecord(
            trace_id=self.trace_id,
            events=list(self._events),
        )

    @property
    def event_count(self) -> int:
        return len(self._events)
