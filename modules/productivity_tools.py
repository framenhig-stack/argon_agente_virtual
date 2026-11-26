"""
Ruta: modules/productivity_tools.py
Descripción: Gestión de agenda/calendario local, lectura de correos por IMAP
e inspección segura de archivos de código locales con validación canónica de rutas.
"""
import ast
import email
from email.header import decode_header
import imaplib
import json
import logging
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from config import Config, BASE_DIR, LOG_DIR

logger = logging.getLogger("ProductivityTools")
CALENDAR_FILE = LOG_DIR / "calendar_tasks.json"


class ProductivityTools:
    def __init__(self) -> None:
        self._cal_lock = threading.Lock()
        self._cached_events: List[Dict[str, Any]] | None = None
        self._ensure_calendar_file()

    def _ensure_calendar_file(self) -> None:
        with self._cal_lock:
            if not CALENDAR_FILE.exists():
                sample_events = [
                    {
                        "id": 1,
                        "title": "Revisar arquitectura de Argon 4 en VS Code",
                        "datetime": datetime.now().strftime("%Y-%m-%d 18:30"),
                        "status": "pendiente"
                    }
                ]
                CALENDAR_FILE.write_text(
                    json.dumps(sample_events, indent=2, ensure_ascii=False), encoding="utf-8"
                )

    # ---------------- CALENDARIO Y PENDIENTES ----------------
    def list_calendar_events(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de eventos y pendientes activos usando caché en memoria."""
        with self._cal_lock:
            if self._cached_events is not None:
                return list(self._cached_events)
            try:
                data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
                self._cached_events = [item for item in data if item.get("status") == "pendiente"]
                return list(self._cached_events)
            except Exception as exc:
                logger.error(f"Error leyendo calendario: {exc}")
                return []

    def add_calendar_event(self, title: str, date_str: str = "") -> Dict[str, Any]:
        """Agrega un nuevo pendiente o cita a la agenda local evitando duplicados activos."""
        clean_title = (title or "").strip()
        if not clean_title:
            return {"ok": False, "status": "failed", "error": "El título del pendiente no puede estar vacío."}

        with self._cal_lock:
            try:
                data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
                # Comprobación de idempotencia: evitar duplicar el mismo pendiente activo
                for existing in data:
                    if (
                        existing.get("status") == "pendiente"
                        and str(existing.get("title", "")).strip().lower() == clean_title.lower()
                    ):
                        return {
                            "ok": True,
                            "status": "success",
                            "deduplicated": True,
                            "event": existing,
                        }

                if not date_str:
                    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                new_item = {
                    "id": len(data) + 1,
                    "title": clean_title,
                    "datetime": date_str,
                    "status": "pendiente"
                }
                data.append(new_item)
                CALENDAR_FILE.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                self._cached_events = None
                logger.info(f"Pendiente agregado al calendario: {clean_title}")
                return {"ok": True, "status": "success", "event": new_item}
            except Exception as exc:
                return {"ok": False, "status": "failed", "error": str(exc)}

    def complete_calendar_event(self, event_id: int) -> Dict[str, Any]:
        """Marca un pendiente como completado por su ID."""
        with self._cal_lock:
            try:
                data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
                for item in data:
                    if item.get("id") == event_id:
                        item["status"] = "completado"
                        CALENDAR_FILE.write_text(
                            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
                        )
                        self._cached_events = None
                        return {"ok": True, "status": "success", "title": item.get("title")}
                return {"ok": False, "status": "failed", "error": f"No se encontró el pendiente #{event_id}."}
            except Exception as exc:
                return {"ok": False, "status": "failed", "error": str(exc)}

    # ---------------- REVISIÓN DE CORREOS (IMAP / WEB) ----------------
    @staticmethod
    def check_emails(limit: int = 3, allow_browser_fallback: bool = False) -> Dict[str, Any]:
        """
        Consulta los últimos correos vía IMAP si las credenciales están en .env.
        No abre el navegador automáticamente a menos que allow_browser_fallback=True.
        """
        if not Config.EMAIL_USER or not Config.EMAIL_APP_PASSWORD:
            if allow_browser_fallback:
                webbrowser.open("https://mail.google.com")
                return {
                    "ok": True,
                    "status": "partial",
                    "mode": "browser",
                    "summary": "Credenciales IMAP no configuradas. Se abrió el navegador.",
                }
            return {
                "ok": False,
                "status": "failed",
                "mode": "unconfigured",
                "error": (
                    "Credenciales IMAP no configuradas. Define EMAIL_USER y EMAIL_APP_PASSWORD "
                    "en el archivo .env para consultar correos."
                ),
            }

        try:
            mail = imaplib.IMAP4_SSL(Config.EMAIL_IMAP_HOST, timeout=10)
            mail.login(Config.EMAIL_USER, Config.EMAIL_APP_PASSWORD)
            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            mail_ids = messages[0].split()
            if not mail_ids:
                mail.logout()
                return {
                    "ok": True,
                    "status": "success",
                    "mode": "imap",
                    "summary": "No tienes correos nuevos sin leer.",
                }

            recent_ids = mail_ids[-limit:]
            summaries = []
            for m_id in reversed(recent_ids):
                _, msg_data = mail.fetch(m_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg.get("Subject", "Sin asunto"))[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")
                        sender = msg.get("From", "Remitente desconocido")
                        summaries.append(f"De {sender}: {subject}")

            mail.logout()
            joined = " | ".join(summaries)
            return {
                "ok": True,
                "status": "success",
                "mode": "imap",
                "summary": f"Tienes {len(mail_ids)} correos sin leer. Los más recientes son: {joined}"
            }
        except Exception as exc:
            logger.error(f"Error IMAP: {exc}")
            return {"ok": False, "status": "failed", "error": f"No pude conectar al servidor de correo: {exc}"}

    # ---------------- AUDITOR Y ANALIZADOR DE CÓDIGO (BLINDADO FASE 1) ----------------
    @staticmethod
    def _is_sensitive_path(path_obj: Path) -> bool:
        """Verifica si un archivo o cualquiera de sus carpetas padre es sensible o está excluido."""
        name_lower = path_obj.name.lower()
        if name_lower.startswith(".env") or name_lower in Config.SENSITIVE_FILENAMES:
            return True
        if path_obj.suffix.lower() in Config.SENSITIVE_EXTENSIONS:
            return True
        for part in path_obj.parts:
            if part in Config.IGNORED_DIRS:
                return True
        return False

    @classmethod
    def analyze_code_file(cls, relative_path: str, base_dir: Path | None = None) -> Dict[str, Any]:
        """
        Inspecciona un archivo de código dentro del directorio autorizado (BASE_DIR).
        Valida rutas canónicas con pathlib.Path.is_relative_to() y bloquea traversal y archivos sensibles.
        """
        root_dir = (base_dir or BASE_DIR).resolve()
        clean_name = (relative_path or "").strip().replace('"', "").replace("'", "")

        if not clean_name or "\x00" in clean_name:
            return {"ok": False, "status": "denied", "error": "Ruta de archivo vacía o inválida."}

        raw_path = Path(clean_name)

        # 1. Rechazar de inmediato cualquier intento de Path Traversal ('..')
        if ".." in raw_path.parts:
            return {
                "ok": False,
                "status": "denied",
                "error": "Acceso denegado: No se permiten secuencias de navegación '..' fuera del proyecto.",
            }

        # 2. Resolver ruta candidata (si es absoluta, verificar que pertenezca a root_dir)
        try:
            candidate = raw_path.resolve() if raw_path.is_absolute() else (root_dir / raw_path).resolve()
        except Exception:
            return {"ok": False, "status": "denied", "error": "Formato de ruta no válido."}

        # 3. Verificación canónica con Path.is_relative_to (previene prefijos engañosos y symlinks externos)
        if not candidate.is_relative_to(root_dir):
            return {
                "ok": False,
                "status": "denied",
                "error": "Acceso denegado: La ruta solicitada está fuera del directorio autorizado del proyecto.",
            }

        # 4. Bloquear archivos sensibles (.env, PyWhatKit_DB.txt, bases SQLite, logs)
        rel_candidate = candidate.relative_to(root_dir)
        if cls._is_sensitive_path(rel_candidate) or cls._is_sensitive_path(raw_path):
            return {
                "ok": False,
                "status": "denied",
                "error": "Acceso denegado: Por seguridad no se permite inspeccionar archivos sensibles o de configuración privada.",
            }

        # 5. Si el usuario pasó solo el nombre de un archivo (sin directorios) y no está en la raíz, buscar de forma segura
        target = candidate
        if not target.exists() or not target.is_file():
            if len(raw_path.parts) == 1 and not raw_path.is_absolute():
                safe_matches: List[Path] = []
                for m in root_dir.rglob(raw_path.name):
                    try:
                        resolved_m = m.resolve()
                        if (
                            resolved_m.is_file()
                            and resolved_m.is_relative_to(root_dir)
                            and not cls._is_sensitive_path(resolved_m.relative_to(root_dir))
                        ):
                            safe_matches.append(resolved_m)
                    except Exception:
                        continue
                if safe_matches:
                    target = safe_matches[0]
                else:
                    return {"ok": False, "status": "failed", "error": f"No encontré el archivo '{clean_name}' en el proyecto."}
            else:
                return {"ok": False, "status": "failed", "error": f"No encontré el archivo '{clean_name}' en el proyecto."}

        if target.suffix.lower() not in Config.ALLOWED_CODE_EXTENSIONS:
            return {
                "ok": False,
                "status": "denied",
                "error": f"Extensión '{target.suffix}' no permitida para análisis de código.",
            }

        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            syntax_status = "Sintaxis válida"

            if target.suffix.lower() == ".py":
                try:
                    tree = ast.parse(content)
                    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                    syntax_status = (
                        f"Sintaxis Python correcta. Contiene {len(classes)} clases "
                        f"({', '.join(classes[:4])}) y {len(funcs)} funciones."
                    )
                except SyntaxError as syn_err:
                    syntax_status = f"Error de sintaxis en línea {syn_err.lineno}: {syn_err.msg}"

            return {
                "ok": True,
                "status": "success",
                "filepath": str(target.relative_to(root_dir)),
                "lines": len(lines),
                "syntax": syntax_status,
                "snippet": "\n".join(lines[:90])
            }
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": f"No se pudo leer el archivo: {exc}"}


def build_unified_task_result(
    title: str,
    local_res: Dict[str, Any],
    notion_res: Dict[str, Any],
    notion_enabled: bool = True,
) -> Dict[str, Any]:
    """
    Evalúa de forma veraz el resultado de crear una tarea en la agenda local y en Notion.
    Devuelve 'success', 'partial' o 'failed' en lugar de asumir éxito incondicional.
    """
    local_ok = bool(local_res.get("ok", False))
    notion_ok = bool(notion_res.get("ok", False))

    if not notion_enabled:
        if local_ok:
            return {
                "ok": True,
                "status": "success",
                "title": title,
                "local": local_res,
                "notion_synced": False,
                "message": f"Agendado en calendario local: {title} (Notion no configurado).",
            }
        return {
            "ok": False,
            "status": "failed",
            "title": title,
            "local": local_res,
            "notion_synced": False,
            "error": local_res.get("error", "Fallo al guardar en la agenda local."),
        }

    if local_ok and notion_ok:
        return {
            "ok": True,
            "status": "success",
            "title": title,
            "local": local_res,
            "notion_synced": True,
            "message": f"Tarea sincronizada en agenda local y Notion: {title}.",
        }

    if local_ok or notion_ok:
        failed_target = "Notion API" if local_ok else "agenda local"
        err_detail = notion_res.get("error") if local_ok else local_res.get("error")
        return {
            "ok": True,
            "status": "partial",
            "title": title,
            "local": local_res,
            "notion_synced": notion_ok,
            "warning": f"Guardado parcial: falló la sincronización en {failed_target} ({err_detail}).",
        }

    return {
        "ok": False,
        "status": "failed",
        "title": title,
        "local": local_res,
        "notion_synced": False,
        "error": (
            f"Fallo total al crear la tarea '{title}'. "
            f"Local: {local_res.get('error')} | Notion: {notion_res.get('error')}"
        ),
    }