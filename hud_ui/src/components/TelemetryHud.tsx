function TelemetryHUD() {
  return (
    <aside className="xl:col-span-4 flex flex-col gap-space-md">
      {/* Telemetry Card 1: Main Core Matrix */}
      <div className="bg-surface-container-low/90 backdrop-blur-xl rounded-xl p-space-md lg:p-space-lg shadow-xl flex flex-col gap-space-md">
        {/* HUD Header */}
        <div className="flex items-center justify-between pb-space-xs bg-surface-container-high/30 p-space-xs rounded">
          <div className="flex items-center gap-space-xs">
            <span className="material-symbols-outlined text-secondary text-[20px]">equalizer</span>
            <span className="font-headline-md text-headline-md text-primary font-bold tracking-wide">TELEMETRÍA HUD</span>
          </div>
          <span className="font-label-code text-label-code text-primary-container animate-pulse">SINK://ONLINE</span>
        </div>

        {/* CPU USAGE */}
        <div className="space-y-space-xs">
          <div className="flex justify-between items-end font-label-code text-label-code">
            <span className="text-on-surface font-semibold flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px] text-primary-container">memory</span>
              USO DE CPU
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-primary-container font-telemetry-lg text-telemetry-lg font-bold">78%</span>
              <span className="text-outline text-telemetry-sm">/ 4.6 GHz</span>
            </div>
          </div>
          <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden p-0.5">
            <div className="h-full bg-primary-container rounded-full shadow-[0_0_10px_rgba(0,240,255,0.8)]" style={{ width: '78%' }}></div>
          </div>
          <div className="flex justify-between items-center text-outline font-label-code text-label-code">
            <span>16 NÚCLEOS LÓGICOS</span>
            <span className="text-secondary">AVX-512 ACTIVE</span>
          </div>
        </div>

        {/* MEMORY / VRAM */}
        <div className="space-y-space-xs pt-space-xs">
          <div className="flex justify-between items-end font-label-code text-label-code">
            <span className="text-on-surface font-semibold flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px] text-secondary">storage</span>
              MEMORIA VRAM ASIGNADA
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-secondary font-telemetry-lg text-telemetry-lg font-bold">64%</span>
              <span className="text-outline text-telemetry-sm">(20.4 / 32.0 GB)</span>
            </div>
          </div>
          <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden p-0.5">
            <div className="h-full bg-secondary rounded-full shadow-[0_0_10px_rgba(67,226,242,0.8)]" style={{ width: '64%' }}></div>
          </div>
          <div className="flex justify-between items-center text-outline font-label-code text-label-code">
            <span>PAGINACIÓN: ZERO-COPY</span>
            <span className="text-primary-container font-mono">11.6 GB LIBRE</span>
          </div>
        </div>

        {/* MODEL LATENCY & TOKEN VELOCITY */}
        <div className="space-y-space-xs pt-space-xs">
          <div className="flex justify-between items-end font-label-code text-label-code">
            <span className="text-on-surface font-semibold flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px] text-primary-fixed">speed</span>
              LATENCIA MODELO
            </span>
            <div className="flex items-baseline gap-1">
              <span className="text-primary font-telemetry-lg text-telemetry-lg font-bold">14.2</span>
              <span className="text-outline text-telemetry-sm">ms / token</span>
            </div>
          </div>
          <div className="bg-surface-container-lowest p-space-sm rounded-lg flex items-center justify-between">
            <div className="flex flex-col">
              <span className="font-label-code text-label-code text-outline">GENERACIÓN CONTINUA</span>
              <span className="font-telemetry-lg text-telemetry-lg font-bold text-primary-container">58.4 tok/s</span>
            </div>
            <div className="flex flex-col text-right">
              <span className="font-label-code text-label-code text-outline">TIME TO FIRST TOKEN</span>
              <span className="font-telemetry-lg text-telemetry-lg font-bold text-secondary">38.6 ms</span>
            </div>
          </div>
        </div>

        {/* REALTIME THROUGHPUT SVG CHART */}
        <div className="space-y-space-xs pt-space-xs">
          <div className="flex justify-between items-center font-label-code text-label-code">
            <span className="text-on-surface font-semibold flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px] text-secondary">show_chart</span>
              THROUGHPUT TEMPORAL (60 SEG)
            </span>
            <span className="text-primary-container font-mono">AVG: 56.9 t/s</span>
          </div>
          <div className="w-full bg-surface-container-lowest rounded-lg p-space-sm relative overflow-hidden">
            <svg className="w-full h-20 overflow-visible" preserveAspectRatio="none" viewBox="0 0 320 80">
              <line className="text-surface-container-highest" stroke="currentColor" strokeDasharray="3 3" x1="0" x2="320" y1="20" y2="20"></line>
              <line className="text-surface-container-highest" stroke="currentColor" strokeDasharray="3 3" x1="0" x2="320" y1="40" y2="40"></line>
              <line className="text-surface-container-highest" stroke="currentColor" strokeDasharray="3 3" x1="0" x2="320" y1="60" y2="60"></line>
              <defs>
                <linearGradient id="cyanGlow" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.35"></stop>
                  <stop offset="100%" stopColor="#00f0ff" stopOpacity="0.0"></stop>
                </linearGradient>
              </defs>
              <path d="M 0,55 Q 30,50 60,35 T 120,40 T 180,22 T 240,30 T 290,15 L 320,18 L 320,80 L 0,80 Z" fill="url(#cyanGlow)"></path>
              <path className="drop-shadow-[0_0_6px_rgba(0,240,255,0.8)]" d="M 0,55 Q 30,50 60,35 T 120,40 T 180,22 T 240,30 T 290,15 L 320,18" fill="none" stroke="#00f0ff" strokeWidth="2.5"></path>
              <circle className="shadow-lg" cx="320" cy="18" fill="#dbfcff" r="4"></circle>
              <circle className="animate-ping" cx="320" cy="18" fill="none" r="7" stroke="#00f0ff" strokeWidth="1.5"></circle>
            </svg>
          </div>
        </div>

        {/* GPU METRICS & TENSOR STATUS GRID */}
        <div className="grid grid-cols-2 gap-space-xs pt-space-xs">
          <div className="bg-surface-container p-space-sm rounded-lg flex flex-col">
            <span className="font-label-code text-label-code text-outline">TEMP GPU</span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="material-symbols-outlined text-[16px] text-emerald-400">thermostat</span>
              <span className="font-telemetry-lg text-telemetry-lg font-bold text-on-surface">54°C</span>
              <span className="font-label-code text-label-code text-emerald-300">ESTABLE</span>
            </div>
          </div>
          <div className="bg-surface-container p-space-sm rounded-lg flex flex-col">
            <span className="font-label-code text-label-code text-outline">POTENCIA</span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="material-symbols-outlined text-[16px] text-secondary">bolt</span>
              <span className="font-telemetry-lg text-telemetry-lg font-bold text-on-surface">182W</span>
              <span className="font-label-code text-label-code text-secondary font-mono">TDP 220W</span>
            </div>
          </div>
          <div className="bg-surface-container p-space-sm rounded-lg flex flex-col">
            <span className="font-label-code text-label-code text-outline">TENSORES ACTIVOS</span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="material-symbols-outlined text-[16px] text-primary-container">hub</span>
              <span className="font-telemetry-lg text-telemetry-lg font-bold text-primary-container">128/128</span>
            </div>
          </div>
          <div className="bg-surface-container p-space-sm rounded-lg flex flex-col">
            <span className="font-label-code text-label-code text-outline">CHECKPOINT</span>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="material-symbols-outlined text-[16px] text-on-surface-variant">check_circle</span>
              <span className="font-telemetry-md text-telemetry-md font-bold text-on-surface">SAFE_SYNC</span>
            </div>
          </div>
        </div>
      </div>

      {/* Telemetry Card 2: Neural Shard Status */}
      <div className="bg-surface-container-low/90 backdrop-blur-xl rounded-xl p-space-md shadow-xl flex flex-col gap-space-sm">
        <div className="flex items-center justify-between pb-1">
          <span className="font-label-code text-label-code text-primary font-bold uppercase tracking-wider">
            TOPOLOGÍA DE NODO // HERMES
          </span>
          <span className="font-label-code text-label-code text-outline">0x8849-AF</span>
        </div>
        <div className="space-y-1.5 font-label-code text-label-code">
          <div className="flex justify-between items-center bg-surface-container-lowest px-space-sm py-1 rounded">
            <span className="text-on-surface-variant">SHARD 01: Multi-Head QK</span>
            <span className="text-emerald-400 font-bold">ACTIVO [0.99]</span>
          </div>
          <div className="flex justify-between items-center bg-surface-container-lowest px-space-sm py-1 rounded">
            <span className="text-on-surface-variant">SHARD 02: Feed-Forward SwiGLU</span>
            <span className="text-emerald-400 font-bold">ACTIVO [1.00]</span>
          </div>
          <div className="flex justify-between items-center bg-surface-container-lowest px-space-sm py-1 rounded">
            <span className="text-on-surface-variant">SHARD 03: KV Cache Paged</span>
            <span className="text-secondary font-bold">OPTIMIZADO</span>
          </div>
          <div className="flex justify-between items-center bg-surface-container-lowest px-space-sm py-1 rounded">
            <span className="text-on-surface-variant">SHARD 04: Vector Ring Buffer</span>
            <span className="text-primary-container font-bold">ENLACE SÓLIDO</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default TelemetryHUD;
