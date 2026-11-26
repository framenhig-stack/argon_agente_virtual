"""
Ruta: tests/test_phase1_security.py
Descripción: Pruebas unitarias de la Fase 1 (Seguridad de rutas, motor de permisos,
aprobaciones vinculadas a argumentos y veracidad de resultados en tareas).
No realiza llamadas de red ni envía mensajes reales.
"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from modules.productivity_tools import ProductivityTools, build_unified_task_result
from modules.tool_policy import ToolPolicyEngine
from modules.tool_router import AgentToolRouter


class TestPhase1SecurityAndTools(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name).resolve()

        # Crear archivo legítimo de prueba
        self.valid_py = self.base_path / "sample_module.py"
        self.valid_py.write_text("class Demo:\n    def hello(self):\n        return 42\n", encoding="utf-8")

        # Crear archivos sensibles simulados (sin datos reales)
        (self.base_path / ".env").write_text("SECRET_KEY=dummy", encoding="utf-8")
        (self.base_path / "PyWhatKit_DB.txt").write_text("dummy phone log", encoding="utf-8")
        (self.base_path / "memory.sqlite3").write_text("binary db", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # ---------------- 1. PRUEBAS DE SEGURIDAD DE RUTAS ----------------
    def test_analyze_code_file_allows_valid_project_file(self) -> None:
        res = ProductivityTools.analyze_code_file("sample_module.py", base_dir=self.base_path)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "success")
        self.assertIn("Sintaxis Python correcta", res["syntax"])

    def test_analyze_code_file_rejects_path_traversal(self) -> None:
        res = ProductivityTools.analyze_code_file("../outside_secret.py", base_dir=self.base_path)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "denied")

    def test_analyze_code_file_rejects_sibling_prefix_attack(self) -> None:
        # Carpeta hermana que comparte el mismo prefijo textual que base_path
        sibling_dir = self.base_path.parent / f"{self.base_path.name}_secret"
        sibling_dir.mkdir(exist_ok=True)
        sibling_file = sibling_dir / "leak.py"
        sibling_file.write_text("print('secret')", encoding="utf-8")
        try:
            res = ProductivityTools.analyze_code_file(str(sibling_file), base_dir=self.base_path)
            self.assertFalse(res["ok"])
            self.assertEqual(res["status"], "denied")
        finally:
            sibling_file.unlink(missing_ok=True)
            sibling_dir.rmdir()

    def test_analyze_code_file_blocks_sensitive_files(self) -> None:
        for sensitive in [".env", "PyWhatKit_DB.txt", "memory.sqlite3"]:
            res = ProductivityTools.analyze_code_file(sensitive, base_dir=self.base_path)
            self.assertFalse(res["ok"], f"Debió bloquearse: {sensitive}")
            self.assertEqual(res["status"], "denied")

    # ---------------- 2. PRUEBAS DE PERMISOS Y APROBACIONES ----------------
    def test_sensitive_external_tool_blocked_without_approval(self) -> None:
        engine = ToolPolicyEngine()
        mock_send = MagicMock(return_value={"ok": True})

        res = engine.execute(
            "send_whatsapp",
            mock_send,
            {"message": "Hola equipo", "phone": "+12025550100"},
            require_confirmation_override=True,
        )
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "approval_required")
        mock_send.assert_not_called()

    def test_approval_is_bound_to_exact_arguments_and_single_use(self) -> None:
        engine = ToolPolicyEngine()
        mock_send = MagicMock(return_value={"ok": True})
        args_original = {"message": "Mensaje autorizado", "phone": "+12025550100"}
        args_tampered = {"message": "Mensaje diferente no autorizado", "phone": "+12025550100"}

        # Solicitud inicial devuelve action_id
        blocked = engine.execute("send_whatsapp", mock_send, args_original, require_confirmation_override=True)
        action_id = blocked["action_id"]
        engine.approve_action(action_id)

        # Intento con argumentos distintos sigue bloqueado
        tampered_res = engine.execute("send_whatsapp", mock_send, args_tampered, require_confirmation_override=True)
        self.assertEqual(tampered_res["status"], "approval_required")
        mock_send.assert_not_called()

        # Ejecución con los argumentos exactos aprobados sí pasa
        approved_res = engine.execute("send_whatsapp", mock_send, args_original, require_confirmation_override=True)
        self.assertTrue(approved_res["ok"])
        self.assertEqual(approved_res["status"], "success")
        mock_send.assert_called_once()

        # Una segunda llamada sin nueva aprobación vuelve a requerir confirmación
        second_res = engine.execute("send_whatsapp", mock_send, args_original, require_confirmation_override=True)
        self.assertEqual(second_res["status"], "approval_required")

    # ---------------- 3. PRUEBAS DE VERACIDAD DE RESULTADOS ----------------
    def test_unified_task_reports_success_partial_and_failed_truthfully(self) -> None:
        # Caso 1: Ambos sistemas tienen éxito -> 'success'
        both_ok = build_unified_task_result(
            "Preparar demo",
            local_res={"ok": True},
            notion_res={"ok": True},
            notion_enabled=True,
        )
        self.assertEqual(both_ok["status"], "success")
        self.assertTrue(both_ok["ok"])

        # Caso 2: Local funciona pero Notion falla -> 'partial'
        partial = build_unified_task_result(
            "Preparar demo",
            local_res={"ok": True},
            notion_res={"ok": False, "error": "Timeout Notion"},
            notion_enabled=True,
        )
        self.assertEqual(partial["status"], "partial")
        self.assertTrue(partial["ok"])
        self.assertFalse(partial["notion_synced"])

        # Caso 3: Ambos fallan -> 'failed' y ok=False
        both_fail = build_unified_task_result(
            "Preparar demo",
            local_res={"ok": False, "error": "Disco lleno"},
            notion_res={"ok": False, "error": "Sin red"},
            notion_enabled=True,
        )
        self.assertEqual(both_fail["status"], "failed")
        self.assertFalse(both_fail["ok"])


if __name__ == "__main__":
    unittest.main()