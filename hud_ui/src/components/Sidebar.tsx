function Sidebar() {
  return (
    <aside className="fixed left-0 top-16 bottom-0 w-64 bg-surface-container-low/70 backdrop-blur-xl z-40 hidden md:flex flex-col justify-between p-space-md shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
      <div className="space-y-space-md">
        <div className="px-space-sm py-space-xs font-label-code text-label-code text-outline uppercase tracking-wider flex items-center justify-between">
          <span>Subrutinas Activas</span>
          <span className="text-primary-container">[4/4]</span>
        </div>
        <nav className="space-y-space-xs">
          <a aria-current="page" className="flex items-center gap-space-sm px-space-md py-space-sm transition-all bg-primary-container text-on-primary-container font-bold rounded" href="#">
            <span className="material-symbols-outlined text-[18px]">terminal</span>
            <span>Terminal Hermes</span>
          </a>
          <a className="flex items-center gap-space-sm px-space-md py-space-sm font-label-code text-label-code text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all" href="#">
            <span className="material-symbols-outlined text-[18px]">monitoring</span>
            <span>Matriz Telemetría</span>
          </a>
          <a className="flex items-center gap-space-sm px-space-md py-space-sm font-label-code text-label-code text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all" href="#">
            <span className="material-symbols-outlined text-[18px]">memory</span>
            <span>Bancos de Memoria</span>
          </a>
          <a className="flex items-center gap-space-sm px-space-md py-space-sm font-label-code text-label-code text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface transition-all" href="#">
            <span className="material-symbols-outlined text-[18px]">security</span>
            <span>Protocolos Cipher</span>
          </a>
        </nav>
      </div>
      <div className="bg-surface-container p-space-sm rounded space-y-space-xs">
        <div className="flex justify-between items-center font-label-code text-label-code text-outline">
          <span>CARGA DE NÚCLEO</span>
          <span className="text-secondary">42.8%</span>
        </div>
        <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
          <div className="h-full bg-secondary rounded-full shadow-[0_0_8px_rgba(67,226,242,0.8)]" style={{ width: '42.8%' }}></div>
        </div>
        <div className="flex justify-between items-center font-label-code text-label-code text-outline">
          <span>LATENCIA LOCAL</span>
          <span className="text-primary-container">1.4 ms</span>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
