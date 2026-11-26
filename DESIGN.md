# Sistema de Diseño — Argon 4 // Hermes Tactical HUD

## 1. Filosofía Visual y Principios
La interfaz de **Argon 4** sigue una dirección de **Producto Tecnológico Táctico Oscuro (Tactical Developer UI)** orientada a la supervisión real del agente:
- **Cero Datos Simulados en Producción:** Cada indicador visual responde a un campo real entregado por `GET /api/state` o `GET /api/metrics`. No se muestran medidores decorativos sin respaldo en el backend.
- **Densidad Progresiva (Arquitectura Híbrida):** La vista central prioriza el flujo de conversación, los pasos en vivo (`live_steps`) y las alertas de seguridad (`pending_approvals`), mientras que el panel derecho intercambiable (*Context Inspector Drawer*) permite alternar entre Telemetría/Métricas, Memoria SQLite y Agenda Local + Notion.
- **La Seguridad es Explícita:** Las solicitudes de confirmación humana nunca se ocultan en menús secundarios; aparecen en el **Banner de Autorización Humana** con sus argumentos exactos antes de ejecutar cualquier herramienta sensible.

---

## 2. Paleta de Colores Semánticos

| Rol Semántico | Token Tailwind / Hex | Significado Operativo en Argon 4 |
| :--- | :--- | :--- |
| **Lienzo Base (Canvas)** | `#0b0c10` | Fondo principal de bajo deslumbramiento para sesiones prolongadas. |
| **Superficie Elevada (Cards/Header)** | `#11131a` / `#0e1017` | Paneles contenedores, cabecera operativa y cajón inspector lateral. |
| **Bordes Estructurales** | `border-slate-800` (`#1e293b`) | Separación nítida de `1px` entre módulos sin recargar la vista. |
| **Acento Primario (Operativo)** | `cyan-400` (`#22d3ee`) | Estado en línea, modo `local_first`, escucha activa y controles primarios. |
| **Éxito y Privacidad Local** | `emerald-400` (`#34d399`) | Estado `success` verificado, modo `strict_local` y botón de autorización. |
| **Atención / Confirmación Humana** | `amber-400` (`#fbbf24`) | Estado `approval_required`, tareas `partial` y modo `cloud_first`. |
| **Error / Denegación / Corte** | `rose-400` (`#fb7185`) | Estado `failed`, `denied`, `timeout`, borrado de recuerdos y corte de voz. |

---

## 3. Tipografía y Jerarquía
- **Interfaz y Lectura (`font-sans`):** *Inter / System UI* para mensajes extensos del agente, notas de memoria y títulos de tareas.
- **Telemetría, Estados e IDs (`font-mono`):** *JetBrains Mono / Monospace* para identificadores de aprobación (`action_id`), cronómetros de pasos (`elapsed`), porcentajes de hardware (`psutil`), argumentos JSON y métricas de latencia (`ms`).

---

## 4. Componentes y Estados Principales
1. **Header Operativo:** Muestra en todo momento el estado (`IDLE`, `LISTENING`, `TOOL_EXEC`, `SPEAKING`), el escudo de modo (`strict_local`, `local_first`, `cloud_first`), el proveedor activo (`ollama` vs `gemini`), el estado de conexión al puerto `8000` y los controles de voz (`Escuchar Voz`, `Manos Libres`, `Silenciar`).
2. **Banner de Autorización Humana (`pending_approvals`):** Se despliega condicionalmente cuando `ToolPolicyEngine` retiene una acción `external_write` o `sensitive`. Presenta herramienta, nivel de riesgo, bloque JSON de argumentos y acciones **Autorizar Ejecución** / **Rechazar**.
3. **Tarjeta de Trazabilidad en Vivo (`live_steps`):** Muestra la secuencia de pasos del `AgentExecutionLoop` con indicadores luminosos (`running` en ámbar pulsante, `done` en esmeralda) y tiempo transcurrido.
4. **Inspector Contextual Derecho (3 Pestañas):**
   - **01 Telemetría y Métricas:** Barras reales de CPU, RAM y Batería (`psutil`) + contadores de fiabilidad de la Fase 5 (`success`, `partial`, `approval_required`, `denied/failed`) e historial sanitizado.
   - **02 Memoria SQLite:** Buscador instantáneo en cliente, etiquetas de `#id`, `category` y `source` (`explicit` / `inferred`), y botón de eliminación verificada (`DELETE /api/memories/{id}`).
   - **03 Agenda y Notion:** Formulario de creación rápida y listado unificado de pendientes.

---

## 5. Reglas de Accesibilidad y Ergonomía
- Contraste mínimo WCAG AA entre textos informativos (`text-slate-100` / `text-slate-300`) y superficies oscuras (`#0b0c10` / `#11131a`).
- Ningún estado depende únicamente del color: cada insignia incluye texto explícito en mayúsculas (`SUCCESS`, `PARTIAL`, `APPROVAL_REQUIRED`, `STRICT_LOCAL`).
- Modo Enfoque (*Focus Mode*): botón dedicado en el rail lateral para colapsar el panel derecho y expandir la consola central en pantallas portátiles.
