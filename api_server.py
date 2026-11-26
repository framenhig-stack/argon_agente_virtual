"""
Ruta: api_server.py
Descripción: Servidor API Asíncrono de Alto Rendimiento (FastAPI + Uvicorn).
Conecta el núcleo de Argon 4 (Fases 1 a 5) con la nueva HUD Táctica diseñada en Google Stitch.
"""
import logging
import threading
import time
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import Config
from core_agent import ArgonHermesOrchestrator
from modules.observability import metrics_collector
from modules.tool_policy import policy_engine

logger = logging.getLogger("APIServer")

app = FastAPI(
    title="Argon 4 // Hermes Tactical OS API",
    description="Backend FastAPI Local-First para el Frontend React HUD y telemetría Rainmeter",
    version="4.7.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

core = ArgonHermesOrchestrator()


class CommandRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Texto de la orden para el agente.")
    prompt: Optional[str] = Field(default=None, description="Campo alternativo enviado por React Terminal.")


class VoiceProfileRequest(BaseModel):
    voice: Optional[str] = Field(default="es-ES-AlvaroNeural")
    pitch: Optional[str] = Field(default="-14Hz")
    rate: Optional[str] = Field(default="+6%")


class ShortcutRequest(BaseModel):
    startup: bool = Field(default=False)


class MemoryCreateRequest(BaseModel):
    note: str = Field(..., description="Contenido del recuerdo a guardar en SQLite.")
    category: str = Field(default="Proyecto", description="Categoría del recuerdo.")


class MemoryUpdateRequest(BaseModel):
    note: str = Field(..., description="Nuevo contenido del recuerdo.")
    category: Optional[str] = Field(default=None, description="Categoría opcional.")


class TaskCreateRequest(BaseModel):
    title: str = Field(..., description="Título de la tarea a crear.")
    target: str = Field(default="both", description="Destino: local | notion | both")


# ---------------- ENDPOINTS DE ESTADO, TELEMETRÍA Y OBSERVABILIDAD ----------------

@app.get("/telemetry")
async def rainmeter_telemetry() -> Dict[str, Any]:
    """Endpoint consumido por el widget de escritorio de Rainmeter (skins/HUD_Agent.ini)."""
    st = core.tasks.get_system_status()
    d = st["data"] if st["ok"] else {"cpu_percent": 0, "ram_percent": 0, "battery_percent": 100}
    return {
        "status": core.state,
        "tool": core.active_tool,
        "last_action": core.last_action,
        "updated_at": time.strftime("%H:%M:%S"),
        "cpu": d["cpu_percent"],
        "ram": d["ram_percent"],
        "battery": d["battery_percent"],
    }


@app.get("/api/state")
async def api_state() -> Dict[str, Any]:
    """Retorna la telemetría completa, modo Local-First y aprobaciones pendientes para React."""
    st = core.tasks.get_system_status()
    telemetry = st["data"] if st["ok"] else {"cpu_percent": 0, "ram_percent": 0, "battery_percent": 100}
    return {
        "state": core.state,
        "active_tool": core.active_tool,
        "last_action": core.last_action,
        "is_processing": core.is_processing,
        "handsfree": core.handsfree,
        "require_confirmation": Config.REQUIRE_CONFIRMATION,
        "live_steps": core.live_steps,
        "argon_mode": Config.ARGON_MODE,
        "model": core.last_provider_used,
        "notion_enabled": core.notion.enabled,
        "pending_approvals": policy_engine.get_pending_approvals(),
        "telemetry": telemetry,
        "memories": core.skills.recall_memories(limit=8),
        "calendar": core.get_unified_calendar(),
        "logs": core.ui_logs,
    }

@app.get("/api/metrics")
async def api_metrics() -> Dict[str, Any]:
    """Devuelve las métricas acumuladas de ejecución, latencias y categorías de fallo (Fase 5)."""
    return metrics_collector.get_summary()


# ---------------- ENDPOINTS DE COMANDOS Y APROBACIONES HITL ----------------

@app.post("/api/command")
@app.post("/command")
@app.post("/api/comando")
async def api_command(cmd: CommandRequest) -> Dict[str, Any]:
    """Recibe instrucciones desde el Command Execution Bus de React."""
    text = (cmd.text or cmd.prompt or "").strip()
    if text:
        core.add_log("USUARIO", text, "user")
        threading.Thread(target=core.process_command, args=(text,), daemon=True).start()
        return {
            "ok": True,
            "status": "accepted",
            "respuesta": f"Directiva '{text}' despachada al núcleo en modo {Config.ARGON_MODE}."
        }
    return {"ok": False, "status": "failed", "respuesta": "Comando vacío."}


@app.post("/api/approvals/{action_id}/approve")
async def api_approve_action(action_id: str) -> Dict[str, Any]:
    """Autoriza y ejecuta una acción sensible pendiente (Botón APPROVE & RUN de la HUD)."""
    msg = core.execute_approved_action(action_id)
    core.add_log("HITL_GATE", msg, "agent")
    return {"ok": True, "action_id": action_id, "message": msg}


@app.post("/api/approvals/{action_id}/deny")
async def api_deny_action(action_id: str) -> Dict[str, Any]:
    """Rechaza y descarta una acción sensible pendiente (Botón DENY de la HUD)."""
    policy_engine.deny_action(action_id)
    msg = f"Operación {action_id} denegada por el operador humano."
    core.add_log("HITL_GATE", msg, "agent")
    return {"ok": True, "action_id": action_id, "message": msg}


# ---------------- ENDPOINTS DEL BANCO DE MEMORIA SQLITE (TAB MEM) ----------------

@app.post("/api/memories")
async def api_create_memory(req: MemoryCreateRequest) -> Dict[str, Any]:
    """Crea un recuerdo desde el botón '+ ADD MEMORY KEY-VALUE' pasando por ToolPolicyEngine."""
    return core.router.invoke_tool("save_memory", {"note": req.note, "category": req.category})


@app.put("/api/memories/{mem_id}")
async def api_update_memory(mem_id: int, req: MemoryUpdateRequest) -> Dict[str, Any]:
    """Actualiza un recuerdo existente desde el ícono de edición en la HUD."""
    return core.router.invoke_tool(
        "update_memory",
        {"mem_id": mem_id, "new_note": req.note, "category": req.category or ""},
    )


@app.delete("/api/memories/{mem_id}")
async def api_delete_memory(mem_id: int) -> Dict[str, Any]:
    """Elimina un recuerdo específico de SQLite por su ID."""
    return core.router.invoke_tool("delete_memory", {"mem_id": mem_id})


@app.get("/api/memories/export")
async def api_export_memories() -> Dict[str, Any]:
    """Exporta todos los recuerdos almacenados en SQLite."""
    return core.skills.export_memories()


# ---------------- ENDPOINTS DE AGENDA UNIFICADA (TAB TASK) ----------------

@app.post("/api/tasks")
async def api_create_task(req: TaskCreateRequest) -> Dict[str, Any]:
    """Crea una tarea desde la barra 'QUICK TASK / TODO' de la HUD."""
    if req.target.lower() == "local":
        return core.productivity.add_calendar_event(req.title)
    return core.router.invoke_tool("add_task", {"title": req.title})


@app.post("/api/tasks/{task_id}/complete")
async def api_complete_task(task_id: int) -> Dict[str, Any]:
    """Marca como completada una tarea local al hacer clic en su checkbox."""
    return core.productivity.complete_calendar_event(task_id)


# ---------------- ENDPOINTS DE VOZ Y CONTROL ----------------

@app.post("/api/listen")
async def api_listen() -> Dict[str, Any]:
    """Inicia la escucha por micrófono en un hilo secundario."""
    def _worker():
        core.start_live_trace("Escuchando micrófono (pausas naturales de hasta 1.75s permitidas)...")
        spoken = core.voice.listen(timeout=8, phrase_time_limit=45)
        if spoken:
            core.add_log("USUARIO (VOZ)", spoken, "user")
            core.process_command(spoken)
        else:
            core.finish_live_trace()

    threading.Thread(target=_worker, daemon=True).start()
    return {"ok": True}


@app.post("/api/stop_voice")
async def api_stop_voice() -> Dict[str, Any]:
    """Interrumpe la locución activa del sintetizador neuronal (Botón HALT)."""
    core.voice.stop_speaking()
    core.finish_live_trace()
    return {"ok": True}


@app.post("/api/handsfree")
async def api_handsfree() -> Dict[str, Any]:
    """Activa o desactiva la conversación continua (manos libres)."""
    core.handsfree = not core.handsfree
    if core.handsfree:
        def _loop():
            while core.handsfree:
                if core.state == "IDLE" and not core.is_processing:
                    spoken = core.voice.listen(timeout=6, phrase_time_limit=40)
                    if spoken:
                        core.add_log("USUARIO (VOZ)", spoken, "user")
                        if spoken.lower() in ["detener escucha", "modo manual"]:
                            core.handsfree = False
                            break
                        core.process_command(spoken)
                time.sleep(0.25)
        threading.Thread(target=_loop, daemon=True).start()
    return {"handsfree": core.handsfree}


@app.post("/api/voice")
async def api_voice(profile: Optional[VoiceProfileRequest] = None) -> Dict[str, Any]:
    """Ajusta el perfil vocal en caliente."""
    voice = profile.voice if profile and profile.voice else "es-ES-AlvaroNeural"
    pitch = profile.pitch if profile and profile.pitch else "-14Hz"
    rate = profile.rate if profile and profile.rate else "+6%"
    core.voice.set_voice_profile(voice, pitch, rate)
    threading.Thread(
        target=lambda: core.respond("Frecuencia vocal recalibrada. Tono grave futurista activo."),
        daemon=True
    ).start()
    return {"ok": True}


@app.post("/api/shortcut")
async def api_shortcut(payload: Optional[ShortcutRequest] = None) -> Dict[str, Any]:
    """Crea o actualiza el acceso directo en el escritorio y auto-arranque sujeto a política."""
    startup = payload.startup if payload else False
    return policy_engine.execute(
        "setup_windows_integration",
        core.skills.setup_windows_integration,
        {"enable_startup": startup},
    )


def _boot_announcement() -> None:
    time.sleep(1.2)
    mems = core.skills.recall_memories(limit=3)
    if mems:
        core.respond(
            f"Arquitectura de {Config.AGENT_NAME} activa en modo {Config.ARGON_MODE}. "
            f"He cargado {len(mems)} recuerdos permanentes en el puerto 8000."
        )
    else:
        core.respond(
            f"Núcleo {Config.AGENT_NAME} edición Hermes activo en modo {Config.ARGON_MODE}. "
            "Servidor FastAPI listo en el puerto 8000."
        )


if __name__ == "__main__":
    threading.Thread(target=_boot_announcement, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)