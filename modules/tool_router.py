"""
Ruta: modules/tool_router.py
Descripción: Motor de Tool Calling Nativo con Control Central de Permisos (ToolPolicyEngine),
estados veraces y enrutamiento desacoplado de proveedores LLM (Fases 1 y 2).
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List
from config import Config
from modules.productivity_tools import build_unified_task_result
from modules.tool_policy import ToolPolicyEngine, policy_engine
from modules.agent_loop import AgentExecutionLoop, PlanStep

logger = logging.getLogger("ToolRouter")


class AgentToolRouter:
    def __init__(self, orchestrator: Any, policy: ToolPolicyEngine | None = None) -> None:
        self.core = orchestrator
        self.policy = policy or policy_engine
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = AgentExecutionLoop(tool_invoker=self.invoke_tool)
        self.registry: Dict[str, Callable[..., Dict[str, Any]]] = {
            "save_memory": self._tool_save_memory,
            "recall_memories": self._tool_recall_memories,
            "search_web": self._tool_search_web,
            "read_clipboard": self._tool_read_clipboard,
            "get_system_status": self._tool_system_status,
            "get_top_processes": self._tool_top_processes,
            "add_task": self._tool_add_task,
            "list_tasks": self._tool_list_tasks,
            "check_emails": self._tool_check_emails,
            "send_whatsapp": self._tool_send_whatsapp,
            "open_application": self._tool_open_application,
            "analyze_code_file": self._tool_analyze_code_file,
            "search_memories": self._tool_search_memories,
            "update_memory": self._tool_update_memory,
            "delete_memory": self._tool_delete_memory,
        }

        self.function_declarations: List[Dict[str, Any]] = [
            {
                "name": "save_memory",
                "description": "Guarda un dato, preferencia o hecho importante en la memoria permanente SQLite.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "note": {"type": "STRING", "description": "El hecho o nota a recordar."},
                        "category": {"type": "STRING", "description": "Categoría (Clave, Proyecto, Preferencia)."}
                    },
                    "required": ["note"]
                }
            },
            {
                "name": "search_web",
                "description": "Busca información o noticias en tiempo real en internet.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Término de búsqueda web."}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_clipboard",
                "description": "Lee el texto actual copiado en el portapapeles de Windows.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "get_system_status",
                "description": "Obtiene el uso actual de CPU, RAM, disco y batería del sistema.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "get_top_processes",
                "description": "Lista los procesos que más memoria RAM están consumiendo.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "add_task",
                "description": "Agenda una tarea o pendiente en el calendario local y en Notion API.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "Título de la tarea o evento a agendar."}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "list_tasks",
                "description": "Lista las tareas y pendientes activos de la agenda local y Notion.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "check_emails",
                "description": "Revisa los correos electrónicos no leídos en la bandeja IMAP.",
                "parameters": {"type": "OBJECT", "properties": {}}
            },
            {
                "name": "send_whatsapp",
                "description": "Envía un mensaje de WhatsApp a un número o al teléfono por defecto.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "message": {"type": "STRING", "description": "Texto del mensaje a enviar."},
                        "phone": {"type": "STRING", "description": "Número destino opcional."}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "open_application",
                "description": "Abre una aplicación de Windows (calculadora, bloc de notas, explorador, terminal).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "app_name": {
                            "type": "STRING",
                            "description": "Nombre de la aplicación: calculadora, bloc de notas, explorador o terminal."
                        }
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "analyze_code_file",
                "description": "Inspecciona un archivo de código dentro del directorio del proyecto.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "relative_path": {"type": "STRING", "description": "Ruta relativa del archivo dentro del proyecto."}
                    },
                    "required": ["relative_path"]
                }
            },
        ]

        self.ollama_tools: List[Dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": d["name"],
                    "description": d["description"],
                    "parameters": json.loads(
                        json.dumps(d["parameters"]).replace('"OBJECT"', '"object"').replace('"STRING"', '"string"')
                    )
                }
            }
            for d in self.function_declarations
        ]

    # ---------------- WRAPPERS DE HERRAMIENTAS ----------------
    def _tool_save_memory(self, note: str, category: str = "Clave") -> Dict[str, Any]:
        return self.core.skills.save_memory(note, category=category)

    def _tool_recall_memories(self) -> Dict[str, Any]:
        return {"ok": True, "status": "success", "memories": self.core.skills.recall_memories(limit=8)}

    def _tool_search_memories(self, query: str = "", category: str = "") -> Dict[str, Any]:
     return self.core.skills.search_memories(query=query, category=category, limit=8)

    def _tool_update_memory(self, mem_id: int, new_note: str, category: str = "") -> Dict[str, Any]:
     return self.core.skills.update_memory(int(mem_id), new_note, category=category or None)

    def _tool_delete_memory(self, mem_id: int) -> Dict[str, Any]:
         return self.core.skills.delete_memory(int(mem_id))
    
    def _tool_search_web(self, query: str) -> Dict[str, Any]:
        return self.core.skills.search_web(query)

    def _tool_read_clipboard(self) -> Dict[str, Any]:
        return self.core.skills.read_clipboard()

    def _tool_system_status(self) -> Dict[str, Any]:
        return self.core.tasks.get_system_status()

    def _tool_top_processes(self) -> Dict[str, Any]:
        return self.core.skills.get_top_processes()

    def _tool_add_task(self, title: str) -> Dict[str, Any]:
        local_res = self.core.productivity.add_calendar_event(title)
        notion_enabled = bool(getattr(self.core.notion, "enabled", False))
        notion_res = self.core.notion.create_task(title) if notion_enabled else {"ok": False, "error": "Notion desactivado"}
        return build_unified_task_result(
            title=title,
            local_res=local_res,
            notion_res=notion_res,
            notion_enabled=notion_enabled,
        )

    def _tool_list_tasks(self) -> Dict[str, Any]:
        return {"ok": True, "status": "success", "events": self.core.get_unified_calendar()[:6]}

    def _tool_check_emails(self) -> Dict[str, Any]:
        return self.core.productivity.check_emails()

    def _tool_send_whatsapp(self, message: str, phone: str = "") -> Dict[str, Any]:
        target = phone.strip() if phone else Config.DEFAULT_TARGET_PHONE
        if not target:
            return {
                "ok": False,
                "status": "failed",
                "error": "No se especificó número de teléfono ni existe DEFAULT_TARGET_PHONE.",
            }
        return self.core.whatsapp.send_message(target, message)

    def _tool_open_application(self, app_name: str) -> Dict[str, Any]:
        return self.core.tasks.open_application(app_name)

    def _tool_analyze_code_file(self, relative_path: str) -> Dict[str, Any]:
        return self.core.productivity.analyze_code_file(relative_path)

    # ---------------- EJECUCIÓN CENTRALIZADA CON POLÍTICAS ----------------
    def invoke_tool(self, fn_name: str, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Punto único de ejecución de cualquier herramienta pasando por ToolPolicyEngine."""
        clean_args = args or {}
        fn = self.registry.get(fn_name)
        if not fn:
            return {
                "ok": False,
                "status": "denied",
                "tool": fn_name,
                "error": f"Herramienta '{fn_name}' no registrada.",
            }

        self.core._set_tool_telemetry(fn_name.upper(), f"Validando y ejecutando {fn_name}...")
        return self.policy.execute(fn_name, fn, clean_args)

    def execute_parallel_calls(
        self,
        normalized_calls: List[Dict[str, Any]],
        force_sequential: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Convierte las llamadas propuestas en un Plan estructurado y lo ejecuta a través de
        AgentExecutionLoop (paralelizando solo lecturas independientes y encadenando pasos secuenciales).
        """
        from modules.tool_policy import TOOL_SPECS

        plan_steps: List[PlanStep] = []
        prev_step_id: str | None = None

        for idx, call in enumerate(normalized_calls, start=1):
            fn_name = call.get("name", "")
            args = call.get("args", {}) or {}
            step_id = call.get("step_id") or f"step_{idx}"
            explicit_deps = call.get("depends_on")

            if explicit_deps is not None:
                deps = list(explicit_deps)
            elif force_sequential and prev_step_id is not None:
                deps = [prev_step_id]
            else:
                # Si la herramienta modifica estado ('local_write', 'external_write', 'sensitive'),
                # encadenarla tras el paso anterior para evitar carreras o efectos desordenados
                spec = TOOL_SPECS.get(fn_name)
                if spec and spec.risk_level != "read" and prev_step_id is not None:
                    deps = [prev_step_id]
                else:
                    deps = []

            plan_steps.append(
                PlanStep(
                    step_id=step_id,
                    tool=fn_name,
                    args=args,
                    depends_on=deps,
                )
            )
            prev_step_id = step_id

        report = self.loop.execute_plan(plan_steps)
        if not report.observations and report.summary_error:
            return [{"tool": "plan_validator", "result": {"ok": False, "status": report.status, "error": report.summary_error}}]

        return [
            {"step_id": obs.step_id, "tool": obs.tool, "status": obs.status, "result": obs.output}
            for obs in report.observations
        ]

    def route_and_execute(self, user_text: str) -> str | None:
        """
        Utiliza el ProviderRouter desacoplado para seleccionar herramientas y las ejecuta
        mediante AgentExecutionLoop respetando dependencias secuenciales y modo de privacidad.
        """
        provider_router = getattr(self.core, "provider_router", None)
        if provider_router is not None:
            llm_res = provider_router.route_tools(
                user_text=user_text,
                system_prompt=self.core.system_prompt,
                gemini_declarations=self.function_declarations,
                ollama_tools=self.ollama_tools,
            )
            if not llm_res.ok or not llm_res.tool_calls:
                return None

            text_lower = user_text.lower()
            is_sequential = any(
                seq_word in text_lower
                for seq_word in (" luego ", " después ", " despues ", " a continuación ", " y guarda ")
            )
            tool_outputs = self.execute_parallel_calls(
                llm_res.tool_calls,
                force_sequential=is_sequential,
            )
            context_str = json.dumps(tool_outputs, ensure_ascii=False)
            return self.core.ask_brain(
                "Informa al usuario con total veracidad el resultado de cada paso ejecutado "
                "(si algún paso devolvió 'approval_required', 'skipped_dependency', 'partial' o 'failed', "
                f"explícalo con exactitud sin afirmar que se completó): '{user_text}'",
                extra_context=f"<observaciones_herramientas>\n{context_str}\n</observaciones_herramientas>",
            )

        return None