"""
Ruta: modules/advanced_skills.py
Descripción: Memoria Cognitiva Persistente y Controlable en SQLite (Fase 4),
con filtro anti-secretos, defensa contra Stored Prompt Injection, búsqueda por relevancia,
operaciones CRUD verificadas, Búsqueda Web, Portapapeles y Despliegue en Windows 11.
"""
import os
import re
import sqlite3
import subprocess
import logging
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil
import pyperclip
from duckduckgo_search import DDGS
from config import BASE_DIR, LOG_DIR

logger = logging.getLogger("AdvancedSkills")
MEMORY_DB = LOG_DIR / "argon_memory.db"

# Patrones de secretos, tokens y credenciales que NUNCA deben guardarse en SQLite
SECRET_PATTERNS = [
    re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),                     # Google / Gemini API Key
    re.compile(r"\bsk-[A-Za-z0-9\-_]{20,}\b"),                      # OpenAI / Anthropic Key
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),                  # GitHub Token
    re.compile(r"\b(?:secret|ntn)_[A-Za-z0-9]{20,}\b"),             # Notion Token
    re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.I),        # Bearer Token
    re.compile(r"(?:password|contraseña|api[_\s]?key|token|clave\s+secreta)\s*(?:es|=|:)\s*\S+", re.I),
]

# Patrones de Prompt Injection o instrucciones privilegiadas que no deben guardarse como recuerdos
INJECTION_PATTERNS = [
    re.compile(r"ignor(?:a|e)[rs]?\s+(?:todas\s+)?las\s+instrucciones", re.I),
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.I),
    re.compile(r"system\s*prompt", re.I),
    re.compile(r"env[ií](?:a|e)[ns]?\s+(?:un\s+)?whatsapp", re.I),
    re.compile(r"<datos_portapapeles_no_confiables>|<resultados_web_no_confiables>", re.I),
]


