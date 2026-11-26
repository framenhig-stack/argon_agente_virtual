# Argon 4 // Hermes Edition — Local-First Tactical AI Assistant

Asistente personal de productividad e ingeniería **local-first** para Windows 11 con arquitectura desacoplada (**FastAPI + React HUD + MCP**), inferencia local con **Ollama** y soporte opcional en la nube con **Google Gemini**, motor central de políticas de seguridad (`ToolPolicyEngine`), ciclo de ejecución agéntica con control de dependencias (`AgentExecutionLoop`) y memoria persistente auditable en **SQLite**.

---

## Arquitectura

- `main_agent.py` inicia el asistente de escritorio con voz y la interfaz Flask que utilizan los lanzadores de Windows.
- `api_server.py` expone el backend FastAPI para el HUD React y utiliza el motor de `core_agent.py`.
- `mcp_server.py` ofrece las herramientas del asistente a clientes de Model Context Protocol.
- `config.py` carga el archivo `.env` y reúne las opciones de proveedores, voz e integraciones.

## 1. Características Principales

- **Privacidad Local-First Real (`ProviderRouter`):** Opera en modos `local_first`, `strict_local` (cero llamadas a la nube garantizadas por código) o `cloud_first`. Bloquea el envío de capturas de pantalla, portapapeles o código local a la nube sin autorización.
- **Seguridad de Herramientas (`ToolPolicyEngine`):** Clasificación por nivel de riesgo (`read`, `local_write`, `external_write`, `sensitive`), validación de esquemas, idempotencia y aprobaciones humanas de un solo uso vinculadas al hash exacto de la herramienta y sus argumentos.
- **Ciclo de Ejecución Agéntica (`AgentExecutionLoop`):** Planificación multi-paso con validación de grafos de dependencias (DAG), paralelismo seguro exclusivo para lecturas independientes y encadenamiento de observaciones verificadas.
- **Memoria SQLite Gobernada (`AdvancedSkills`):** Recuperación por relevancia léxica, distinción entre recuerdos explícitos e inferidos, operaciones CRUD verificadas y filtros contra almacenamiento de claves API o *Prompt Injection*.
- **HUD Táctica Híbrida en React (`hud_ui/`):** Supervisión en tiempo real de pasos en ejecución (`live_steps`), banner interactivo para autorizar/rechazar acciones sensibles, inspector de memoria SQLite, agenda combinada (Local + Notion) y métricas de observabilidad.
- **Observabilidad y Evaluaciones (`observability.py` & `evals/`):** Redacción automática de secretos/PII en logs (`RedactingLogFilter`), métricas por categoría de fallo y suite reproducible de **50 solicitudes en español**.

---

## 2. Requisitos del Sistema

- **Sistema Operativo:** Windows 10 / Windows 11 (compatible con Linux/macOS para backend y pruebas).
- **Python:** `3.10`, `3.11` o `3.12`.
- **Node.js:** `18+` o `20+` (para la interfaz `hud_ui` con Vite y React).
- **Inferencia Local (Recomendado):** [Ollama](https://ollama.com/) instalado localmente (`ollama pull llama3.1:latest`).

---

## 3. Instalación Paso a Paso en un Entorno Limpio

### 3.1. Clonar el repositorio y preparar el entorno Python
```powershell
git clone https://github.com/framenhig-stack/argon_agente_virtual.git
cd argon_agente_virtual

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3.2. Configurar el Frontend (React HUD)
```powershell
cd hud_ui
npm install
cd ..
```

### 3.3. Configurar Variables de Entorno (`.env`)
Desde la raíz del proyecto, crea tu configuración local y edita las variables de las integraciones que vayas a usar. Puedes dejar vacíos los campos de credenciales opcionales.
```powershell
Copy-Item .env.example .env
```
El archivo `.env` permanece en tu equipo.

---

## 4. Ejecución del Sistema

### Iniciar el Servidor de Backend (FastAPI en puerto 8000)
```powershell
.\.venv\Scripts\Activate.ps1
python api_server.py
```

### Iniciar el Frontend (React HUD en puerto 5173)
```powershell
cd hud_ui
npm run dev
```
Acceder a la interfaz táctica en `http://localhost:5173`.

---

## 5. Pruebas Unitarias y Benchmark de Evaluación

### Ejecutar todas las pruebas unitarias (Fases 1 a 5)
```powershell
python -m unittest discover -s tests -v
```

### Ejecutar el benchmark reproducible (50 solicitudes en español)
```powershell
python evals/eval_suite_es.py
```

---

## 6. Servidor Model Context Protocol (MCP)

Argon 4 expone sus herramientas auditadas y gobernadas a través del protocolo MCP:
```powershell
python mcp_server.py
```
