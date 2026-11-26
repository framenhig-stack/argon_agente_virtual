"""
Ruta: core_agent.py
Descripción: Núcleo y Cerebro Cognitivo de Argon 4 // Hermes Edition v4.5.
Aplica Separación de Preocupaciones (SoC), Arquitectura Local-First con proveedores
intercambiables (ProviderRouter) y Control Centralizado de Permisos (ToolPolicyEngine).
"""
import base64
import logging
import re
import threading
import time
from typing import Dict, Any, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config, write_telemetry_snapshot
from modules.voice_engine import VoiceEngine
from modules.system_tasks import SystemTasks
from modules.whatsapp_bridge import WhatsAppBridge
from modules.voip_caller import VoIPCaller
from modules.productivity_tools import ProductivityTools
from modules.advanced_skills import AdvancedSkills
from modules.notion_bridge import NotionBridge
from modules.tool_policy import policy_engine
from modules.tool_router import AgentToolRouter
from modules.llm_providers import OllamaProvider, GeminiProvider, ProviderRouter

logger = logging.getLogger("CoreAgent")


class ArgonHermesOrchestrator:
    def __init__(self) -> None:
        self.state = "IDLE"
        self.active_tool = "NONE"
        self.last_action = f"Núcleo Argon 4 // Hermes inicializado en modo {Config.ARGON_MODE}."
        self.handsfree = False
        self.ui_logs: List[Dict[str, str]] = []
        self.live_steps: List[Dict[str, str]] = []
        self.is_processing: bool = False
        self.task_start_ts: float = 0.0
        self._state_lock = threading.RLock()

        # Pool de conexiones HTTP persistentes para baja latencia
        self.http = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(total=2, backoff_factor=0.2)
        )
        self.http.mount("http://", adapter)
        self.http.mount("https://", adapter)

        self.voice = VoiceEngine(on_state_change=self._on_state_change)
        self.tasks = SystemTasks()
        self.whatsapp = WhatsAppBridge()
        self.voip = VoIPCaller()
        self.productivity = ProductivityTools()
        self.skills = AdvancedSkills()
        self.notion = NotionBridge()

        self.notion.export_rainmeter_skin()

        # Inicialización de Proveedores Desacoplados (Fase 2)
        self.ollama_provider = OllamaProvider(http_session=self.http)
        self.gemini_provider = GeminiProvider(http_session=self.http)
        self.ollama_online: bool = self.ollama_provider.is_available()
        self.gemini_online: bool = self.gemini_provider.is_available()
        self.active_model: str = self.ollama_provider.active_model
        self.last_provider_used: str = "ollama" if Config.ARGON_MODE != "cloud_first" else "gemini"

        self.provider_router = ProviderRouter(
            local_provider=self.ollama_provider,
            cloud_provider=self.gemini_provider,
            mode=Config.ARGON_MODE,
            cloud_fallback=Config.CLOUD_FALLBACK,
            allow_cloud_sensitive=Config.ALLOW_CLOUD_SENSITIVE_DATA,
        )

        self.system_prompt = (
            f"Eres {Config.AGENT_NAME} (Edición Hermes), un sistema agéntico multimodal avanzado estilo J.A.R.V.I.S. "
            f"operando en modo '{Config.ARGON_MODE}' en Windows 11. Tu voz es grave, serena y futurista. "
            "Cuentas con visión de pantalla bajo permiso, memoria persistente SQLite, agenda sincronizada con Notion, "
            "triaje de correo y WhatsApp con confirmación de seguridad. Responde siempre en español con precisión "
            "ejecutiva en 1 a 3 oraciones claras y nunca afirmes que una acción se completó si requirió aprobación o falló."
        )
        self.chat_history: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        past_turns = self.skills.load_recent_conversation(limit=8)
        if past_turns:
            self.chat_history.extend(past_turns)

        self.router = AgentToolRouter(self, policy=policy_engine)
        write_telemetry_snapshot(self.state, self.active_tool, self.last_action)

    # ---------------- TRAZABILIDAD EN VIVO ----------------
    def start_live_trace(self, initial_label: str) -> None:
        with self._state_lock:
            self.is_processing = True
            self.task_start_ts = time.time()
            self.live_steps = [{
                "label": initial_label,
                "status": "running",
                "elapsed": "0.0s"
            }]

    def push_live_step(self, label: str, status: str = "running") -> None:
        with self._state_lock:
            now_elapsed = f"{round(time.time() - self.task_start_ts, 1)}s" if self.task_start_ts else "0.1s"
            for step in self.live_steps:
                if step["status"] == "running":
                    step["status"] = "done"
                    step["elapsed"] = now_elapsed
            self.live_steps.append({
                "label": label,
                "status": status,
                "elapsed": now_elapsed
            })

    def finish_live_trace(self) -> None:
        with self._state_lock:
            now_elapsed = f"{round(time.time() - self.task_start_ts, 1)}s" if self.task_start_ts else "0.1s"
            for step in self.live_steps:
                if step["status"] == "running":
                    step["status"] = "done"
                    step["elapsed"] = now_elapsed
            self.is_processing = False

    def _on_state_change(self, new_state: str) -> None:
        with self._state_lock:
            self.state = new_state
            write_telemetry_snapshot(self.state, self.active_tool, self.last_action)

    def _set_tool_telemetry(self, tool_name: str, description: str) -> None:
        self.push_live_step(f"[{tool_name}] {description}")
        with self._state_lock:
            self.active_tool = tool_name
            self.last_action = description
            self.state = "TOOL_EXEC" if tool_name != "NONE" else "IDLE"
            write_telemetry_snapshot(self.state, self.active_tool, self.last_action)

    def add_log(self, sender: str, text: str, tag: str = "agent") -> None:
        with self._state_lock:
            self.ui_logs.append({"sender": sender, "text": text, "tag": tag})
            if len(self.ui_logs) > 60:
                self.ui_logs = self.ui_logs[-60:]

    def respond(self, text: str) -> str:
        self.push_live_step("Sintetizando voz neuronal grave (-14Hz)...", status="done")
        self.finish_live_trace()
        with self._state_lock:
            self.last_action = text
            self.active_tool = "VOICE_SYNTH"
            write_telemetry_snapshot("SPEAKING", self.active_tool, self.last_action)
        self.add_log(Config.AGENT_NAME.upper(), text, "agent")
        self.skills.log_conversation_turn("assistant", text)
        self.voice.speak(text)
        with self._state_lock:
            self.active_tool = "NONE"
            self.state = "IDLE"
            write_telemetry_snapshot("IDLE", self.active_tool, self.last_action)
        return text

    # ---------------- VISIÓN MULTIMODAL DE PANTALLA (CON COMPUERTA DE PRIVACIDAD) ----------------
    def analyze_screen_with_gemini(self, user_prompt: str) -> str:
        """
        Captura la pantalla actual de Windows 11 y la analiza respetando la política Local-First.
        No envía la captura a la nube en modo strict_local ni sin permiso explícito.
        """
        self._set_tool_telemetry("SCREEN_VISION", "Capturando pantalla en alta resolución...")
        snap = self.tasks.take_screenshot()
        if not snap.get("ok"):
            return f"No pude capturar la pantalla: {snap.get('error')}"

        filepath = snap["filepath"]
        try:
            with open(filepath, "rb") as img_file:
                b64_img = base64.b64encode(img_file.read()).decode("utf-8")

            prompt_text = (
                f"El usuario solicita analizar su pantalla actual en Windows 11. "
                f"Solicitud: '{user_prompt}'. Responde en español de forma directa, técnica y ejecutiva."
            )
            self._set_tool_telemetry("SCREEN_VISION", f"Evaluando imagen bajo modo {Config.ARGON_MODE}...")
            res = self.provider_router.analyze_screen_image(
                prompt_text=prompt_text,
                base64_png=b64_img,
                system_prompt=self.system_prompt,
            )
            if res.ok:
                self.last_provider_used = f"{res.provider} ({res.model})"
                return res.text
            return res.error
        except Exception as exc:
            logger.error(f"Error en análisis de pantalla: {exc}")
            return f"Ocurrió un error al analizar la pantalla: {exc}"

    # ---------------- MOTOR DE RAZONAMIENTO DESACOPLADO (LOCAL-FIRST) ----------------
    def ask_brain(
        self,
        user_prompt: str,
        extra_context: str = "",
        contains_sensitive_data: bool = False,
    ) -> str:
        """
        Enruta el razonamiento a través de ProviderRouter respetando ARGON_MODE
        (local_first, strict_local o cloud_first) y protegiendo datos sensibles.
        """
        self.push_live_step("Consultando memoria cognitiva SQLite...")
        memories = self.skills.recall_memories(limit=8, query=user_prompt)
        mem_block = ""
        if memories:
            facts = "; ".join([f"[{m['category']}] {m['note']}" for m in memories])
            mem_block = f"\n[MEMORIA PERMANENTE SOBRE USUARIO: {facts}]"

        full_user_msg = f"{user_prompt}{mem_block}"
        if extra_context:
            full_user_msg += f"\n{extra_context}"

        with self._state_lock:
            self.chat_history.append({"role": "user", "content": full_user_msg})
            if len(self.chat_history) > 15:
                self.chat_history = [self.chat_history[0]] + self.chat_history[-14:]
            history_snapshot = list(self.chat_history)

        self._set_tool_telemetry("LLM_ROUTER", f"Razonando en modo {Config.ARGON_MODE}...")
        try:
            llm_res = self.provider_router.chat(
                messages=history_snapshot,
                system_prompt=self.system_prompt,
                contains_sensitive_data=contains_sensitive_data,
            )
            if llm_res.ok:
                self.last_provider_used = f"{llm_res.provider} ({llm_res.model})"
                with self._state_lock:
                    self.chat_history.append({"role": "assistant", "content": llm_res.text})
                return llm_res.text
            return llm_res.error
        finally:
            with self._state_lock:
                self.state = "IDLE"

    def get_unified_calendar(self) -> List[Dict[str, Any]]:
        """Combina los pendientes locales con las tareas de Notion API si están activas."""
        local_events = self.productivity.list_calendar_events()
        notion_events = self.notion.fetch_tasks(limit=4)
        return notion_events + local_events

    def execute_approved_action(self, action_id: str) -> str:
        """Aprueba y ejecuta inmediatamente una acción que estaba en espera de confirmación."""
        pending = {p["action_id"]: p for p in policy_engine.get_pending_approvals()}
        target = pending.get(action_id)
        if not target:
            return f"No encontré ninguna acción pendiente con el identificador {action_id}."

        policy_engine.approve_action(action_id)
        tool_name = target["tool"]
        args = target["args"]

        if tool_name == "setup_windows_integration":
            res = policy_engine.execute(
                "setup_windows_integration",
                self.skills.setup_windows_integration,
                args,
            )
        else:
            res = self.router.invoke_tool(tool_name, args)

        if res.get("ok"):
            return f"Acción '{tool_name}' autorizada y ejecutada correctamente."
        return f"La acción '{tool_name}' fue autorizada pero devolvió un fallo: {res.get('error')}"

    def process_command(self, user_text: str) -> str:
        self.start_live_trace(f"Analizando instrucción: '{user_text[:45]}...'")
        text = user_text.lower().strip()
        self.skills.log_conversation_turn("user", user_text)
        self.skills.auto_extract_memory(user_text)

        # 0. GESTIÓN DE APROBACIONES DE SEGURIDAD Y NUBE
        if text in ("aprobar nube", "autorizar nube", "usar nube"):
            self.provider_router.approve_cloud_once()
            return self.respond("Autorización temporal concedida para usar el proveedor en la nube en tu siguiente consulta.")

        if text.startswith(("aprobar acción", "aprobar accion", "confirmar acción", "confirmar accion")):
            pending_list = policy_engine.get_pending_approvals()
            if not pending_list:
                return self.respond("No hay acciones pendientes de aprobación en este momento.")
            latest_id = pending_list[-1]["action_id"]
            msg = self.execute_approved_action(latest_id)
            return self.respond(msg)

        if text.startswith(("rechazar acción", "rechazar accion", "cancelar acción", "cancelar accion")):
            pending_list = policy_engine.get_pending_approvals()
            if not pending_list:
                return self.respond("No hay acciones pendientes para cancelar.")
            latest_id = pending_list[-1]["action_id"]
            policy_engine.deny_action(latest_id)
            return self.respond(f"Acción pendiente {latest_id} cancelada y descartada por seguridad.")
        
        # 0.5 TAREAS COMPUESTAS Y ENCADENAMIENTO SECUENCIAL (FASE 3)
        if any(seq in text for seq in (" luego ", " después ", " despues ", " y además ", " y ademas ")):
            self.push_live_step("Planificando ejecución multi-paso con control de dependencias...")
            compound_reply = self.router.route_and_execute(user_text)
            if compound_reply is not None:
                return self.respond(compound_reply)
            
        # 1. VISIÓN MULTIMODAL DE PANTALLA
        if any(k in text for k in [
            "mira mi pantalla", "analiza mi pantalla", "qué ves en mi pantalla",
            "que ves en mi pantalla", "captura de pantalla", "qué hay en mi pantalla"
        ]):
            reply = self.analyze_screen_with_gemini(user_text)
            return self.respond(reply)

        # 2. MEMORIA PERSISTENTE Y GOBERNANZA DE RECUERDOS (FASE 4)
        if any(k in text for k in ["recuerda que", "memoriza que", "guarda en tu memoria", "no olvides que"]):
            cleaned = re.sub(
                r"^(recuerda que|memoriza que|guarda en tu memoria|no olvides que)\s*:?\s*",
                "",
                user_text,
                flags=re.IGNORECASE
            ).strip()
            res = self.router.invoke_tool("save_memory", {"note": cleaned, "category": "Clave"})
            return self.respond(
                f"Registrado en mi núcleo de memoria permanente (#{res.get('id')}): {cleaned}."
                if res.get("ok") else str(res.get("error"))
            )

        del_match = re.search(
            r"(?:olvida|borra|elimina)\s+(?:el\s+)?recuerdo\s*#?\s*(\d+)",
            text,
            flags=re.IGNORECASE,
        )
        if del_match:
            mem_id = int(del_match.group(1))
            res = self.router.invoke_tool("delete_memory", {"mem_id": mem_id})
            return self.respond(
                f"He eliminado el recuerdo #{mem_id} de mi base de datos permanente."
                if res.get("ok") else str(res.get("error"))
            )

        upd_match = re.search(
            r"(?:actualiza|corrige)\s+(?:el\s+)?recuerdo\s*#?\s*(\d+)\s*(?:con|a|:)\s*(.+)",
            user_text,
            flags=re.IGNORECASE,
        )
        if upd_match:
            mem_id = int(upd_match.group(1))
            new_note = upd_match.group(2).strip()
            res = self.router.invoke_tool("update_memory", {"mem_id": mem_id, "new_note": new_note})
            return self.respond(
                f"Recuerdo #{mem_id} actualizado correctamente a: {new_note}."
                if res.get("ok") else str(res.get("error"))
            )

        if any(k in text for k in ["qué recuerdas", "que recuerdas", "qué sabes de mí", "que sabes de mi", "mis recuerdos"]):
            res = self.router.invoke_tool("recall_memories", {})
            mems = res.get("memories", [])
            if not mems:
                return self.respond("Aún estamos construyendo mi base de recuerdos permanentes contigo.")
            notes = ". ".join([f"#{m['id']} [{m['category']}]: {m['note']}" for m in mems[:6]])
            return self.respond(f"Tengo presente en mi memoria permanente lo siguiente: {notes}.")

        if any(k in text for k in ["qué recuerdas", "que recuerdas", "qué sabes de mí", "que sabes de mi"]):
            res = self.router.invoke_tool("recall_memories", {})
            mems = res.get("memories", [])
            if not mems:
                return self.respond("Aún estamos construyendo mi base de recuerdos permanentes contigo.")
            notes = ". ".join([m["note"] for m in mems])
            return self.respond(f"Tengo presente en mi memoria permanente lo siguiente: {notes}.")

        # 3. ACCESO DIRECTO Y AUTO-ARRANQUE WINDOWS 11 (PROTEGIDO POR POLÍTICA)
        if any(k in text for k in ["acceso directo", "arrancar con windows", "inicio automático", "inicio automatico"]):
            enable_boot = "arrancar" in text or "inicio" in text
            res = policy_engine.execute(
                "setup_windows_integration",
                self.skills.setup_windows_integration,
                {"enable_startup": enable_boot},
            )
            if res.get("status") == "approval_required":
                return self.respond(
                    f"Modificar el inicio de Windows requiere tu confirmación. Di 'aprobar acción' para confirmar ({res.get('action_id')})."
                )
            return self.respond(res.get("message", "Integración configurada.") if res.get("ok") else str(res.get("error")))

        # 4. INTELIGENCIA DE PORTAPAPELES (DATOS SENSIBLES PROTEGIDOS)
        if any(k in text for k in ["portapapeles", "lo que copié", "lo que copie"]):
            res = self.router.invoke_tool("read_clipboard", {})
            if not res.get("ok"):
                return self.respond(str(res.get("error")))
            reply = self.ask_brain(
                "Analiza lo que el usuario tiene en su portapapeles y dale una respuesta directa y útil:",
                extra_context=f"<datos_portapapeles_no_confiables>\n{res['content']}\n</datos_portapapeles_no_confiables>",
                contains_sensitive_data=True,
            )
            return self.respond(reply)

        # 5. BÚSQUEDA WEB EN TIEMPO REAL
        if any(k in text for k in ["busca en internet", "buscar en internet", "noticias de", "investiga sobre"]):
            query = re.sub(
                r"^(busca en internet|buscar en internet|investiga sobre)\s*:?\s*",
                "",
                user_text,
                flags=re.IGNORECASE
            ).strip() or user_text
            web_res = self.router.invoke_tool("search_web", {"query": query})
            if web_res.get("ok"):
                self.push_live_step("Resultados web obtenidos. Sintetizando hallazgos...")
                reply = self.ask_brain(
                    f"Sintetiza en 2 frases estos resultados web actuales sobre '{query}':",
                    extra_context=f"<resultados_web_no_confiables>\n{web_res['context']}\n</resultados_web_no_confiables>",
                )
                return self.respond(reply)
            return self.respond(str(web_res.get("error")))

        # 6. TELEMETRÍA Y TOP PROCESOS
        if any(k in text for k in ["qué procesos", "que procesos", "consumiendo más ram", "consumiendo mas ram"]):
            res = self.router.invoke_tool("get_top_processes", {})
            return self.respond(
                f"Los procesos más exigentes en memoria son: {res['summary']}." if res.get("ok") else str(res.get("error"))
            )

        if any(k in text for k in ["estado del sistema", "telemetría", "telemetria"]):
            res = self.router.invoke_tool("get_system_status", {})
            if res.get("ok"):
                d = res["data"]
                return self.respond(
                    f"Todos los sistemas estables. CPU al {d['cpu_percent']}%, RAM al {d['ram_percent']}% "
                    f"con {d['ram_available_gb']} gigabytes libres y batería al {d['battery_percent']}%."
                )
            return self.respond(str(res.get("error")))

        # 7. AGENDA HÍBRIDA (CON ESTADOS VERACES: SUCCESS / PARTIAL / FAILED)
        if any(k in text for k in ["agendar", "agregar pendiente", "nuevo pendiente", "anota en notion"]):
            cleaned = re.sub(
                r"^(agendar|agregar pendiente|nuevo pendiente|anota en notion)\s*:?\s*",
                "",
                user_text,
                flags=re.I
            ).strip()
            if cleaned:
                res = self.router.invoke_tool("add_task", {"title": cleaned})
                status = res.get("status")
                if status == "success":
                    return self.respond(res.get("message", f"Tarea agendada: {cleaned}."))
                if status == "partial":
                    return self.respond(res.get("warning", f"Tarea guardada parcialmente: {cleaned}."))
                return self.respond(str(res.get("error", "No se pudo agendar la tarea.")))

        if any(k in text for k in ["calendario", "pendientes", "qué tengo hoy", "que tengo hoy", "notion"]):
            res = self.router.invoke_tool("list_tasks", {})
            evs = res.get("events", [])
            if not evs:
                return self.respond("No tienes pendientes activos en tu agenda ni en Notion.")
            titles = ", ".join([f"{e['id']}: {e['title']}" for e in evs[:4]])
            return self.respond(f"Tus pendientes activos son: {titles}.")

        # 8. CORREOS Y AUDITORÍA DE CÓDIGO (CON VALIDACIÓN CANÓNICA Y PROTECCIÓN DE PRIVACIDAD)
        if any(k in text for k in ["revisar correo", "revisar correos", "mis correos"]):
            res = self.router.invoke_tool("check_emails", {})
            return self.respond(res["summary"] if res.get("ok") else str(res.get("error")))

        if any(k in text for k in ["revisar código", "revisar codigo", "analizar código", "analizar codigo"]):
            file_match = re.search(r"([a-zA-Z0-9_./\\-]+\.(?:py|js|ts|tsx|jsx|json|txt|md))", user_text)
            target_file = file_match.group(1) if file_match else "core_agent.py"
            res = self.router.invoke_tool("analyze_code_file", {"relative_path": target_file})
            if not res.get("ok"):
                return self.respond(str(res.get("error")))
            reply = self.ask_brain(
                f"Evalúa técnicamente este código ({res['filepath']}, {res['syntax']}):",
                extra_context=res["snippet"],
                contains_sensitive_data=True,
            )
            return self.respond(reply)

        # 9. APLICACIONES, WHATSAPP Y VOIP (CON POLÍTICA DE CONFIRMACIÓN)
        for app_name in ["calculadora", "bloc de notas", "explorador", "terminal"]:
            if f"abrir {app_name}" in text or f"abre la {app_name}" in text:
                res = self.router.invoke_tool("open_application", {"app_name": app_name})
                return self.respond(f"Desplegando {app_name}." if res.get("ok") else str(res.get("error")))

        if "whatsapp" in text:
            match = re.search(r"(\+?\d[\d\s\-]{7,}\d).*?(?:diciendo|mensaje|que diga)\s+(.+)", user_text, re.I)
            if match:
                phone, msg = match.group(1).strip(), match.group(2).strip()
            else:
                msg_match = re.search(r"(?:diciendo|mensaje|que diga)\s+(.+)", user_text, re.I)
                phone = Config.DEFAULT_TARGET_PHONE
                msg = msg_match.group(1).strip() if msg_match else ""

            if phone and msg:
                res = self.router.invoke_tool("send_whatsapp", {"message": msg, "phone": phone})
                if res.get("status") == "approval_required":
                    return self.respond(
                        f"Por seguridad, enviar WhatsApp a {phone} requiere confirmación. "
                        f"Di 'aprobar acción' para enviarlo ({res.get('action_id')})."
                    )
                return self.respond("Mensaje de WhatsApp entregado." if res.get("ok") else str(res.get("error")))
            return self.respond("Dime qué mensaje deseas enviar por WhatsApp, por ejemplo: 'Enviar WhatsApp diciendo Hola'.")

        if "sala de voz" in text or "webrtc" in text:
            self._set_tool_telemetry("VOIP_WEBRTC", "Creando sala WebRTC")
            res = self.voip.start_webrtc_room()
            if res.get("ok"):
                return self.respond("Canal de voz WebRTC abierto.")
            return self.respond("No se pudo abrir la sala de voz.")

        # 10. ENRUTADOR DE HERRAMIENTAS INTELIGENTE + CONVERSACIÓN
        self.push_live_step(f"Evaluando herramientas nativas ({Config.ARGON_MODE})...")
        routed_reply = self.router.route_and_execute(user_text)
        if routed_reply is not None:
            return self.respond(routed_reply)

        reply = self.ask_brain(user_text)
        return self.respond(reply)