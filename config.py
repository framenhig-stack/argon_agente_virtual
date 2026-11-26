"""
Ruta: config.py
Descripción: Configuración central unificada de Argon 4 // Hermes Edition.
Incluye validación de modos de privacidad (local_first, strict_local, cloud_first),
políticas de proveedores LLM y seguridad de herramientas (Fases 1 y 2).
"""
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Set
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

SKINS_DIR = BASE_DIR / "skins"
SKINS_DIR.mkdir(exist_ok=True)

TELEMETRY_FILE = LOG_DIR / "runtime_telemetry.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "agent_activity.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
) 
 
# Filtro global de redacción de secretos en logs (Fase 5)
try:
    from modules.observability import RedactingLogFilter
    for _handler in logging.getLogger().handlers:
        _handler.addFilter(RedactingLogFilter())
except Exception:
    pass

logger = logging.getLogger("Config")

VALID_ARGON_MODES = {"local_first", "strict_local", "cloud_first"}
VALID_CLOUD_FALLBACKS = {"manual_approval", "auto", "disabled"}


def _get_validated_choice(env_key: str, default: str, allowed: Set[str]) -> str:
    val = os.getenv(env_key, default).strip().lower()
    if val not in allowed:
        logger.warning(
            f"Valor inválido para {env_key}='{val}'. Usando valor seguro por defecto: '{default}'."
        )
        return default
    return val


class Config:
    AGENT_NAME: str = os.getenv("AGENT_NAME", "Argon 4")
    LANGUAGE_CODE: str = os.getenv("LANGUAGE_CODE", "es-PE")
    ASSISTANT_VOICE: str = os.getenv("ASSISTANT_VOICE", "es-ES-AlvaroNeural")
    VOICE_PITCH: str = os.getenv("VOICE_PITCH", "-14Hz")
    VOICE_RATE_STR: str = os.getenv("VOICE_RATE", "+6%")
    VOICE_RATE: int = 175
    VOICE_VOLUME: float = float(os.getenv("VOICE_VOLUME", "1.0"))

    # --- Políticas de Seguridad y Permisos (Fase 1) ---
    REQUIRE_CONFIRMATION: bool = os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
    TOOL_TIMEOUT_SECONDS: int = int(os.getenv("TOOL_TIMEOUT_SECONDS", "30"))
    # --- Límites del Ciclo de Ejecución Agéntica (Fase 3) ---
    MAX_PLAN_STEPS: int = int(os.getenv("MAX_PLAN_STEPS", "5"))
    MAX_PARALLEL_TOOLS: int = int(os.getenv("MAX_PARALLEL_TOOLS", "3"))
    MAX_PLAN_DURATION_SECONDS: float = float(os.getenv("MAX_PLAN_DURATION_SECONDS", "45.0"))

    SENSITIVE_FILENAMES: Set[str] = {
        ".env",
        ".env.local",
        "pywhatkit_db.txt",
        "filespy.txt",
        "runtime_telemetry.json",
        "agent_activity.log",
        "calendar_tasks.json",
    }
    SENSITIVE_EXTENSIONS: Set[str] = {".db", ".sqlite", ".sqlite3", ".log", ".pem", ".key", ".pfx"}
    IGNORED_DIRS: Set[str] = {".git", ".venv", "venv", "ENV", "__pycache__", "node_modules", "logs", "dist"}
    ALLOWED_CODE_EXTENSIONS: Set[str] = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".txt", ".css", ".html"}

    # --- Modo de Ejecución y Proveedores Intercambiables (Fase 2) ---
    # Valores aceptados para ARGON_MODE: local_first | strict_local | cloud_first
    ARGON_MODE: str = _get_validated_choice("ARGON_MODE", "local_first", VALID_ARGON_MODES)
    LOCAL_PROVIDER: str = os.getenv("LOCAL_PROVIDER", "ollama").strip().lower()
    CLOUD_PROVIDER: str = os.getenv("CLOUD_PROVIDER", "gemini").strip().lower()
    # Valores aceptados para CLOUD_FALLBACK: manual_approval | auto | disabled
    CLOUD_FALLBACK: str = _get_validated_choice("CLOUD_FALLBACK", "manual_approval", VALID_CLOUD_FALLBACKS)
    # Controla si se permite enviar capturas de pantalla, portapapeles o código local a la nube sin pedir permiso
    ALLOW_CLOUD_SENSITIVE_DATA: bool = os.getenv("ALLOW_CLOUD_SENSITIVE_DATA", "false").lower() == "true"

    # Motores Cognitivos (Google Gemini + Ollama Local)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "").strip()
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "45"))

    # Notion API
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "").strip()
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "").strip()

    # Canales: Correo IMAP, WhatsApp y VoIP
    EMAIL_IMAP_HOST: str = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
    EMAIL_USER: str = os.getenv("EMAIL_USER", "").strip()
    EMAIL_APP_PASSWORD: str = os.getenv("EMAIL_APP_PASSWORD", "").strip()

    _raw_cc = os.getenv("DEFAULT_COUNTRY_CODE", "+51").strip().split()[0]
    DEFAULT_COUNTRY_CODE: str = _raw_cc if _raw_cc.startswith("+") else "+51"
    DEFAULT_TARGET_PHONE: str = os.getenv("DEFAULT_TARGET_PHONE", "").strip()

    WHATSAPP_BRIDGE_URL: str = os.getenv("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000")
    WHATSAPP_SESSION: str = os.getenv("WHATSAPP_SESSION", "argon_session")
    SIP_SOFTPHONE_BIN: str = os.getenv("SIP_SOFTPHONE_BIN", "linphonecsh")

    HUD_PORT: int = int(os.getenv("HUD_PORT", "8765"))


_telemetry_lock = threading.Lock()
_last_telemetry_signature = ""


def write_telemetry_snapshot(state: str, active_tool: str, last_action: str) -> None:
    """Guarda el estado instantáneo del agente en disco solo cuando cambia."""
    global _last_telemetry_signature
    clean_action = last_action[:150]
    sig = f"{state}|{active_tool}|{clean_action}"

    with _telemetry_lock:
        if sig == _last_telemetry_signature:
            return
        _last_telemetry_signature = sig
        payload: Dict[str, Any] = {
            "status": state,
            "tool": active_tool,
            "last_action": clean_action,
            "updated_at": datetime.now().strftime("%H:%M:%S"),
        }
        try:
            TELEMETRY_FILE.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass