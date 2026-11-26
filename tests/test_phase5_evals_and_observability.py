"""
Ruta: tests/test_phase5_evals_and_observability.py
Descripción: Pruebas unitarias de la Fase 5 (Ejecución de las 50 solicitudes representativas en español,
redacción automática de secretos en logs y clasificación de métricas de observabilidad).
"""
import logging
import unittest

from evals.eval_suite_es import EVAL_DATASET_50_ES, ArgonEvalHarness
from modules.observability import (
    MetricsCollector,
    RedactingLogFilter,
    redact_sensitive_text,
)


class TestPhase5EvalsAndObservability(unittest.TestCase):
    def test_eval_dataset_has_50_spanish_cases_and_passes_100_percent(self) -> None:
        self.assertEqual(len(EVAL_DATASET_50_ES), 50)
        harness = ArgonEvalHarness()
        try:
            report = harness.run_all(export_report=False)
            self.assertEqual(
                report["passed_cases"],
                50,
                f"Fallaron casos en la evaluación: {report['failures']}",
            )
            self.assertEqual(report["pass_rate_pct"], 100.0)
        finally:
            harness.cleanup()

    def test_log_redaction_strips_api_keys_tokens_passwords_and_phones(self) -> None:
        raw_log = (
            "Error con GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuv "
            "y token sk-proj1234567890abcdefghijklmnopqrstuv "
            "hacia el teléfono +51 987 654 321 con password=MiClaveSuperSecreta99"
        )
        sanitized = redact_sensitive_text(raw_log)
        self.assertNotIn("AIzaSyD1234567890", sanitized)
        self.assertNotIn("sk-proj1234567890", sanitized)
        self.assertNotIn("987 654 321", sanitized)
        self.assertNotIn("MiClaveSuperSecreta99", sanitized)
        self.assertIn("[REDACTED_GEMINI_KEY]", sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)
        self.assertIn("[REDACTED_PHONE]", sanitized)
        self.assertIn("[REDACTED_SECRET]", sanitized)

    def test_redacting_log_filter_sanitizes_log_records(self) -> None:
        log_filter = RedactingLogFilter()
        record = logging.LogRecord(
            name="TestLogger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Usando Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret",
            args=(),
            exc_info=None,
        )
        log_filter.filter(record)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", str(record.msg))
        self.assertIn("Bearer [REDACTED_TOKEN]", str(record.msg))

    def test_metrics_collector_separates_failure_categories_and_latencies(self) -> None:
        collector = MetricsCollector()
        collector.record_tool_execution("get_system_status", "success", 12.5)
        collector.record_tool_execution("send_whatsapp", "approval_required", 1.2, "Requiere confirmación")
        collector.record_tool_execution("analyze_code_file", "denied", 0.8, "Acceso denegado")
        collector.record_tool_execution("search_web", "failed", 150.0, "Error de red al conectar")
        collector.record_tool_execution("check_emails", "timeout", 10000.0, "Timeout IMAP")

        summary = collector.get_summary()
        self.assertEqual(summary["total_tool_calls"], 5)
        self.assertEqual(summary["failure_categories"]["approval_required"], 1)
        self.assertEqual(summary["failure_categories"]["permission_denied"], 1)
        self.assertEqual(summary["failure_categories"]["network_error"], 1)
        self.assertEqual(summary["failure_categories"]["timeout"], 1)
        self.assertEqual(summary["per_tool"]["get_system_status"]["calls"], 1)


if __name__ == "__main__":
    unittest.main()

