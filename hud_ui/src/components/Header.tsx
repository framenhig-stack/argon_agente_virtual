function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 z-50 bg-surface-container-low/80 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.6)]">
      <div className="w-full h-full px-gutter flex items-center justify-between">
        <div className="flex items-center gap-space-lg">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded bg-surface-container-highest flex items-center justify-center text-primary-container shadow-[0_0_12px_rgba(0,240,255,0.35)]">
              <span className="material-symbols-outlined text-[20px]">deployed_code</span>
            </div>
            <div className="flex flex-col">
              <span className="font-headline-md text-headline-md tracking-wider text-primary font-bold uppercase drop-shadow-[0_0_8px_rgba(0,240,255,0.4)]">ARGON 4 HERMES</span>
              <span className="font-label-code text-label-code text-secondary tracking-widest">AUTONOMOUS INTEL NODE</span>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-space-sm bg-surface-container-high px-space-md py-space-xs rounded-full shadow-[inset_0_1px_3px_rgba(0,0,0,0.8)]">
            <div className="relative flex items-center justify-center w-2.5 h-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
            </div>
            <span className="font-label-code text-label-code text-on-surface-variant uppercase">Sistema en línea (Local)</span>
          </div>
          <div className="hidden lg:flex items-center bg-surface-container-highest px-space-sm py-space-xs rounded font-label-code text-label-code text-outline">
            <span className="text-primary-container mr-1">SYS://</span>v4.8.2-hermes
          </div>
        </div>
        <div className="flex items-center gap-space-md">
          <div className="flex items-center gap-space-xs">
            <button className="p-space-xs text-on-surface-variant hover:text-primary-container hover:bg-surface-container-high rounded transition-colors" title="Configuración de Red Neuronal" type="button">
              <span className="material-symbols-outlined text-[20px]">hub</span>
            </button>
            <button className="p-space-xs text-on-surface-variant hover:text-primary-container hover:bg-surface-container-high rounded transition-colors" title="Retroalimentación Acústica" type="button">
              <span className="material-symbols-outlined text-[20px]">volume_up</span>
            </button>
            <button className="p-space-xs text-on-surface-variant hover:text-primary-container hover:bg-surface-container-high rounded transition-colors" title="Parámetros de Enlace" type="button">
              <span className="material-symbols-outlined text-[20px]">tune</span>
            </button>
          </div>
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shadow-[0_0_10px_rgba(0,240,255,0.4)]">
            <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
