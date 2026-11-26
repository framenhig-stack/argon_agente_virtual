"""
Ruta: modules/tool_policy.py
Descripción: Motor central de políticas, validación de argumentos, niveles de riesgo
y aprobaciones vinculadas a argumentos para herramientas de Argon 4 (Fase 1).
"""
from dataclasses import dataclass
from modules.observability import metrics_collector
import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Literal, Optional
from config import Config

logger = logging.getLogger("ToolPolicy")

RiskLevel = Literal["read", "local_write", "external_write", "sensitive"]
ExecutionStatus = Literal["success", "failed", "partial", "approval_required", "denied", "timeout"]

ALLOWED_WINDOWS_APPS = {"calculadora", "bloc de notas", "explorador", "terminal"}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    risk_level: RiskLevel
    requires_approval: bool
    required_args: tuple[str, ...] = ()
    max_str_length: int = 1000


TOOL_SPECS: Dict[str, ToolSpec] = {
    "get_system_status": ToolSpec(
        name="get_system_status",
        description="Obtiene métricas de CPU, RAM y batería.",
        risk_level="read",
        requires_approval=False,
    ),
    "get_top_processes": ToolSpec(
        name="get_top_processes",
        description="Lista procesos con mayor uso de RAM.",
        risk_level="read",
        requires_approval=False,
    ),
    "recall_memories": ToolSpec(
        name="recall_memories",
        description="Consulta recuerdos almacenados en SQLite.",
        risk_level="read",
        requires_approval=False,
    ),
    "list_tasks": ToolSpec(
        name="list_tasks",
        description="Lista pendientes activos de agenda local y Notion.",
        risk_level="read",
        requires_approval=False,
    ),
    "search_web": ToolSpec(
        name="search_web",
        description="Realiza una búsqueda web en tiempo real.",
        risk_level="read",
        requires_approval=False,
        required_args=("query",),
        max_str_length=300,
    ),
    "save_memory": ToolSpec(
        name="save_memory",
        description="Guarda una nota en la memoria SQLite local.",
        risk_level="local_write",
        requires_approval=False,
        required_args=("note",),
        max_str_length=500,
    ),
    "search_memories": ToolSpec(
        name="search_memories",
        description="Busca recuerdos específicos por palabra clave o categoría en SQLite.",
        risk_level="read",
        requires_approval=False,
    ),
    "update_memory": ToolSpec(
        name="update_memory",
        description="Actualiza o corrige un recuerdo existente en SQLite por su ID.",
        risk_level="local_write",
        requires_approval=False,
        required_args=("mem_id", "new_note"),
        max_str_length=500,
    ),
    "delete_memory": ToolSpec(
        name="delete_memory",
        description="Elimina un recuerdo específico de SQLite por su ID.",
        risk_level="local_write",
        requires_approval=False,
        required_args=("mem_id",),
    ),
    "add_task": ToolSpec(
        name="add_task",
        description="Crea una tarea en agenda local y sincroniza con Notion si está activo.",
        risk_level="external_write",
        requires_approval=False,
        required_args=("title",),
        max_str_length=300,
    ),
    "read_clipboard": ToolSpec(
        name="read_clipboard",
        description="Lee el contenido actual del portapapeles del sistema.",
        risk_level="sensitive",
        requires_approval=False,
    ),
    "analyze_code_file": ToolSpec(
        name="analyze_code_file",
        description="Inspecciona el AST y contenido de un archivo dentro del proyecto.",
        risk_level="sensitive",
        requires_approval=False,
        required_args=("relative_path",),
        max_str_length=260,
    ),
    "check_emails": ToolSpec(
        name="check_emails",
        description="Consulta correos no leídos vía IMAP.",
        risk_level="sensitive",
        requires_approval=False,
    ),
    "open_application": ToolSpec(
        name="open_application",
        description="Abre una aplicación autorizada de Windows.",
        risk_level="local_write",
        requires_approval=False,
        required_args=("app_name",),
        max_str_length=60,
    ),
    "send_whatsapp": ToolSpec(
        name="send_whatsapp",
        description="Envía un mensaje de WhatsApp a un contacto externo.",
        risk_level="external_write",
        requires_approval=True,
        required_args=("message",),
        max_str_length=1000,
    ),
    "setup_windows_integration": ToolSpec(
        name="setup_windows_integration",
        description="Configura acceso directo o registro de auto-arranque en Windows.",
        risk_level="sensitive",
        requires_approval=True,
    ),
}


