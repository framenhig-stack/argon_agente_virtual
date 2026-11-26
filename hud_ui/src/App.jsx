import { useState, useEffect, useRef } from 'react';

const API_BASE = 'http://127.0.0.1:8000';

const DEMO_STATE = {
  state: 'IDLE',
  active_tool: 'NONE',
  last_action: 'Núcleo Argon 4 // Hermes listo en modo local_first.',
  is_processing: false,
  argon_mode: 'local_first',
  model: 'ollama (llama3.1:latest)',
  notion_enabled: true,
  live_steps: [
    { label: 'Consultando memoria cognitiva SQLite...', status: 'done', elapsed: '0.1s' },
    { label: '[TOOL_POLICY] Validando permisos y rutas...', status: 'done', elapsed: '0.2s' }
  ],
  pending_approvals: [],
  telemetry: {
    cpu_percent: 14,
    ram_percent: 48,
    ram_available_gb: 8.4,
    battery_percent: 96
  },
  memories: [
    { id: 1, category: 'Proyecto', note: 'Arquitectura desacoplada FastAPI + React HUD', date: '2026-10-23 09:30', source: 'explicit' },
    { id: 2, category: 'Preferencia', note: 'Modo local_first activado por defecto por privacidad', date: '2026-10-23 10:00', source: 'explicit' }
  ],
  calendar: [
    { id: 1, title: 'Revisar arquitectura de Argon 4 en VS Code', datetime: '2026-10-23 18:30', status: 'pendiente' }
  ],
  logs: [
    { sender: 'ARGON 4', text: 'Sistema táctico Hermes en línea. Todos los controles de seguridad de las Fases 1 a 5 están activos.', tag: 'agent' }
  ]
};

const DEMO_METRICS = {
  total_tool_calls: 12,
  completion_rate_pct: 100.0,
  status_counts: { success: 11, partial: 1, failed: 0, denied: 0, approval_required: 0, timeout: 0 },
  failure_categories: { model_error: 0, tool_error: 0, network_error: 0, permission_denied: 0, approval_required: 0, timeout: 0 },
  recent_events: [
    { timestamp: '10:45:12', tool: 'get_system_status', status: 'success', duration_ms: 8.4, error: '' },
    { timestamp: '10:46:05', tool: 'save_memory', status: 'success', duration_ms: 14.2, error: '' }
  ]
};

