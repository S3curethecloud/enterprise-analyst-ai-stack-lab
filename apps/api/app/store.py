from __future__ import annotations

from threading import RLock

from apps.api.app.contracts import AnalysisResult, TraceRecord


class AnalysisStore:
    def __init__(self) -> None:
        self._analyses: dict[str, AnalysisResult] = {}
        self._traces: dict[str, TraceRecord] = {}
        self._lock = RLock()

    def save_analysis(self, analysis: AnalysisResult) -> None:
        with self._lock:
            self._analyses[analysis.analysis_id] = analysis

    def get_analysis(self, analysis_id: str) -> AnalysisResult | None:
        with self._lock:
            return self._analyses.get(analysis_id)

    def save_trace(self, trace: TraceRecord) -> None:
        with self._lock:
            self._traces[trace.trace_id] = trace

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        with self._lock:
            return self._traces.get(trace_id)

    def clear(self) -> None:
        with self._lock:
            self._analyses.clear()
            self._traces.clear()