def normalize_tool_result(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Garantiza que toda respuesta de herramienta incluya un campo 'status' y 'ok' coherentes."""
    if not isinstance(raw_result, dict):
        return {"ok": False, "status": "failed", "error": "Formato de respuesta inválido."}

    result = dict(raw_result)
    if "status" in result:
        status = result["status"]
        if "ok" not in result:
            result["ok"] = status in ("success", "partial")
        return result

    ok_val = bool(result.get("ok", False))
    result["status"] = "success" if ok_val else "failed"
    result["ok"] = ok_val
    return result


class ToolPolicyEngine:
    """
    Controla la validación de esquemas, prevención de duplicados inmediatos (idempotencia)
    y autorización de acciones sensibles vinculadas a sus argumentos exactos.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._approved_actions: Dict[str, float] = {}
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._recent_calls: Dict[str, float] = {}
        self.dedup_window_seconds: float = 3.0

    @staticmethod
    def compute_action_id(tool_name: str, args: Dict[str, Any]) -> str:
        """Crea un hash determinista vinculado a la herramienta y sus argumentos exactos."""
        canonical_args = json.dumps(args or {}, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(f"{tool_name}:{canonical_args}".encode("utf-8")).hexdigest()[:12]
        return f"{tool_name}_{digest}"

    def validate_args(self, spec: ToolSpec, args: Dict[str, Any]) -> Optional[str]:
        """Valida argumentos requeridos, tipos básicos, longitudes y listas blancas."""
        if not isinstance(args, dict):
            return "Los argumentos deben ser un objeto JSON (dict)."

        for req in spec.required_args:
            val = args.get(req)
            if val is None or (isinstance(val, str) and not val.strip()):
                return f"Falta el argumento obligatorio '{req}' o está vacío."

        for key, val in args.items():
            if isinstance(val, str) and len(val) > spec.max_str_length:
                return f"El argumento '{key}' excede la longitud máxima permitida ({spec.max_str_length} caracteres)."

        if spec.name == "open_application":
            app_name = str(args.get("app_name", "")).strip().lower()
            if app_name not in ALLOWED_WINDOWS_APPS:
                return f"Aplicación '{app_name}' no autorizada. Permitidas: {', '.join(sorted(ALLOWED_WINDOWS_APPS))}."

        return None

    def approve_action(self, action_id: str, ttl_seconds: float = 300.0) -> bool:
        """Autoriza por única vez una acción específica pendiente."""
        with self._lock:
            self._approved_actions[action_id] = time.time() + ttl_seconds
            self._pending_requests.pop(action_id, None)
            logger.info(f"Acción autorizada por el usuario: {action_id}")
            return True

    def deny_action(self, action_id: str) -> bool:
        """Rechaza y elimina una solicitud de acción pendiente."""
        with self._lock:
            self._approved_actions.pop(action_id, None)
            self._pending_requests.pop(action_id, None)
            logger.info(f"Acción denegada por el usuario: {action_id}")
            return True

    def get_pending_approvals(self) -> list[Dict[str, Any]]:
        """Devuelve la lista de acciones que esperan confirmación del usuario."""
        with self._lock:
            return list(self._pending_requests.values())

    def _consume_approval_if_valid(self, action_id: str) -> bool:
        with self._lock:
            expiry = self._approved_actions.pop(action_id, None)
            if expiry is not None and time.time() <= expiry:
                return True
            return False

    def execute(
        self,
        tool_name: str,
        fn: Callable[..., Dict[str, Any]],
        args: Optional[Dict[str, Any]] = None,
        require_confirmation_override: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Valida permisos, argumentos e idempotencia antes de invocar cualquier herramienta,
        y registra métricas de duración y categoría de resultado (Fase 5).
        """
        t0 = time.perf_counter()
        clean_args = args or {}
        spec = TOOL_SPECS.get(tool_name)
        if not spec:
            err = f"Herramienta '{tool_name}' no registrada en la política de seguridad."
            metrics_collector.record_tool_execution(tool_name, "denied", (time.perf_counter() - t0) * 1000, err)
            return {"ok": False, "status": "denied", "error": err}

        # 1. Validación estricta de argumentos
        validation_error = self.validate_args(spec, clean_args)
        if validation_error:
            metrics_collector.record_tool_execution(
                tool_name, "denied", (time.perf_counter() - t0) * 1000, validation_error
            )
            return {
                "ok": False,
                "status": "denied",
                "tool": tool_name,
                "error": validation_error,
            }

        action_id = self.compute_action_id(tool_name, clean_args)

        # 2. Control de confirmación para acciones sensibles/externas
        policy_requires_conf = (
            Config.REQUIRE_CONFIRMATION
            if require_confirmation_override is None
            else require_confirmation_override
        )
        if spec.requires_approval and policy_requires_conf:
            if not self._consume_approval_if_valid(action_id):
                pending_info = {
                    "action_id": action_id,
                    "tool": tool_name,
                    "risk_level": spec.risk_level,
                    "args": clean_args,
                    "requested_at": time.strftime("%H:%M:%S"),
                }
                with self._lock:
                    self._pending_requests[action_id] = pending_info
                logger.warning(f"Ejecución bloqueada esperando aprobación: {action_id}")
                err_msg = (
                    f"La acción '{tool_name}' ({spec.risk_level}) requiere confirmación explícita "
                    f"antes de ejecutarse. ID de aprobación: {action_id}"
                )
                metrics_collector.record_tool_execution(
                    tool_name, "approval_required", (time.perf_counter() - t0) * 1000, err_msg
                )
                return {
                    "ok": False,
                    "status": "approval_required",
                    "action_id": action_id,
                    "tool": tool_name,
                    "risk_level": spec.risk_level,
                    "args": clean_args,
                    "error": err_msg,
                }

        # 3. Prevención de ejecuciones duplicadas accidentales (Idempotencia en escrituras)
        if spec.risk_level in ("local_write", "external_write", "sensitive") and spec.name in (
            "add_task",
            "send_whatsapp",
            "save_memory",
        ):
            now = time.time()
            with self._lock:
                last_ts = self._recent_calls.get(action_id, 0.0)
                if now - last_ts < self.dedup_window_seconds:
                    dup_err = f"Operación duplicada detectada para '{tool_name}'. Evitando doble ejecución."
                    metrics_collector.record_tool_execution(
                        tool_name, "denied", (time.perf_counter() - t0) * 1000, dup_err
                    )
                    return {
                        "ok": False,
                        "status": "denied",
                        "tool": tool_name,
                        "error": dup_err,
                    }
                self._recent_calls[action_id] = now

        # 4. Ejecución controlada y normalización del estado de salida
        try:
            raw_res = fn(**clean_args)
            normalized = normalize_tool_result(raw_res)
            normalized["tool"] = tool_name
            normalized["risk_level"] = spec.risk_level
            elapsed_ms = (time.perf_counter() - t0) * 1000
            metrics_collector.record_tool_execution(
                tool_name,
                str(normalized.get("status", "failed")),
                elapsed_ms,
                str(normalized.get("error", "")),
            )
            return normalized
        except TimeoutError as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"Timeout ejecutando {tool_name}: {exc}")
            metrics_collector.record_tool_execution(tool_name, "timeout", elapsed_ms, str(exc))
            return {"ok": False, "status": "timeout", "tool": tool_name, "error": str(exc)}
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.error(f"Excepción ejecutando {tool_name}: {exc}")
            metrics_collector.record_tool_execution(tool_name, "failed", elapsed_ms, str(exc))
            return {"ok": False, "status": "failed", "tool": tool_name, "error": str(exc)}

# Instancia global compartida por el enrutador, el orquestador y el servidor MCP
policy_engine = ToolPolicyEngine()