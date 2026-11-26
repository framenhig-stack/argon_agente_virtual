"""
Ruta: modules/agent_loop.py
Descripción: Ciclo de ejecución agéntica estructurada (Fase 3).
Separa planificación, validación de dependencias, ejecución (secuencial vs. paralela segura),
observación de resultados reales y límites de seguridad contra bucles o inyección.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set

from config import Config
from modules.tool_policy import TOOL_SPECS

logger = logging.getLogger("AgentLoop")


@dataclass
class PlanStep:
    step_id: str
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class StepObservation:
    step_id: str
    tool: str
    status: str
    ok: bool
    output: Dict[str, Any]
    elapsed_ms: int = 0


@dataclass
class PlanExecutionReport:
    ok: bool
    status: str  # "success" | "partial" | "failed" | "approval_required" | "denied" | "limit_exceeded"
    observations: List[StepObservation] = field(default_factory=list)
    summary_error: str = ""


class AgentExecutionLoop:
    """
    Ejecuta un plan de pasos validando límites, dependencias (DAG) y aislamiento de datos.
    - Solo paraleliza pasos que NO tienen dependencias pendientes y cuyo nivel de riesgo es 'read'.
    - Los pasos de escritura ('local_write', 'external_write', 'sensitive') se ejecutan secuencialmente.
    - Si un paso padre falla o requiere aprobación, los pasos dependientes se omiten de forma segura.
    """

    def __init__(
        self,
        tool_invoker: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        max_steps: Optional[int] = None,
        max_parallel: Optional[int] = None,
        max_duration_seconds: Optional[float] = None,
    ) -> None:
        self.invoke_tool = tool_invoker
        self.max_steps = max_steps or getattr(Config, "MAX_PLAN_STEPS", 5)
        self.max_parallel = max_parallel or getattr(Config, "MAX_PARALLEL_TOOLS", 3)
        self.max_duration_seconds = max_duration_seconds or float(
            getattr(Config, "MAX_PLAN_DURATION_SECONDS", 45.0)
        )

    def validate_plan(self, steps: List[PlanStep]) -> Optional[str]:
        """Valida que el plan no sea vacío, no supere el límite de pasos y no tenga ciclos ni herramientas inválidas."""
        if not steps:
            return "El plan de ejecución está vacío."

        if len(steps) > self.max_steps:
            return (
                f"El plan solicita {len(steps)} pasos, superando el límite máximo de seguridad "
                f"({self.max_steps} pasos por instrucción)."
            )

        step_ids: Set[str] = set()
        for step in steps:
            if not step.step_id or step.step_id in step_ids:
                return f"Identificador de paso inválido o duplicado: '{step.step_id}'."
            if step.tool not in TOOL_SPECS:
                return f"El paso '{step.step_id}' intenta usar una herramienta no autorizada: '{step.tool}'."
            step_ids.add(step.step_id)

        # Verificar que todas las dependencias existan y detectar ciclos (DFS)
        adj: Dict[str, List[str]] = {s.step_id: list(s.depends_on) for s in steps}
        for s in steps:
            for dep in s.depends_on:
                if dep not in step_ids:
                    return f"El paso '{s.step_id}' depende de un paso inexistente: '{dep}'."
                if dep == s.step_id:
                    return f"El paso '{s.step_id}' no puede depender de sí mismo."

        visiting: Set[str] = set()
        visited: Set[str] = set()

        def _has_cycle(node: str) -> bool:
            visiting.add(node)
            for neighbor in adj.get(node, []):
                if neighbor in visiting:
                    return True
                if neighbor not in visited and _has_cycle(neighbor):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        for s_id in step_ids:
            if s_id not in visited and _has_cycle(s_id):
                return "El plan contiene una dependencia circular (ciclo infinito detectado)."

        return None

    @staticmethod
    def _extract_safe_observation_text(output: Dict[str, Any]) -> str:
        """
        Extrae un resumen seguro de la salida de un paso previo para inyectarlo como dato
        (nunca como instrucción ejecutable) en un paso dependiente.
        """
        for key in ("summary", "message", "context", "snippet", "title"):
            if key in output and isinstance(output[key], str):
                return output[key][:400]
        if "data" in output and isinstance(output["data"], dict):
            return json.dumps(output["data"], ensure_ascii=False)[:400]
        if "memories" in output and isinstance(output["memories"], list):
            notes = [str(m.get("note", "")) for m in output["memories"][:5] if isinstance(m, dict)]
            return "; ".join(notes)[:400]
        return json.dumps(output, ensure_ascii=False)[:400]

    def _resolve_step_args(
        self,
        raw_args: Dict[str, Any],
        completed_map: Dict[str, StepObservation],
    ) -> Dict[str, Any]:
        """
        Sustituye marcadores como '{{step_1.output}}' en los argumentos de un paso hijo
        usando la observación real verificada del paso padre.
        """
        resolved: Dict[str, Any] = {}
        pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_-]+)\.output\s*\}\}")

        for k, v in (raw_args or {}).items():
            if isinstance(v, str):
                def _replacer(match: re.Match[str]) -> str:
                    ref_id = match.group(1)
                    obs = completed_map.get(ref_id)
                    if not obs:
                        return ""
                    return self._extract_safe_observation_text(obs.output)

                resolved[k] = pattern.sub(_replacer, v)
            else:
                resolved[k] = v
        return resolved

    def execute_plan(self, steps: List[PlanStep]) -> PlanExecutionReport:
        """Ejecuta el plan respetando dependencias, concurrencia segura y límites de tiempo."""
        validation_err = self.validate_plan(steps)
        if validation_err:
            return PlanExecutionReport(
                ok=False,
                status="denied",
                observations=[],
                summary_error=validation_err,
            )

        start_time = time.time()
        completed: Dict[str, StepObservation] = {}
        observations: List[StepObservation] = []
        pending: List[PlanStep] = list(steps)

        while pending:
            if time.time() - start_time > self.max_duration_seconds:
                return PlanExecutionReport(
                    ok=False,
                    status="limit_exceeded",
                    observations=observations,
                    summary_error="Se agotó el tiempo máximo permitido para el plan de ejecución.",
                )

            # 1. Revisar si algún paso pendiente tiene una dependencia que falló o fue bloqueada
            still_waiting: List[PlanStep] = []
            ready_steps: List[PlanStep] = []

            for step in pending:
                failed_deps = [
                    dep for dep in step.depends_on
                    if dep in completed and not completed[dep].ok
                ]
                if failed_deps:
                    skipped_obs = StepObservation(
                        step_id=step.step_id,
                        tool=step.tool,
                        status="skipped_dependency",
                        ok=False,
                        output={
                            "ok": False,
                            "status": "skipped_dependency",
                            "error": f"Omitido porque el paso previo Requerido ({', '.join(failed_deps)}) no se completó.",
                        },
                        elapsed_ms=0,
                    )
                    completed[step.step_id] = skipped_obs
                    observations.append(skipped_obs)
                    continue

                if all(dep in completed and completed[dep].ok for dep in step.depends_on):
                    ready_steps.append(step)
                else:
                    still_waiting.append(step)

            if not ready_steps:
                break

            # 2. Separar pasos listos en lecturas paralelizables vs. escrituras secuenciales
            parallel_reads: List[PlanStep] = []
            sequential_steps: List[PlanStep] = []

            for step in ready_steps:
                spec = TOOL_SPECS.get(step.tool)
                if spec and spec.risk_level == "read" and not step.depends_on:
                    parallel_reads.append(step)
                else:
                    sequential_steps.append(step)

            # 3. Ejecutar lecturas independientes en paralelo (si hay más de 1)
            if len(parallel_reads) > 1:
                with ThreadPoolExecutor(max_workers=min(len(parallel_reads), self.max_parallel)) as pool:
                    future_map = {}
                    for step in parallel_reads:
                        resolved_args = self._resolve_step_args(step.args, completed)
                        t0 = time.time()
                        fut = pool.submit(self.invoke_tool, step.tool, resolved_args)
                        future_map[fut] = (step, t0)

                    for fut in as_completed(future_map):
                        step, t0 = future_map[fut]
                        elapsed = int((time.time() - t0) * 1000)
                        try:
                            res = fut.result(timeout=Config.TOOL_TIMEOUT_SECONDS)
                        except Exception as exc:
                            res = {"ok": False, "status": "failed", "error": str(exc)}
                        obs = StepObservation(
                            step_id=step.step_id,
                            tool=step.tool,
                            status=str(res.get("status", "failed")),
                            ok=bool(res.get("ok", False)),
                            output=res,
                            elapsed_ms=elapsed,
                        )
                        completed[step.step_id] = obs
                        observations.append(obs)
            else:
                sequential_steps = parallel_reads + sequential_steps

            # 4. Ejecutar pasos secuenciales o con efectos secundarios uno por uno en orden
            for step in sequential_steps:
                if time.time() - start_time > self.max_duration_seconds:
                    return PlanExecutionReport(
                        ok=False,
                        status="limit_exceeded",
                        observations=observations,
                        summary_error="Tiempo límite del plan excedido durante la ejecución secuencial.",
                    )

                resolved_args = self._resolve_step_args(step.args, completed)
                t0 = time.time()
                res = self.invoke_tool(step.tool, resolved_args)
                elapsed = int((time.time() - t0) * 1000)

                obs = StepObservation(
                    step_id=step.step_id,
                    tool=step.tool,
                    status=str(res.get("status", "failed")),
                    ok=bool(res.get("ok", False)),
                    output=res,
                    elapsed_ms=elapsed,
                )
                completed[step.step_id] = obs
                observations.append(obs)

            pending = still_waiting

        # 5. Calcular el estado global veraz del plan completo
        statuses = [o.status for o in observations]
        all_ok = all(o.ok for o in observations) and len(observations) == len(steps)
        any_ok = any(o.ok for o in observations)

        if "approval_required" in statuses:
            final_status = "approval_required"
        elif all_ok:
            final_status = "success"
        elif any_ok:
            final_status = "partial"
        elif all(s == "denied" for s in statuses):
            final_status = "denied"
        else:
            final_status = "failed"

        return PlanExecutionReport(
            ok=all_ok or final_status == "partial",
            status=final_status,
            observations=observations,
        )

