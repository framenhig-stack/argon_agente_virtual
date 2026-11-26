function StatusBar() {
  return (
    <section className="w-full bg-surface-container-low/90 backdrop-blur-xl rounded-xl p-space-md shadow-xl flex flex-wrap items-center justify-between gap-space-md">
      <div className="flex items-center gap-space-md">
        <div className="flex flex-col">
          <span className="font-headline-md text-headline-md tracking-wider text-primary font-bold uppercase drop-shadow-[0_0_12px_rgba(0,240,255,0.45)]">
            ARGON 4 HERMES
          </span>
          <span className="font-label-code text-label-code text-secondary tracking-widest">
            SISTEMA DE RAZONAMIENTO NEURONAL PROFUNDO // OPERACIÓN LOCAL
          </span>
        </div>
        <div className="flex items-center gap-space-sm bg-surface-container-highest px-space-md py-space-xs rounded-full shadow-[inset_0_1px_3px_rgba(0,0,0,0.8)]">
          <div className="relative flex items-center justify-center w-2.5 h-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-80"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]"></span>
          </div>
          <span className="font-label-code text-label-code text-emerald-300 font-semibold uppercase tracking-wider">
            Sistema en línea (Local)
          </span>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-space-xs lg:gap-space-sm">
        <div className="flex items-center gap-space-xs bg-surface-container px-space-sm py-space-xs rounded font-label-code text-label-code text-on-surface-variant shadow-sm">
          <span className="text-primary-container">LATENCIA:</span>
          <span className="text-secondary font-bold">12ms</span>
        </div>
        <div className="flex items-center gap-space-xs bg-surface-container px-space-sm py-space-xs rounded font-label-code text-label-code text-on-surface-variant shadow-sm">
          <span className="text-primary-container">KERNEL:</span>
          <span className="text-on-surface font-bold">4.8.2-hms</span>
        </div>
        <div className="flex items-center gap-space-xs bg-surface-container px-space-sm py-space-xs rounded font-label-code text-label-code text-on-surface-variant shadow-sm">
          <span className="text-primary-container">QUANT:</span>
          <span className="text-secondary font-bold">Q4_K_M</span>
        </div>
        <div className="hidden sm:flex items-center gap-space-xs bg-surface-container px-space-sm py-space-xs rounded font-label-code text-label-code text-on-surface-variant shadow-sm">
          <span className="text-primary-container">CONTEXTO:</span>
          <span className="text-on-surface font-bold">32.768 TK</span>
        </div>
        <div className="flex items-center bg-surface-container-high px-space-sm py-space-xs rounded font-label-code text-label-code text-primary-container shadow-[0_0_10px_rgba(0,240,255,0.2)]">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-container mr-1.5 animate-pulse"></span>
          INFERENCIA ACTIVA
        </div>
      </div>
    </section>
  );
}

export default StatusBar;
