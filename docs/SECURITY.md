# Política de Seguridad, Privacidad y Permisos — Argon 4

## 1. Principios de Seguridad por Defecto (Safe-by-Default)
Argon 4 aplica controles en el código de la aplicación (nunca confiando únicamente en el prompt del LLM):
1. **Confirmación obligatoria por defecto (`REQUIRE_CONFIRMATION=true`):** Ninguna acción que escriba en servicios de terceros o modifique el inicio del sistema operativo se ejecuta sin aprobación explícita del usuario.
2. **Aprobaciones de un solo uso vinculadas a argumentos:** Cuando el usuario aprueba un `action_id`, el permiso autoriza exclusivamente esa herramienta con esos argumentos exactos una sola vez. Un modelo comprometido no puede reutilizar la autorización para enviar otro mensaje o cambiar el destinatario.
3. **Mismos controles en todas las vías:** Tanto el chat por voz/texto, como el enrutador de herramientas (`AgentToolRouter`), los endpoints REST (`api_server.py`) y el servidor MCP (`mcp_server.py`) pasan por `ToolPolicyEngine`.

---

## 2. Clasificación de Niveles de Riesgo de Herramientas

| Nivel de Riesgo | Herramientas Incluidas | Política Aplicada |
| :--- | :--- | :--- |
| **`read`** | `get_system_status`, `get_top_processes`, `recall_memories`, `search_memories`, `list_tasks`, `search_web` | Ejecución permitida; aptas para paralelismo cuando no tienen dependencias. |
| **`local_write`** | `save_memory`, `update_memory`, `delete_memory`, `open_application` | Ejecución secuencial; validación de lista blanca (`ALLOWED_WINDOWS_APPS`) y filtro anti-secretos en SQLite. |
| **`external_write`** | `add_task` (Notion), `send_whatsapp` | Ejecución secuencial con control de idempotencia; `send_whatsapp` exige aprobación explícita por `action_id`. |
| **`sensitive`** | `read_clipboard`, `analyze_code_file`, `check_emails`, `setup_windows_integration` | `analyze_code_file` aplica validación canónica de rutas; `setup_windows_integration` exige aprobación explícita; los datos leídos se marcan como `contains_sensitive_data=True`. |

---

## 3. Blindaje contra Path Traversal y Exfiltración de Archivos
La herramienta `ProductivityTools.analyze_code_file()` protege el sistema de archivos mediante 5 capas:
1. Rechazo inmediato de cualquier ruta que contenga `..` en sus componentes (`Path.parts`).
2. Resolución canónica con `Path.resolve()` y verificación estricta con `candidate.is_relative_to(root_dir)` (previene ataques de carpetas hermanas con prefijo coincidente y enlaces simbólicos externos).
3. Lista negra de archivos sensibles (`Config.SENSITIVE_FILENAMES`: `.env`, `PyWhatKit_DB.txt`, `filesPy.txt`, logs y telemetría) y extensiones prohibidas (`.db`, `.sqlite`, `.sqlite3`, `.log`, `.pem`, `.key`).
4. Exclusión de directorios internos (`.git`, `.venv`, `node_modules`, `logs`, `dist`).
5. Lista blanca de extensiones de código permitidas (`ALLOWED_CODE_EXTENSIONS`).

---

## 4. Modos de Privacidad y Uso de la Nube (`ProviderRouter`)
El usuario controla qué datos salen del equipo mediante tres variables en `.env`:
- **`ARGON_MODE=strict_local`:** Deshabilita al 100 % cualquier llamada de red hacia Google Gemini (tanto en chat, como en *tool calling* y análisis de capturas de pantalla). Toda la inferencia ocurre localmente en Ollama.
- **`ARGON_MODE=local_first` (Por defecto):** Prioriza Ollama local. Si Ollama no está disponible, consulta `CLOUD_FALLBACK` (`manual_approval`, `auto` o `disabled`).
- **`ALLOW_CLOUD_SENSITIVE_DATA=false` (Por defecto):** Bloquea el envío automático de capturas de pantalla (`analyze_screen_with_gemini`), contenido del portapapeles (`read_clipboard`) o fragmentos de código local (`analyze_code_file`) hacia proveedores en la nube a menos que el usuario otorgue permiso explícito (`"aprobar nube"`).

---

## 5. Defensa contra Prompt Injection y Sanitización de Secretos
- **Delimitación de contenido no confiable:** Los resultados de búsqueda web (`<resultados_web_no_confiables>`), el portapapeles (`<datos_portapapeles_no_confiables>`) y las salidas de herramientas (`<observaciones_herramientas>`) se encapsulan como datos y no pueden autorizar llamadas a herramientas restringidas.
- **Protección contra *Stored Prompt Injection* en SQLite:** `AdvancedSkills` bloquea cualquier intento de guardar instrucciones de manipulación (`ignora las instrucciones`, `system prompt`, `envía un whatsapp`) en la memoria permanente.
- **Filtro Anti-Secretos en SQLite y Logs (`RedactingLogFilter`):** Tanto la base de datos `argon_memory.db` como el archivo `logs/agent_activity.log` detectan y bloquean/redactan automáticamente claves de Gemini (`AIza...`), claves tipo `sk-...`, tokens de GitHub (`ghp_...`), tokens de Notion (`ntn_...` / `secret_...`), encabezados `Bearer`, contraseñas y números telefónicos.

