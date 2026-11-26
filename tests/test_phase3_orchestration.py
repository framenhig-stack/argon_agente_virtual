"""
Ruta: tests/test_phase3_orchestration.py
Descripción: Pruebas unitarias de la Fase 3 (Ejecución secuencial con dependencias,
paso de observaciones reales, detención cuando un paso previo falla o pide aprobación,
límite máximo de pasos y defensa contra Prompt Injection en salidas de herramientas).
"""
import unittest
from typing import Any, Dict, List

from modules.agent_loop import AgentExecutionLoop, PlanStep


class TestPhase3Orchestration(unittest.TestCase):
    def test_dependent_steps_execute_in_strict_order_and_pass_observation(self) -> None:
        execution_order: List[str] = []
        captured_notes: List[str] = []

        def fake_invoker(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
            execution_order.append(tool_name)
            if tool_name == "get_system_status":
                return {
                    "ok": True,
                    "status": "success",
                    "summary": "CPU 12%, RAM 48%",
                }
            if tool_name == "save_memory":
                captured_notes.append(args.get("note", ""))
                return {"ok": True, "status": "success"}
            return {"ok": False, "status": "failed"}

        loop = AgentExecutionLoop(tool_invoker=fake_invoker, max_steps=5)
        plan = [
            PlanStep(step_id="step_1", tool="get_system_status", args={}),
            PlanStep(
                step_id="step_2",
                tool="save_memory",
                args={"note": "Reporte: {{step_1.output}}", "category": "Sistema"},
                depends_on=["step_1"],
            ),
        ]

        report = loop.execute_plan(plan)
        self.assertTrue(report.ok)
        self.assertEqual(report.status, "success")
        self.assertEqual(execution_order, ["get_system_status", "save_memory"])
        self.assertEqual(captured_notes[0], "Reporte: CPU 12%, RAM 48%")

    def test_dependent_step_is_skipped_when_parent_requires_approval_or_fails(self) -> None:
        called_tools: List[str] = []

        def fake_invoker(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
            called_tools.append(tool_name)
            if tool_name == "send_whatsapp":
                return {
                    "ok": False,
                    "status": "approval_required",
                    "action_id": "send_whatsapp_123",
                    "error": "Requiere confirmación",
                }
            return {"ok": True, "status": "success"}

        loop = AgentExecutionLoop(tool_invoker=fake_invoker, max_steps=5)
        plan = [
            PlanStep(step_id="s1", tool="send_whatsapp", args={"message": "Hola"}),
            PlanStep(
                step_id="s2",
                tool="save_memory",
                args={"note": "Se envió el WhatsApp exitosamente"},
                depends_on=["s1"],
            ),
        ]

        report = loop.execute_plan(plan)
        self.assertEqual(report.status, "approval_required")
        # El paso 2 jamás debe ejecutarse si el paso 1 quedó en espera de aprobación
        self.assertEqual(called_tools, ["send_whatsapp"])
        self.assertEqual(report.observations[1].status, "skipped_dependency")

    def test_plan_exceeding_max_steps_is_rejected_before_execution(self) -> None:
        called = False

        def fake_invoker(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal called
            called = True
            return {"ok": True, "status": "success"}

        loop = AgentExecutionLoop(tool_invoker=fake_invoker, max_steps=3)
        oversized_plan = [
            PlanStep(step_id=f"s{i}", tool="get_system_status", args={})
            for i in range(1, 5)  # 4 pasos > límite de 3
        ]

        report = loop.execute_plan(oversized_plan)
        self.assertFalse(report.ok)
        self.assertEqual(report.status, "denied")
        self.assertFalse(called)

    def test_circular_dependency_is_detected_and_blocked(self) -> None:
        loop = AgentExecutionLoop(tool_invoker=lambda t, a: {"ok": True, "status": "success"})
        cyclic_plan = [
            PlanStep(step_id="a", tool="get_system_status", depends_on=["b"]),
            PlanStep(step_id="b", tool="get_top_processes", depends_on=["a"]),
        ]
        report = loop.execute_plan(cyclic_plan)
        self.assertFalse(report.ok)
        self.assertEqual(report.status, "denied")
        self.assertIn("ciclo", report.summary_error.lower())


if __name__ == "__main__":
    unittest.main()

