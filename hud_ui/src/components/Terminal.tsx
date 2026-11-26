import { useState, useRef, useEffect } from 'react';

interface MensajeTerminal {
  id: number;
  tipo: 'usuario' | 'hermes';
  texto: string;
  timestamp: string;
}

function generarTimestamp() {
  const now = new Date();
  const timeStr =
    now.toTimeString().split(' ')[0] +
    '.' +
    String(now.getMilliseconds()).padStart(3, '0');
  return timeStr;
}

function Terminal() {
  const [historial, setHistorial] = useState<MensajeTerminal[]>([
    {
      id: 0,
      tipo: 'hermes',
      texto: '>> [HERMES_CORE]: Nodo local inicializado. Esperando instrucciones de ejecución.',
      timestamp: generarTimestamp(),
    },
  ]);
  const [input, setInput] = useState('');
  const [procesando, setProcesando] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [historial]);

  const enviarComando = async () => {
    const texto = input.trim();
    if (!texto || procesando) return;

    const mensajeUsuario: MensajeTerminal = {
      id: nextId.current++,
      tipo: 'usuario',
      texto,
      timestamp: generarTimestamp(),
    };

    setHistorial((prev) => [...prev, mensajeUsuario]);
    setInput('');
    setProcesando(true);

    try {
    // 1. React envía el comando al puerto 8000 (tu backend Python)
    const respuesta = await fetch("http://127.0.0.1:8000/api/comando", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt: texto }) // Enviamos el texto de la línea 40
    });

    const datos = await respuesta.json();

    // 2. Armamos la respuesta de Hermes usando tu estructura original
    const respuestaHermes: MensajeTerminal = {
      id: nextId.current++,
      tipo: 'hermes',
      texto: `>> [HERMES_CORE]: ${datos.respuesta}`,
      timestamp: generarTimestamp(),
    };

    setHistorial((prev) => [...prev, respuestaHermes]);

  } catch (error) {
    // 3. Error táctico si el agente Python está apagado
    const errorHermes: MensajeTerminal = {
      id: nextId.current++,
      tipo: 'hermes',
      texto: ">> [ERROR_SYS]: Núcleo local de Python desconectado. Puerto 8000 inactivo.",
      timestamp: generarTimestamp(),
    };
    setHistorial((prev) => [...prev, errorHermes]);
  } finally {
    setProcesando(false);
  }
  };

  const limpiarBuffer = () => {
    setHistorial([
      {
        id: nextId.current++,
        tipo: 'hermes',
        texto: '>> [HERMES_CORE]: Buffer de terminal restablecido. Conexión de nodo local intacta y lista para instrucciones.',
        timestamp: generarTimestamp(),
      },
    ]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviarComando();
    }
  };

  return (
    <main className="xl:col-span-8 flex flex-col bg-surface-container-low/85 backdrop-blur-xl rounded-xl shadow-2xl p-space-md lg:p-space-lg flex-1 min-w-0">
      {/* Terminal Top Bar */}
      <div className="flex items-center justify-between pb-space-sm mb-space-md bg-surface-container-high/40 p-space-sm rounded-lg">
        <div className="flex items-center gap-space-sm">
          <span className="material-symbols-outlined text-primary-container text-[18px]">terminal</span>
          <span className="font-label-code text-label-code text-primary-container uppercase tracking-wider">CANAL://HERMES-STREAM-01</span>
          <span className="bg-surface-container px-space-xs py-0.5 rounded font-label-code text-label-code text-outline">SHM-BUFF-SYNC</span>
        </div>
        <div className="flex items-center gap-space-sm">
          <button
            className="font-label-code text-label-code text-outline hover:text-primary-container px-space-xs py-0.5 rounded transition-colors flex items-center gap-1"
            type="button"
            onClick={limpiarBuffer}
          >
            <span className="material-symbols-outlined text-[14px]">refresh</span> RESET_BUFF
          </button>
          <div className="flex gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-surface-container-highest"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-secondary/50"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-primary-container shadow-[0_0_6px_rgba(0,240,255,0.6)]"></span>
          </div>
        </div>
      </div>

      {/* Terminal Feed */}
      <div
        ref={feedRef}
        className="flex flex-col gap-space-lg overflow-y-auto max-h-[640px] pr-space-xs scroll-smooth"
      >
        {historial.map((msg) =>
          msg.tipo === 'usuario' ? (
            <div key={msg.id} className="flex justify-end items-start gap-space-sm pl-8">
              <div className="flex flex-col items-end max-w-2xl">
                <div className="flex items-center gap-space-xs font-label-code text-label-code text-outline mb-1">
                  <span>CANAL 0x4F // PRIORIDAD ALTA</span>
                  <span className="text-outline-variant">•</span>
                  <span>{msg.timestamp}</span>
                  <span className="text-primary-container font-bold ml-1">[USR_OP]</span>
                </div>
                <div className="bg-surface-container-high/90 text-on-surface p-space-md rounded-xl rounded-tr-none shadow-md">
                  <p className="font-body-md text-body-md leading-relaxed">{msg.texto}</p>
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-surface-container-highest flex items-center justify-center text-primary-container shrink-0 mt-4 shadow-sm">
                <span className="material-symbols-outlined text-[18px]">account_circle</span>
              </div>
            </div>
          ) : (
            <div key={msg.id} className="flex flex-col items-start w-full">
              <div className="flex items-center gap-space-xs font-telemetry-sm text-telemetry-sm text-secondary-container mb-2">
                <span className="text-primary-container font-bold">[HERMES_CORE]</span>
                <span className="text-on-surface-variant font-label-code text-label-code">DISPATCH_KERNEL</span>
                <span className="text-outline text-label-code">{msg.timestamp}</span>
              </div>
              <div className="w-full space-y-2 font-telemetry-md text-telemetry-md text-primary-container drop-shadow-[0_0_6px_rgba(0,240,255,0.3)]">
                <p className="leading-relaxed text-secondary">{msg.texto}</p>
              </div>
            </div>
          )
        )}

        {/* Indicador de procesamiento */}
        {procesando && (
          <div className="flex flex-col items-start w-full">
            <div className="flex items-center gap-space-xs font-telemetry-sm text-telemetry-sm text-secondary-container mb-2">
              <span className="text-primary-container font-bold">[HERMES_CORE]</span>
              <span className="text-on-surface-variant font-label-code text-label-code">PROCESSING...</span>
            </div>
            <div className="flex items-center gap-2 text-secondary font-telemetry-md text-telemetry-md">
              <span className="inline-block w-2.5 h-4 bg-primary-container animate-pulse shadow-[0_0_8px_rgba(0,240,255,0.8)] align-middle"></span>
              <span>Procesando comando...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Zone */}
      <div className="mt-space-md pt-space-md bg-surface-container-low">
        {/* Parameter Switchers */}
        <div className="flex flex-wrap items-center justify-between gap-space-xs mb-space-sm font-label-code text-label-code">
          <div className="flex flex-wrap items-center gap-space-xs">
            <button className="bg-surface-container-highest hover:bg-surface-container-high text-primary-container px-space-sm py-1 rounded transition-colors flex items-center gap-1 shadow-sm" type="button">
              <span className="material-symbols-outlined text-[14px]">bolt</span>
              <span>[MODO: INFERENCIA RÁPIDA]</span>
            </button>
            <button className="bg-surface-container px-space-sm py-1 rounded text-on-surface-variant hover:text-on-surface transition-colors flex items-center gap-1" type="button">
              <span className="material-symbols-outlined text-[14px]">device_thermostat</span>
              <span>[TEMPERATURA: 0.3]</span>
            </button>
            <button className="bg-surface-container px-space-sm py-1 rounded text-secondary hover:text-primary-container transition-colors flex items-center gap-1" type="button">
              <span className="material-symbols-outlined text-[14px]">tune</span>
              <span>[PRECISIÓN: FP16]</span>
            </button>
          </div>
          <div className="hidden sm:flex items-center gap-space-xs text-outline">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>SHM BUFFER: LISTO</span>
          </div>
        </div>

        {/* Command Entry Bar */}
        <div className="relative bg-surface-container-lowest rounded-xl p-space-sm shadow-[inset_0_2px_6px_rgba(0,0,0,0.8)] flex flex-col gap-space-xs">
          <div className="flex items-center justify-between text-outline px-space-xs font-label-code text-label-code">
            <span className="text-primary-container font-mono tracking-wider">SYS://INPUT &gt;</span>
            <div className="flex items-center gap-2">
              <span className="hidden md:inline">Enter para enviar</span>
              <span className="text-on-surface-variant">| {input.length} / 4096 TK</span>
            </div>
          </div>
          <div className="flex items-end gap-space-sm">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ingresar comando para Argon 4 Hermes..."
              rows={2}
              className="w-full bg-transparent border-0 text-on-surface font-body-md text-body-md placeholder:text-outline-variant focus:outline-none focus:ring-0 resize-none p-space-xs leading-relaxed"
            />
            <button
              onClick={enviarComando}
              disabled={!input.trim() || procesando}
              className="bg-primary-container hover:bg-primary-fixed text-on-primary-container font-label-code text-label-code font-bold py-space-sm px-space-md rounded-lg shadow-[0_0_16px_rgba(0,240,255,0.4)] hover:shadow-[0_0_24px_rgba(0,240,255,0.7)] active:scale-95 transition-all flex items-center gap-space-xs shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
              type="button"
            >
              <span className="hidden sm:inline tracking-wider">EJECUTAR</span>
              <span className="material-symbols-outlined text-[18px]">terminal</span>
              <span className="text-[10px] opacity-75 font-mono">↵</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

export default Terminal;
