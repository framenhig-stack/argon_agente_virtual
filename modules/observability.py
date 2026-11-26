"""
Ruta: modules/observability.py
Descripción: Observabilidad segura, redacción automática de secretos/PII en logs
y recolector de métricas de calidad por categoría de fallo (Fase 5).
"""
import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List
from config import LOG_DIR

METRICS_FILE: Path = LOG_DIR / "agent_metrics.json"

# Patrones de datos sensibles que jamás deben escribirse en texto plano en los logs
_REDACTION_PATTERNS = [
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9\-_]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\b(?:secret|ntn)_[A-Za-z0-9]{20,}\b"), "[REDACTED_NOTION_TOKEN]"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.I), "Bearer [REDACTED_TOKEN]"),
    (
        re.compile(r"((?:password|contraseña|api[_\s]?key|token|clave\s+secreta)\s*(?:es|=|:)\s*)(?!\[REDACTED)\S+", re.I),
        r"\1[REDACTED_SECRET]",
    ),
    (re.compile(r"\+\d{1,3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3,4}\b"), "[REDACTED_PHONE]"),
]


def redact_sensitive_text(text: str) -> str:
    """Reemplaza claves API, tokens, contraseñas y teléfonos por marcadores seguros."""
    if not text:
        return ""
    sanitized = str(text)
    for pattern, replacement in _REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class RedactingLogFilter(logging.Filter):
    """Filtro de logging que sanitiza automáticamente cualquier mensaje antes de escribirlo en disco o consola."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            record.msg = redact_sensitive_text(msg)
            record.args = ()
        except Exception:
            pass
        return True


class MetricsCollector:
    """
    Registra métricas operativas de Argon 4 separando tipos de fallo:
    - tool_error, model_error, network_error, permission_denied, approval_required, timeout, unverified_claim.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.total_tool_calls: int = 0
            self.status_counts: Dict[str, int] = {
                "success": 0,
                "partial": 0,
                "failed": 0,
                "denied": 0,
                "approval_required": 0,
                "timeout": 0,
            }
            self.failure_categories: Dict[str, int] = {
                "model_error": 0,
                "tool_error": 0,
                "network_error": 0,
                "permission_denied": 0,
                "approval_required": 0,
                "timeout": 0,
                "unverified_claim": 0,
            }
            self.tool_stats: Dict[str, Dict[str, Any]] = {}
            self.recent_events: List[Dict[str, Any]] = []

    def record_tool_execution(
        self,
        tool_name: str,
        status: str,
        duration_ms: float,
        error_msg: str = "",
    ) -> None:
        clean_status = status if status in self.status_counts else "failed"
        safe_error = redact_sensitive_text(error_msg)[:160]

        with self._lock:
            self.total_tool_calls += 1
            self.status_counts[clean_status] = self.status_counts.get(clean_status, 0) + 1

            # Clasificación de categoría de fallo según Fase 5 (Tarea 6)
            if clean_status == "denied":
                self.failure_categories["permission_denied"] += 1
            elif clean_status == "approval_required":
                self.failure_categories["approval_required"] += 1
            elif clean_status == "timeout":
                self.failure_categories["timeout"] += 1
            elif clean_status == "failed":
                if any(w in safe_error.lower() for w in ("red", "network", "conexión", "connection", "http")):
                    self.failure_categories["network_error"] += 1
                else:
                    self.failure_categories["tool_error"] += 1

            t_stat = self.tool_stats.setdefault(
                tool_name,
                {"calls": 0, "success": 0, "failed": 0, "total_ms": 0.0, "avg_ms": 0.0},
            )
            t_stat["calls"] += 1
            if clean_status in ("success", "partial"):
                t_stat["success"] += 1
            else:
                t_stat["failed"] += 1
            t_stat["total_ms"] = round(t_stat["total_ms"] + duration_ms, 2)
            t_stat["avg_ms"] = round(t_stat["total_ms"] / t_stat["calls"], 2)

            self.recent_events.append(
                {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "tool": tool_name,
                    "status": clean_status,
                    "duration_ms": round(duration_ms, 2),
                    "error": safe_error,
                }
            )
            if len(self.recent_events) > 40:
                self.recent_events = self.recent_events[-40:]

    def record_model_issue(self, category: str = "model_error") -> None:
        with self._lock:
            if category in self.failure_categories:
                self.failure_categories[category] += 1
            else:
                self.failure_categories["model_error"] += 1

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            completed = self.status_counts["success"] + self.status_counts["partial"]
            completion_rate = (
                round((completed / self.total_tool_calls) * 100.0, 1)
                if self.total_tool_calls > 0
                else 100.0
            )
            return {
                "total_tool_calls": self.total_tool_calls,
                "completion_rate_pct": completion_rate,
                "status_counts": dict(self.status_counts),
                "failure_categories": dict(self.failure_categories),
                "per_tool": dict(self.tool_stats),
                "recent_events": list(self.recent_events[-10:]),
            }

    def export_to_disk(self, filepath: Path = METRICS_FILE) -> Dict[str, Any]:
        summary = self.get_summary()
        try:
            filepath.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        return summary


# Instancia global compartida
metrics_collector = MetricsCollector()

