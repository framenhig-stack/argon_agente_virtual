# Arquitectura del Sistema — Argon 4 // Hermes Edition

## 1. Visión General y Separación de Responsabilidades (SoC)
Argon 4 está diseñado como un asistente personal de IA **local-first**, modular y seguro por defecto. Su arquitectura separa estrictamente la interfaz de usuario, el transporte HTTP/MCP, la orquestación cognitiva, el motor de políticas de seguridad, los proveedores de inferencia y el almacenamiento persistente:

```text
argon4-agent/
├── api_server.py                  # Capa de transporte HTTP/REST (FastAPI + Uvicorn, puerto 8000)
├── core_agent.py                  # Orquestador principal (ArgonHermesOrchestrator)
├── config.py                      # Configuración validada, modos de privacidad y logging seguro
├── mcp_server.py                  # Servidor Model Context Protocol (MCP) gobernado por políticas
├── modules/
│   ├── tool_policy.py             # Motor central de permisos, riesgos, esquemas e idempotencia (Fase 1)
│   ├── llm_providers.py           # Adaptadores Ollama/Gemini y compuerta ProviderRouter (Fase 2)
│   ├── agent_loop.py              # Ciclo de ejecución agéntica, DAG de dependencias y límites (Fase 3)
│   ├── advanced_skills.py         # Memoria SQLite gobernada, web, portapapeles y procesos (Fase 4)
│   ├── observability.py           # Redacción de secretos en logs y recolector de métricas (Fase 5)
│   ├── tool_router.py             # Registro y despacho unificado de herramientas
│   ├── productivity_tools.py      # Agenda local JSON, IMAP y auditor AST con validación canónica
│   ├── system_tasks.py            # Telemetría psutil, capturas de pantalla y apertura de apps
│   ├── notion_bridge.py           # Sincronización con Notion API y skin Rainmeter
│   ├── whatsapp_bridge.py         # Puente de mensajería WhatsApp sujeto a confirmación
│   ├── voice_engine.py            # Síntesis neuronal grave y reconocimiento de voz
│   └── voip_caller.py             # Sala de voz WebRTC
├── hud_ui/                        # Frontend React + Vite + Tailwind CSS (puerto 5173)
├── tests/                         # Suite de pruebas unitarias e integración (Fases 1 a 6)
├── evals/                         # Arnés reproducible de 50 solicitudes en español
└── docs/                          # Documentación técnica y de seguridad
```