class AdvancedSkills:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path: Path = Path(db_path) if db_path else MEMORY_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memories_cache: Optional[List[Dict[str, Any]]] = None
        self._init_memory_db()

    @contextlib.contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_memory_db(self) -> None:
        """Inicializa y migra sin pérdida de datos las tablas de memoria semántica y episódica."""
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT DEFAULT 'General',
                    note TEXT NOT NULL,
                    source TEXT DEFAULT 'explicit',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cols = [r[1] for r in conn.execute("PRAGMA table_info(memories);")]
            if "category" not in cols:
                conn.execute("ALTER TABLE memories ADD COLUMN category TEXT DEFAULT 'General';")
            if "source" not in cols:
                conn.execute("ALTER TABLE memories ADD COLUMN source TEXT DEFAULT 'explicit';")
            if "updated_at" not in cols:
                conn.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT DEFAULT '';")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # ---------------- VALIDACIONES DE SEGURIDAD PARA MEMORIA ----------------
    @staticmethod
    def contains_sensitive_secret(text: str) -> bool:
        """Detecta si un texto contiene claves API, contraseñas o tokens que no deben persistirse."""
        if not text:
            return False
        return any(pat.search(text) for pat in SECRET_PATTERNS)

    @staticmethod
    def contains_prompt_injection(text: str) -> bool:
        """Detecta intentos de inyectar órdenes de sistema dentro de la memoria persistente."""
        if not text:
            return False
        return any(pat.search(text) for pat in INJECTION_PATTERNS)

    # ---------------- 1. MEMORIA PERSISTENTE, RELEVANCIA Y CONTROL DE USUARIO ----------------
    def save_memory(
        self,
        note: str,
        category: str = "Usuario",
        source: str = "explicit",
    ) -> Dict[str, Any]:
        clean = (note or "").strip()
        clean_cat = (category or "Usuario").strip() or "Usuario"
        clean_source = "inferred" if source == "inferred" else "explicit"

        if not clean:
            return {"ok": False, "status": "failed", "error": "El contenido a recordar está vacío."}

        if self.contains_sensitive_secret(clean):
            logger.warning("Intento bloqueado de guardar un secreto o credencial en SQLite.")
            return {
                "ok": False,
                "status": "denied",
                "error": "Seguridad de Memoria: No se permite almacenar claves API, tokens ni contraseñas en la memoria.",
            }

        if self.contains_prompt_injection(clean):
            logger.warning("Intento bloqueado de guardar patrón de Prompt Injection en SQLite.")
            return {
                "ok": False,
                "status": "denied",
                "error": "Seguridad de Memoria: El texto contiene patrones de instrucción no permitidos en recuerdos.",
            }

        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            with self._get_conn() as conn:
                # 1. Evitar duplicados exactos (actualiza fecha y promueve a 'explicit' si ya existía)
                existing = conn.execute(
                    "SELECT id, source FROM memories WHERE lower(note) = ?",
                    (clean.lower(),),
                ).fetchone()
                if existing:
                    mem_id, old_source = existing
                    new_source = "explicit" if clean_source == "explicit" else old_source
                    conn.execute(
                        "UPDATE memories SET category = ?, source = ?, updated_at = ? WHERE id = ?",
                        (clean_cat, new_source, now, mem_id),
                    )
                    conn.commit()
                    self._memories_cache = None
                    return {
                        "ok": True,
                        "status": "success",
                        "id": mem_id,
                        "note": clean,
                        "category": clean_cat,
                        "source": new_source,
                        "updated_existing": True,
                    }

                # 2. Insertar nuevo recuerdo con procedencia y marca temporal
                cur = conn.execute(
                    "INSERT INTO memories (category, note, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (clean_cat, clean, clean_source, now, now),
                )
                mem_id = cur.lastrowid
                conn.commit()

            self._memories_cache = None
            logger.info(f"Memoria almacenada #{mem_id} [{clean_cat}/{clean_source}]: {clean}")
            return {
                "ok": True,
                "status": "success",
                "id": mem_id,
                "note": clean,
                "category": clean_cat,
                "source": clean_source,
            }
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    def update_memory(
        self,
        mem_id: int,
        new_note: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Actualiza un recuerdo existente por su ID verificando que exista y sea seguro."""
        clean = (new_note or "").strip()
        if not clean:
            return {"ok": False, "status": "failed", "error": "El nuevo texto del recuerdo no puede estar vacío."}

        if self.contains_sensitive_secret(clean) or self.contains_prompt_injection(clean):
            return {
                "ok": False,
                "status": "denied",
                "error": "Seguridad de Memoria: El nuevo texto contiene secretos o instrucciones no permitidas.",
            }

        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            with self._get_conn() as conn:
                if category:
                    cur = conn.execute(
                        "UPDATE memories SET note = ?, category = ?, source = 'explicit', updated_at = ? WHERE id = ?",
                        (clean, category.strip(), now, int(mem_id)),
                    )
                else:
                    cur = conn.execute(
                        "UPDATE memories SET note = ?, source = 'explicit', updated_at = ? WHERE id = ?",
                        (clean, now, int(mem_id)),
                    )
                conn.commit()
                if cur.rowcount == 0:
                    return {
                        "ok": False,
                        "status": "failed",
                        "error": f"No existe ningún recuerdo con el ID #{mem_id}.",
                    }

            self._memories_cache = None
            return {"ok": True, "status": "success", "id": int(mem_id), "note": clean}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    def delete_memory(self, mem_id: int) -> Dict[str, Any]:
        """Elimina un recuerdo por su ID comprobando que realmente existía en SQLite."""
        try:
            with self._get_conn() as conn:
                cur = conn.execute("DELETE FROM memories WHERE id = ?", (int(mem_id),))
                conn.commit()
                if cur.rowcount == 0:
                    return {
                        "ok": False,
                        "status": "failed",
                        "error": f"No se encontró ningún recuerdo con el ID #{mem_id} para eliminar.",
                    }
            self._memories_cache = None
            return {"ok": True, "status": "success", "deleted_id": int(mem_id)}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    def _load_all_memories(self) -> List[Dict[str, Any]]:
        if self._memories_cache is not None:
            return list(self._memories_cache)
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, category, note, created_at, source, updated_at FROM memories ORDER BY id DESC"
            )
            rows = cur.fetchall()
        self._memories_cache = [
            {
                "id": r[0],
                "category": r[1],
                "note": r[2],
                "date": r[3],
                "source": r[4] or "explicit",
                "updated_at": r[5] or r[3],
            }
            for r in rows
        ]
        return list(self._memories_cache)

    def recall_memories(self, limit: int = 10, query: str = "") -> List[Dict[str, Any]]:
        """
        Recupera recuerdos de SQLite. Si se proporciona 'query', puntúa por relevancia
        de palabras clave, categoría y procedencia ('explicit' > 'inferred') para no depender
        exclusivamente de las filas más recientes.
        """
        try:
            all_mems = self._load_all_memories()
            if not query or not query.strip():
                return all_mems[:limit]

            tokens = [
                t.lower()
                for t in re.findall(r"[a-záéíóúñ0-9]{3,}", query.lower())
                if t not in {"que", "del", "los", "las", "para", "con", "una", "por", "como", "sobre", "mis"}
            ]
            if not tokens:
                return all_mems[:limit]

            scored: List[tuple[float, int, Dict[str, Any]]] = []
            for idx, m in enumerate(all_mems):
                haystack = f"{m['category']} {m['note']}".lower()
                hits = sum(2.0 for tok in tokens if tok in haystack)
                # Bonificación ligera si es un recuerdo explícito confirmado por el usuario
                explicit_bonus = 0.5 if m.get("source") == "explicit" else 0.0
                # Bonificación por recencia relativa
                recency_bonus = max(0.0, 0.3 - (idx * 0.01))
                score = hits + (explicit_bonus if hits > 0 else 0.0) + recency_bonus
                scored.append((score, -m["id"], m))

            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return [item[2] for item in scored[:limit]]
        except Exception as exc:
            logger.error(f"Error leyendo memoria SQLite: {exc}")
            return []

    def search_memories(self, query: str = "", category: str = "", limit: int = 10) -> Dict[str, Any]:
        """Busca recuerdos por texto y/o categoría devolviendo un estado estructurado."""
        try:
            all_mems = self._load_all_memories()
            filtered = all_mems
            if category and category.strip():
                cat_low = category.strip().lower()
                filtered = [m for m in filtered if m["category"].lower() == cat_low]

            if query and query.strip():
                q_tokens = [t.lower() for t in re.findall(r"[a-záéíóúñ0-9]{2,}", query.lower())]
                matched = []
                for m in filtered:
                    haystack = f"{m['category']} {m['note']}".lower()
                    if any(tok in haystack for tok in q_tokens):
                        matched.append(m)
                filtered = matched

            return {
                "ok": True,
                "status": "success",
                "count": len(filtered[:limit]),
                "memories": filtered[:limit],
            }
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc), "memories": []}

    def export_memories(self) -> Dict[str, Any]:
        """Exporta todos los recuerdos almacenados para inspección o respaldo del usuario."""
        try:
            all_mems = self._load_all_memories()
            return {
                "ok": True,
                "status": "success",
                "total": len(all_mems),
                "memories": all_mems,
            }
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    def auto_extract_memory(self, user_text: str) -> None:
        """
        Detecta automáticamente datos relevantes mencionados por el usuario en conversación natural
        y los registra con procedencia 'inferred', bloqueando secretos e inyecciones.
        """
        if not user_text or len(user_text) > 350:
            return
        if self.contains_sensitive_secret(user_text) or self.contains_prompt_injection(user_text):
            return

        # Ignorar órdenes directas de borrado o consulta de memoria para no auto-guardarlas
        lower_txt = user_text.lower().strip()
        if any(
            cmd in lower_txt
            for cmd in ("olvida", "borra el recuerdo", "elimina el recuerdo", "qué recuerdas", "que recuerdas")
        ):
            return

        patterns = [
            (r"mi proyecto (?:se llama|es|trata sobre)\s+([^.,;\n]+)", "Proyecto"),
            (r"estoy trabajando en\s+([^.,;\n]+)", "Proyecto"),
            (r"prefiero\s+([^.,;\n]+)", "Preferencia"),
            (r"me gusta\s+([^.,;\n]+)", "Preferencia"),
            (r"mi correo (?:es|principal es)\s+([^.,;\n]+)", "Contacto"),
            (r"mi objetivo es\s+([^.,;\n]+)", "Objetivo"),
            (r"tengo que entregar\s+([^.,;\n]+)", "Prioridad"),
        ]
        for pat, cat in patterns:
            match = re.search(pat, user_text, re.IGNORECASE)
            if match and len(match.group(0)) < 140:
                self.save_memory(match.group(0).strip(), category=cat, source="inferred")
                break

    def log_conversation_turn(self, role: str, content: str) -> None:
        """Guarda cada turno de conversación en disco, redactando secretos si aparecieran."""
        try:
            clean_text = (content or "").strip()
            if not clean_text:
                return
            if self.contains_sensitive_secret(clean_text):
                clean_text = "[CONTENIDO SENSIBLE REDACTADO POR POLÍTICA DE SEGURIDAD]"
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO chat_log (role, content, timestamp) VALUES (?, ?, ?)",
                    (role, clean_text, now),
                )
                conn.commit()
        except Exception as exc:
            logger.error(f"Error guardando historial de chat: {exc}")

    def load_recent_conversation(self, limit: int = 10) -> List[Dict[str, str]]:
        """Recupera las últimas interacciones de sesiones anteriores al iniciar Argon 4."""
        try:
            with self._get_conn() as conn:
                cur = conn.execute(
                    "SELECT role, content FROM chat_log ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cur.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
        except Exception:
            return []

    # ---------------- 2. ACCESO DIRECTO Y AUTO-ARRANQUE WINDOWS 11 ----------------
    @staticmethod
    def setup_windows_integration(enable_startup: bool = False) -> Dict[str, Any]:
        """
        Crea un lanzador (.bat / .vbs) + Acceso Directo en el Escritorio de Windows
        apuntando a la arquitectura actual (api_server.py o main_agent.py).
        """
        try:
            venv_pythonw = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"
            venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
            python_bin = venv_pythonw if venv_pythonw.exists() else venv_python
            entry_script = BASE_DIR / "api_server.py" if (BASE_DIR / "api_server.py").exists() else (BASE_DIR / "main_agent.py")

            bat_path = BASE_DIR / "Launch_Argon4.bat"
            bat_content = (
                f'@echo off\n'
                f'cd /d "{BASE_DIR}"\n'
                f'"{venv_python}" "{entry_script}"\n'
            )
            bat_path.write_text(bat_content, encoding="utf-8")

            vbs_path = BASE_DIR / "Argon4_Silent_Launcher.vbs"
            vbs_content = (
                f'Set WshShell = CreateObject("WScript.Shell")\n'
                f'WshShell.CurrentDirectory = "{BASE_DIR}"\n'
                f'WshShell.Run """{python_bin}"" ""{entry_script}""", 0, False\n'
            )
            vbs_path.write_text(vbs_content, encoding="utf-8")

            desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
            shortcut_desktop = desktop_dir / "Argon 4 AI.lnk"

            ps_script = (
                f'$WshShell = New-Object -ComObject WScript.Shell; '
                f'$Shortcut = $WshShell.CreateShortcut("{shortcut_desktop}"); '
                f'$Shortcut.TargetPath = "wscript.exe"; '
                f'$Shortcut.Arguments = """{vbs_path}"""; '
                f'$Shortcut.WorkingDirectory = "{BASE_DIR}"; '
                f'$Shortcut.IconLocation = "shell32.dll,13"; '
                f'$Shortcut.Description = "Argon 4 Tactical AI Assistant"; '
                f'$Shortcut.Save()'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)

            startup_dir = (
                Path(os.environ.get("APPDATA", ""))
                / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            )
            shortcut_startup = startup_dir / "Argon 4 AI.lnk"

            startup_msg = "Acceso directo creado en tu Escritorio ('Argon 4 AI')."
            if enable_startup and startup_dir.exists():
                ps_startup = ps_script.replace(str(shortcut_desktop), str(shortcut_startup))
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_startup], check=True)
                startup_msg = "Acceso directo creado en el Escritorio y activado en el Inicio Automático de Windows."
            elif not enable_startup and shortcut_startup.exists():
                shortcut_startup.unlink()

            return {"ok": True, "status": "success", "message": startup_msg}
        except Exception as exc:
            logger.error(f"Error configurando acceso directo en Windows: {exc}")
            return {"ok": False, "status": "failed", "error": str(exc)}

    # ---------------- 3. BÚSQUEDA WEB, PORTAPAPELES Y PROCESOS ----------------
    @staticmethod
    def search_web(query: str, max_results: int = 3) -> Dict[str, Any]:
        clean_q = query.strip()
        if not clean_q:
            return {"ok": False, "status": "failed", "error": "Consulta vacía."}
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(clean_q, region="pe-es", max_results=max_results):
                    results.append(f"- {r.get('title', '')}: {r.get('body', '')}")
            if not results:
                return {"ok": False, "status": "failed", "error": "Sin resultados web."}
            return {"ok": True, "status": "success", "query": clean_q, "context": "\n".join(results)}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    @staticmethod
    def read_clipboard() -> Dict[str, Any]:
        try:
            content = pyperclip.paste()
            if not content or not content.strip():
                return {"ok": False, "status": "failed", "error": "Portapapeles vacío."}
            return {"ok": True, "status": "success", "content": content.strip()[:2500]}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}

    @staticmethod
    def get_top_processes(limit: int = 4) -> Dict[str, Any]:
        try:
            procs = []
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    mem_mb = p.info["memory_info"].rss / (1024 * 1024)
                    procs.append({"name": p.info["name"], "mem_mb": round(mem_mb, 1)})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x["mem_mb"], reverse=True)
            top = procs[:limit]
            summary = ", ".join([f"{item['name']} ({item['mem_mb']} MB)" for item in top])
            return {"ok": True, "status": "success", "top": top, "summary": summary}
        except Exception as exc:
            return {"ok": False, "status": "failed", "error": str(exc)}