function App() {
  const [agentState, setAgentState] = useState(DEMO_STATE);
  const [metrics, setMetrics] = useState(DEMO_METRICS);
  const [backendOnline, setBackendOnline] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [activeTab, setActiveTab] = useState('telemetry');
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [commandInput, setCommandInput] = useState('');
  const [memoryQuery, setMemoryQuery] = useState('');
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [handsfreeActive, setHandsfreeActive] = useState(false);
  const feedEndRef = useRef(null);

  useEffect(() => {
    if (demoMode) {
      return;
    }
    let mounted = true;

    const fetchState = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/state`);
        if (!res.ok) throw new Error('HTTP error');
        const data = await res.json();
        if (mounted) {
          setAgentState((prev) => ({
            ...prev,
            ...data,
            telemetry: data.telemetry || prev.telemetry,
            memories: data.memories || [],
            calendar: data.calendar || [],
            logs: data.logs && data.logs.length > 0 ? data.logs : prev.logs,
            pending_approvals: data.pending_approvals || [],
            live_steps: data.live_steps || []
          }));
          setBackendOnline(true);
        }
        const mRes = await fetch(`${API_BASE}/api/metrics`);
        if (mRes.ok && mounted) {
          const mData = await mRes.json();
          setMetrics(mData);
        }
      } catch {
        if (mounted) {
          setBackendOnline(false);
        }
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 1200);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [demoMode]);

  useEffect(() => {
    if (feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [agentState.logs, agentState.live_steps]);

  const sendCommand = async (rawText) => {
    const text = (rawText !== undefined ? rawText : commandInput).trim();
    if (!text) return;
    if (rawText === undefined) setCommandInput('');

    if (demoMode || !backendOnline) {
      const nextLogs = [...(agentState.logs || []), { sender: 'USUARIO', text, tag: 'user' }];
      if (text.toLowerCase().includes('whatsapp')) {
        setAgentState((prev) => ({
          ...prev,
          logs: [
            ...nextLogs,
            {
              sender: 'ARGON 4',
              text: 'Por seguridad, enviar WhatsApp requiere tu confirmación explícita en el banner superior.',
              tag: 'agent'
            }
          ],
          pending_approvals: [
            {
              action_id: 'send_whatsapp_demo01',
              tool: 'send_whatsapp',
              risk_level: 'external_write',
              args: { phone: 'Destino de demostración', message: text },
              requested_at: new Date().toLocaleTimeString()
            }
          ]
        }));
      } else {
        setAgentState((prev) => ({
          ...prev,
          logs: [
            ...nextLogs,
            {
              sender: 'ARGON 4',
              text: `[Respuesta Simulada en Modo Demo] Procesado comando: "${text}". Enciende api_server.py en el puerto 8000 para ejecución real.`,
              tag: 'agent'
            }
          ]
        }));
      }
      return;
    }

    try {
      await fetch(`${API_BASE}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
    } catch {
      setBackendOnline(false);
    }
  };

  const handleApproval = async (actionId, approve) => {
    if (demoMode || !backendOnline) {
      setAgentState((prev) => ({
        ...prev,
        pending_approvals: prev.pending_approvals.filter((a) => a.action_id !== actionId),
        logs: [
          ...prev.logs,
          {
            sender: 'ARGON 4',
            text: approve
              ? `Acción ${actionId} autorizada y ejecutada (Demo).`
              : `Acción ${actionId} denegada y descartada por seguridad.`,
            tag: 'agent'
          }
        ]
      }));
      return;
    }

    const endpoint = approve ? 'approve' : 'deny';
    await fetch(`${API_BASE}/api/approvals/${actionId}/${endpoint}`, { method: 'POST' });
  };

  const handleDeleteMemory = async (memId) => {
    if (demoMode || !backendOnline) {
      setAgentState((prev) => ({
        ...prev,
        memories: prev.memories.filter((m) => m.id !== memId)
      }));
      return;
    }
    await fetch(`${API_BASE}/api/memories/${memId}`, { method: 'DELETE' });
  };

  const triggerListen = async () => {
    if (!demoMode && backendOnline) {
      await fetch(`${API_BASE}/api/listen`, { method: 'POST' });
    }
  };

  const toggleHandsfree = async () => {
    if (!demoMode && backendOnline) {
      const res = await fetch(`${API_BASE}/api/handsfree`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setHandsfreeActive(Boolean(data.handsfree));
      }
    } else {
      setHandsfreeActive((prev) => !prev);
    }
  };

  const stopVoice = async () => {
    if (!demoMode && backendOnline) {
      await fetch(`${API_BASE}/api/stop_voice`, { method: 'POST' });
    }
  };

  const simulateDemoState = (preset) => {
    setDemoMode(true);
    if (preset === 'IDLE') {
      setAgentState(DEMO_STATE);
    } else if (preset === 'PROCESSING') {
      setAgentState({
        ...DEMO_STATE,
        state: 'TOOL_EXEC',
        active_tool: 'AGENT_LOOP',
        is_processing: true,
        live_steps: [
          { label: 'Paso 1: get_system_status (lectura local)', status: 'done', elapsed: '0.1s' },
          { label: 'Paso 2: save_memory (encadenando observación...)', status: 'running', elapsed: '0.4s' }
        ]
      });
    } else if (preset === 'APPROVAL') {
      setAgentState({
        ...DEMO_STATE,
        state: 'IDLE',
        pending_approvals: [
          {
            action_id: 'send_whatsapp_a8f921',
            tool: 'send_whatsapp',
            risk_level: 'external_write',
            args: { phone: 'Destino de demostración', message: 'Hola equipo, el prototipo de Argon 4 está listo.' },
            requested_at: '10:52:00'
          }
        ]
      });
    } else if (preset === 'STRICT_LOCAL') {
      setAgentState({
        ...DEMO_STATE,
        argon_mode: 'strict_local',
        model: 'ollama (llama3.1:latest)',
        last_action: 'Modo Estricto Local activo: Cero llamadas a la nube permitidas.'
      });
    }
  };

  const filteredMemories = (agentState.memories || []).filter((m) => {
    if (!memoryQuery.trim()) return true;
    const q = memoryQuery.toLowerCase();
    return (
      String(m.note || '').toLowerCase().includes(q) ||
      String(m.category || '').toLowerCase().includes(q)
    );
  });

  const modeBadgeColor =
    agentState.argon_mode === 'strict_local'
      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'
      : agentState.argon_mode === 'local_first'
      ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/40'
      : 'bg-amber-500/15 text-amber-300 border-amber-500/40';

  const stateBadgeColor =
    agentState.state === 'TOOL_EXEC' || agentState.is_processing
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
      : agentState.state === 'SPEAKING' || agentState.state === 'LISTENING'
      ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
      : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';

  return (
    <div className="min-h-screen bg-[#0b0c10] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30">
      {/* BARRA SUPERIOR OPERATIVA */}
      <header className="h-16 border-b border-slate-800/90 bg-[#11131a]/95 backdrop-blur px-4 lg:px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-cyan-400 shadow-[0_0_12px_#22d3ee]" />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-wider text-sm lg:text-base text-white">
                ARGON 4 // HERMES
              </span>
              <span className={`text-[11px] px-2 py-0.5 rounded border font-mono uppercase ${stateBadgeColor}`}>
                {agentState.state}
              </span>
              <span className={`text-[11px] px-2 py-0.5 rounded border font-mono uppercase ${modeBadgeColor}`}>
                {agentState.argon_mode || 'local_first'}
              </span>
            </div>
            <p className="text-xs text-slate-400 truncate max-w-md hidden sm:block">
              Motor: <span className="text-slate-200 font-mono">{agentState.model}</span> ·{' '}
              {backendOnline && !demoMode ? (
                <span className="text-emerald-400">Backend 8000 Conectado</span>
              ) : (
                <span className="text-amber-400">Modo Prototipo / Demo Aislado</span>
              )}
            </p>
          </div>
        </div>

        {/* CONTROLES DE VOZ Y SIMULACIÓN DE ESTADOS */}
        <div className="flex items-center gap-2">
          <div className="hidden xl:flex items-center gap-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1 mr-2">
            <span className="text-[10px] text-slate-400 px-2 uppercase font-mono">Probar Estado:</span>
            <button
              onClick={() => simulateDemoState('IDLE')}
              className="text-xs px-2 py-1 rounded hover:bg-slate-800 text-slate-300"
            >
              Idle
            </button>
            <button
              onClick={() => simulateDemoState('PROCESSING')}
              className="text-xs px-2 py-1 rounded hover:bg-slate-800 text-cyan-300"
            >
              Pasos en Vivo
            </button>
            <button
              onClick={() => simulateDemoState('APPROVAL')}
              className="text-xs px-2 py-1 rounded hover:bg-slate-800 text-amber-300"
            >
              Aprobación
            </button>
            <button
              onClick={() => simulateDemoState('STRICT_LOCAL')}
              className="text-xs px-2 py-1 rounded hover:bg-slate-800 text-emerald-300"
            >
              Strict Local
            </button>
            {demoMode && (
              <button
                onClick={() => setDemoMode(false)}
                className="text-xs px-2 py-1 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
              >
                Conectar Real
              </button>
            )}
          </div>

          <button
            onClick={triggerListen}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 transition"
          >
            Escuchar Voz
          </button>
          <button
            onClick={toggleHandsfree}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
              handsfreeActive
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-800'
            }`}
          >
            {handsfreeActive ? 'Manos Libres: ON' : 'Manos Libres'}
          </button>
          <button
            onClick={stopVoice}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition"
          >
            Silenciar
          </button>
        </div>
      </header>

      {/* CUERPO PRINCIPAL: NAVEGACIÓN LATERAL + CONSOLA CENTRAL + DRAWER DERECHO */}
      <div className="flex-1 flex overflow-hidden">
        {/* RAIL LATERAL DE NAVEGACIÓN */}
        <aside className="w-16 md:w-56 border-r border-slate-800/90 bg-[#0e1017] flex flex-col justify-between p-3 shrink-0">
          <div className="space-y-1.5">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-2 py-1 hidden md:block">
              Paneles de Control
            </div>
            <button
              onClick={() => {
                setActiveTab('telemetry');
                setDrawerOpen(true);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'telemetry' && drawerOpen
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <span className="font-mono text-sm">01</span>
              <span className="hidden md:inline">Telemetría y Métricas</span>
            </button>

            <button
              onClick={() => {
                setActiveTab('memories');
                setDrawerOpen(true);
              }}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'memories' && drawerOpen
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm">02</span>
                <span className="hidden md:inline">Memoria SQLite</span>
              </div>
              <span className="hidden md:inline text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                {(agentState.memories || []).length}
              </span>
            </button>

            <button
              onClick={() => {
                setActiveTab('calendar');
                setDrawerOpen(true);
              }}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'calendar' && drawerOpen
                  ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm">03</span>
                <span className="hidden md:inline">Agenda y Notion</span>
              </div>
              <span className="hidden md:inline text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                {(agentState.calendar || []).length}
              </span>
            </button>

            <button
              onClick={() => setDrawerOpen((prev) => !prev)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 transition mt-4 border border-slate-800/80"
            >
              <span className="font-mono text-sm">{drawerOpen ? '»' : '«'}</span>
              <span className="hidden md:inline">
                {drawerOpen ? 'Modo Enfoque (Ocultar)' : 'Mostrar Inspector'}
              </span>
            </button>
          </div>

          {/* RESUMEN RÁPIDO DE HARDWARE EN BARRA LATERAL */}
          <div className="hidden md:block p-3 rounded-xl bg-slate-900/90 border border-slate-800/90 space-y-2">
            <div className="text-[10px] font-mono uppercase text-slate-400 flex justify-between">
              <span>Hardware Real</span>
              <span className="text-emerald-400">psutil</span>
            </div>
            <div className="text-xs flex justify-between text-slate-300">
              <span>CPU</span>
              <span className="font-mono">{agentState.telemetry?.cpu_percent ?? 0}%</span>
            </div>
            <div className="text-xs flex justify-between text-slate-300">
              <span>RAM</span>
              <span className="font-mono">{agentState.telemetry?.ram_percent ?? 0}%</span>
            </div>
            <div className="text-xs flex justify-between text-slate-300">
              <span>Batería</span>
              <span className="font-mono">{agentState.telemetry?.battery_percent ?? 100}%</span>
            </div>
          </div>
        </aside>

        {/* ÁREA CENTRAL: BANNER DE APROBACIÓN + PASOS EN VIVO + TERMINAL DE COMANDOS */}
        <main className="flex-1 flex flex-col min-w-0 bg-[#0b0c10] p-4 lg:p-6 gap-4 overflow-y-auto">
          {/* 1. BANNER DE AUTORIZACIÓN HUMANA (FASE 1 Y 2) */}
          {agentState.pending_approvals && agentState.pending_approvals.length > 0 && (
            <div className="rounded-xl border border-amber-500/50 bg-amber-500/10 p-4 space-y-3 shadow-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[11px] font-mono uppercase rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    Autorización Requerida
                  </span>
                  <h3 className="text-sm font-semibold text-amber-200">
                    ToolPolicyEngine bloqueó una acción sensible esperando tu confirmación
                  </h3>
                </div>
                <span className="text-xs font-mono text-amber-300/80">
                  {agentState.pending_approvals.length} pendiente(s)
                </span>
              </div>

              {agentState.pending_approvals.map((req) => (
                <div
                  key={req.action_id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950/80 border border-amber-500/30 rounded-lg p-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-bold text-white">{req.tool}</span>
                      <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-amber-300">
                        riesgo: {req.risk_level}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">ID: {req.action_id}</span>
                    </div>
                    <pre className="text-xs font-mono text-slate-300 bg-slate-900/90 p-2 rounded border border-slate-800 overflow-x-auto">
                      {JSON.stringify(req.args, null, 2)}
                    </pre>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleApproval(req.action_id, true)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition"
                    >
                      Autorizar Ejecución
                    </button>
                    <button
                      onClick={() => handleApproval(req.action_id, false)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 transition"
                    >
                      Rechazar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 2. TRAZABILIDAD DE PASOS EN VIVO (FASE 3 - AGENT LOOP) */}
          {agentState.live_steps && agentState.live_steps.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-mono uppercase tracking-wider text-cyan-400">
                  Trazabilidad del Ciclo Agéntico · Herramienta Activa: {agentState.active_tool}
                </span>
                <span className="font-mono">
                  {agentState.is_processing ? 'Ejecutando plan...' : 'Completado'}
                </span>
              </div>
              <div className="space-y-1.5">
                {agentState.live_steps.map((step, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs font-mono bg-slate-900/70 px-3 py-1.5 rounded border border-slate-800/80"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          step.status === 'running'
                            ? 'bg-amber-400 animate-pulse'
                            : 'bg-emerald-400'
                        }`}
                      />
                      <span className="text-slate-200 truncate">{step.label}</span>
                    </div>
                    <span className="text-slate-400 ml-3 shrink-0">{step.elapsed}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. CONSOLA DE CONVERSACIÓN Y RESULTADOS VERIFICADOS */}
          <div className="flex-1 rounded-xl border border-slate-800 bg-[#11131a] flex flex-col overflow-hidden min-h-[380px]">
            <div className="px-4 py-2.5 border-b border-slate-800/90 flex items-center justify-between bg-slate-900/50">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                Registro de Operaciones y Respuestas Verificadas
              </span>
              <button
                onClick={() => sendCommand('aprobar nube')}
                className="text-[11px] font-mono px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 transition"
              >
                Autorizar Nube (1 vez)
              </button>
            </div>

            <div className="flex-1 p-4 space-y-3 overflow-y-auto">
              {(agentState.logs || []).map((entry, idx) => {
                const isUser = entry.tag === 'user' || entry.sender?.includes('USUARIO');
                return (
                  <div
                    key={idx}
                    className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                  >
                    <div className="text-[10px] font-mono text-slate-400 mb-1 px-1">
                      {entry.sender}
                    </div>
                    <div
                      className={`max-w-2xl rounded-xl px-4 py-2.5 text-sm leading-relaxed border ${
                        isUser
                          ? 'bg-cyan-500/15 text-cyan-100 border-cyan-500/30'
                          : 'bg-slate-900/90 text-slate-200 border-slate-800'
                      }`}
                    >
                      {entry.text}
                    </div>
                  </div>
                );
              })}
              <div ref={feedEndRef} />
            </div>

            {/* BARRA DE ENTRADA DE COMANDOS */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendCommand();
              }}
              className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center gap-2"
            >
              <input
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                placeholder="Escribe una orden para Argon 4 (ej. 'estado del sistema y luego guarda resumen en memoria')..."
                className="flex-1 bg-slate-900 border border-slate-700/80 focus:border-cyan-400 rounded-lg px-3.5 py-2 text-sm text-white placeholder-slate-500 outline-none"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider bg-cyan-400 hover:bg-cyan-300 text-slate-950 transition"
              >
                Ejecutar
              </button>
            </form>
          </div>
        </main>

        {/* PANEL CONTEXTUAL DERECHO (DRAWER INTERCAMBIABLE CON 3 PESTAÑAS) */}
        {drawerOpen && (
          <aside className="w-80 lg:w-96 border-l border-slate-800/90 bg-[#0e1017] p-4 overflow-y-auto shrink-0 space-y-4">
            {/* PESTAÑA 1: TELEMETRÍA REAL Y OBSERVABILIDAD FASE 5 */}
            {activeTab === 'telemetry' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h2 className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                    Telemetría Real y Observabilidad
                  </h2>
                  <span className="text-[11px] font-mono text-emerald-400">
                    Éxito: {metrics.completion_rate_pct ?? 100}%
                  </span>
                </div>

                {/* Barras de Hardware Real (psutil) */}
                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Uso de CPU</span>
                      <span className="font-mono text-cyan-300">
                        {agentState.telemetry?.cpu_percent ?? 0}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-400 transition-all"
                        style={{ width: `${Math.min(100, agentState.telemetry?.cpu_percent ?? 0)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">
                        Memoria RAM ({agentState.telemetry?.ram_available_gb ?? '--'} GB libres)
                      </span>
                      <span className="font-mono text-cyan-300">
                        {agentState.telemetry?.ram_percent ?? 0}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-400 transition-all"
                        style={{ width: `${Math.min(100, agentState.telemetry?.ram_percent ?? 0)}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">Batería del Sistema</span>
                      <span className="font-mono text-emerald-300">
                        {agentState.telemetry?.battery_percent ?? 100}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-400 transition-all"
                        style={{ width: `${Math.min(100, agentState.telemetry?.battery_percent ?? 100)}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Métricas de Herramientas (Fase 5) */}
                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2.5">
                  <div className="text-xs font-semibold text-slate-200">
                    Conteo Verificado de Herramientas ({metrics.total_tool_calls ?? 0})
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between">
                      <span className="text-emerald-400">Success:</span>
                      <span>{metrics.status_counts?.success ?? 0}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between">
                      <span className="text-amber-400">Partial:</span>
                      <span>{metrics.status_counts?.partial ?? 0}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between">
                      <span className="text-amber-300">Approval:</span>
                      <span>{metrics.status_counts?.approval_required ?? 0}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between">
                      <span className="text-rose-400">Denied/Fail:</span>
                      <span>
                        {(metrics.status_counts?.denied ?? 0) + (metrics.status_counts?.failed ?? 0)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Eventos Recientes Sanitizados */}
                <div className="space-y-2">
                  <div className="text-xs font-mono uppercase text-slate-400">
                    Eventos Recientes de Herramientas
                  </div>
                  {(metrics.recent_events || []).map((ev, i) => (
                    <div
                      key={i}
                      className="text-xs font-mono p-2.5 rounded-lg bg-slate-900/70 border border-slate-800 flex items-center justify-between"
                    >
                      <div className="truncate">
                        <span className="text-slate-200">{ev.tool}</span>
                        <span className="text-slate-500 ml-2">{ev.timestamp}</span>
                      </div>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                          ev.status === 'success'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : ev.status === 'approval_required' || ev.status === 'partial'
                            ? 'bg-amber-500/15 text-amber-300'
                            : 'bg-rose-500/15 text-rose-300'
                        }`}
                      >
                        {ev.status} ({ev.duration_ms}ms)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* PESTAÑA 2: BANCO DE MEMORIA SQLITE (FASE 4) */}
            {activeTab === 'memories' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h2 className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                    Memoria Persistente SQLite
                  </h2>
                  <span className="text-xs font-mono text-slate-400">
                    {filteredMemories.length} registros
                  </span>
                </div>

                <input
                  type="text"
                  value={memoryQuery}
                  onChange={(e) => setMemoryQuery(e.target.value)}
                  placeholder="Buscar por texto o categoría..."
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-cyan-400"
                />

                <div className="space-y-2">
                  {filteredMemories.map((m) => (
                    <div
                      key={m.id}
                      className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <div className="flex items-center gap-1.5">
                          <span className="text-cyan-400 font-bold">#{m.id}</span>
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                            {m.category}
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-slate-950 text-slate-400">
                            {m.source || 'explicit'}
                          </span>
                        </div>
                        <button
                          onClick={() => handleDeleteMemory(m.id)}
                          className="text-rose-400 hover:text-rose-300 px-1.5 py-0.5 rounded hover:bg-rose-500/10 transition"
                        >
                          Borrar
                        </button>
                      </div>
                      <p className="text-xs text-slate-200 leading-relaxed">{m.note}</p>
                      <div className="text-[10px] font-mono text-slate-500">{m.date}</div>
                    </div>
                  ))}
                  {filteredMemories.length === 0 && (
                    <p className="text-xs text-slate-500 text-center py-6">
                      No hay recuerdos que coincidan con el filtro.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* PESTAÑA 3: AGENDA UNIFICADA LOCAL + NOTION */}
            {activeTab === 'calendar' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <h2 className="text-xs font-mono uppercase tracking-wider text-cyan-400">
                    Agenda Local + Notion
                  </h2>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                      agentState.notion_enabled
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {agentState.notion_enabled ? 'Notion Activo' : 'Solo Local'}
                  </span>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!newTaskTitle.trim()) return;
                    sendCommand(`agendar ${newTaskTitle.trim()}`);
                    setNewTaskTitle('');
                  }}
                  className="flex gap-1.5"
                >
                  <input
                    type="text"
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    placeholder="Nuevo pendiente..."
                    className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-cyan-400"
                  />
                  <button
                    type="submit"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30"
                  >
                    + Agendar
                  </button>
                </form>

                <div className="space-y-2">
                  {(agentState.calendar || []).map((ev, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1"
                    >
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span className="text-cyan-400">#{ev.id}</span>
                        <span className="text-slate-400">{ev.datetime || 'Activo'}</span>
                      </div>
                      <p className="text-xs text-slate-200">{ev.title}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

export default App;