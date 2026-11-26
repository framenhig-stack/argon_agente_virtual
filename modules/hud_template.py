"""
Ruta: modules/hud_template.py
Descripción: Interfaz Holográfica 4K Argon 4 // Hermes Edition v4.5 (Con Live Thinking Steps
estilo ChatGPT, Visión Multimodal de Pantalla, Canvas 60 FPS y Barge-In Vocal).
"""

HUD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>ARGON 4 // HERMES TACTICAL OS v4.5</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-deep: #02060d;
    --panel-glass: rgba(6, 20, 39, 0.76);
    --cyan: #00f0ff;
    --cyan-glow: rgba(0, 240, 255, 0.35);
    --blue: #0077ff;
    --amber: #ffbe0b;
    --crimson: #ff0055;
    --emerald: #00f5d4;
    --text-main: #e2f9ff;
    --text-dim: #6488a4;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
  body {
    background: radial-gradient(circle at 50% 45%, #071930 0%, #02060d 75%);
    color: var(--text-main);
    font-family: 'Rajdhani', sans-serif;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  body::before {
    content: "";
    position: absolute; inset: 0;
    background-image: 
      linear-gradient(rgba(0, 240, 255, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 240, 255, 0.04) 1px, transparent 1px);
    background-size: 36px 36px;
    pointer-events: none;
    z-index: 0;
  }
  header {
    z-index: 2;
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 24px;
    margin: 12px 18px 4px;
    background: var(--panel-glass);
    border: 1px solid rgba(0, 240, 255, 0.35);
    box-shadow: 0 0 25px rgba(0, 240, 255, 0.12), inset 0 0 15px rgba(0, 240, 255, 0.06);
    clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 18px 100%, 0 calc(100% - 18px));
    backdrop-filter: blur(14px);
  }
  .brand {
    display: flex; align-items: center; gap: 14px;
    font-family: 'Orbitron', sans-serif;
    font-size: 1.2rem; font-weight: 900;
    letter-spacing: 3px; color: var(--cyan);
    text-shadow: 0 0 12px var(--cyan-glow);
  }
  .header-controls { display: flex; align-items: center; gap: 10px; }
  select, .hud-btn {
    background: rgba(3, 12, 26, 0.9);
    color: var(--cyan);
    border: 1px solid var(--cyan);
    padding: 7px 12px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem;
    cursor: pointer;
    transition: all 0.2s ease;
    clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  }
  .hud-btn:hover, select:hover {
    background: var(--cyan); color: #02060d;
    box-shadow: 0 0 16px var(--cyan);
  }
  .badge {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem; padding: 6px 12px;
    border: 1px solid var(--emerald); color: var(--emerald);
    background: rgba(0, 245, 212, 0.08);
  }
  main {
    z-index: 2;
    flex: 1;
    display: grid;
    grid-template-columns: 360px 1fr 460px;
    gap: 16px;
    padding: 10px 18px 18px;
    min-height: 0;
  }
  .panel {
    background: var(--panel-glass);
    border: 1px solid rgba(0, 240, 255, 0.28);
    box-shadow: 0 0 24px rgba(0, 0, 0, 0.6), inset 0 0 20px rgba(0, 240, 255, 0.04);
    backdrop-filter: blur(16px);
    clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px));
    padding: 16px;
    display: flex; flex-direction: column; gap: 10px;
    min-height: 0;
  }
  .panel-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.82rem; letter-spacing: 2px;
    color: var(--cyan);
    border-bottom: 1px solid rgba(0, 240, 255, 0.25);
    padding-bottom: 5px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .gauges { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; padding: 4px 0; }
  .gauge-card {
    text-align: center; background: rgba(2, 8, 18, 0.6);
    border: 1px solid rgba(0, 240, 255, 0.15); padding: 6px 4px;
  }
  .gauge-val {
    font-family: 'Orbitron', sans-serif; font-size: 0.95rem;
    color: var(--text-main);
  }
  .gauge-lbl { font-family: 'Share Tech Mono', monospace; font-size: 0.68rem; color: var(--text-dim); }
  .scroll-list {
    flex: 1; overflow-y: auto;
    background: rgba(2, 8, 18, 0.65);
    border: 1px solid rgba(0, 240, 255, 0.14);
    padding: 10px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.83rem;
    user-select: text;
  }
  .mem-item {
    padding: 6px 8px; margin-bottom: 6px;
    border-left: 2px solid var(--amber);
    background: rgba(255, 190, 11, 0.06);
  }
  .cal-item {
    padding: 6px 8px; margin-bottom: 6px;
    border-left: 2px solid var(--emerald);
    background: rgba(0, 245, 212, 0.06);
  }
  .quick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
  .center-stage {
    position: relative;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }
  #reactorCanvas {
    cursor: pointer;
    filter: drop-shadow(0 0 18px rgba(0, 240, 255, 0.25));
  }
  .state-banner {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.0rem; letter-spacing: 3px;
    color: var(--cyan);
    text-shadow: 0 0 10px var(--cyan);
    margin-top: 4px;
  }
  .sub-banner {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem; color: var(--amber);
    margin-top: 4px;
    text-align: center;
    max-width: 90%;
  }
  .voice-controls { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; justify-content: center; }
  .btn-primary {
    background: rgba(0, 240, 255, 0.16);
    border: 1px solid var(--cyan);
    color: var(--text-main);
    font-family: 'Orbitron', sans-serif;
    font-size: 0.78rem; letter-spacing: 1.5px;
    padding: 10px 16px; cursor: pointer;
    box-shadow: 0 0 18px rgba(0, 240, 255, 0.2);
    clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
    transition: 0.2s;
  }
  .btn-primary:hover, .btn-primary.active {
    background: var(--cyan); color: #02060d;
    box-shadow: 0 0 28px var(--cyan);
  }
  #chatStream {
    flex: 1; overflow-y: auto;
    padding: 12px;
    background: rgba(2, 8, 18, 0.72);
    border: 1px solid rgba(0, 240, 255, 0.15);
    display: flex; flex-direction: column; gap: 12px;
    user-select: text;
  }
  .msg {
    padding: 10px 14px;
    line-height: 1.45;
    font-size: 0.96rem;
    clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);
  }
  .msg.agent {
    border-left: 3px solid var(--cyan);
    background: rgba(0, 240, 255, 0.08);
    color: var(--text-main);
  }
  .msg.user {
    border-right: 3px solid var(--amber);
    background: rgba(255, 190, 11, 0.08);
    color: #fff3cd;
    align-self: flex-end;
    max-width: 90%;
  }
  .msg-sender {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.68rem; letter-spacing: 1.5px;
    margin-bottom: 4px; opacity: 0.8;
  }
  /* TARJETA DE ACTIVIDAD EN VIVO ESTILO CHATGPT */
  #liveTraceBox {
    display: none;
    background: rgba(0, 240, 255, 0.06);
    border: 1px solid rgba(0, 240, 255, 0.35);
    border-left: 3px solid var(--emerald);
    padding: 10px 12px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
  }
  .trace-header {
    display: flex; align-items: center; justify-content: space-between;
    color: var(--emerald);
    font-weight: bold;
    margin-bottom: 6px;
    font-size: 0.78rem;
    letter-spacing: 1px;
  }
  .trace-step {
    display: flex; align-items: center; justify-content: space-between;
    padding: 3px 0;
    color: var(--text-main);
  }
  .trace-step.done { color: var(--text-dim); }
  .trace-step.running { color: var(--cyan); font-weight: bold; }
  .spinner {
    display: inline-block;
    width: 10px; height: 10px;
    border: 2px solid var(--cyan);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
    margin-right: 7px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .input-row { display: flex; gap: 8px; }
  #cmdInput {
    flex: 1;
    background: rgba(2, 10, 22, 0.95);
    border: 1px solid var(--cyan);
    color: var(--text-main);
    padding: 12px 14px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.02rem;
    outline: none;
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <span>❖ ARGON 4 // HERMES</span>
    <span style="font-size:0.72rem; color:var(--text-dim);">GEMINI MULTIMODAL SOTA v4.5</span>
  </div>
  <div class="header-controls">
    <select id="voiceSelect" onchange="changeVoice()">
      <option value="es-ES-AlvaroNeural|-14Hz|+6%">VOZ: J.A.R.V.I.S. PROFUNDO (ÁLVARO -14Hz)</option>
      <option value="es-ES-AlvaroNeural|-18Hz|+4%">VOZ: J.A.R.V.I.S. ULTRA GRAVE (ÁLVARO -18Hz)</option>
      <option value="es-MX-JorgeNeural|-14Hz|+6%">VOZ: TÁCTICO GRAVE (JORGE -14Hz)</option>
      <option value="es-PE-AlexNeural|-12Hz|+6%">VOZ: EJECUTIVO GRAVE (ALEX -12Hz)</option>
      <option value="es-PE-CamilaNeural|-4Hz|+8%">VOZ: F.R.I.D.A.Y. (CAMILA NEURAL)</option>
    </select>
    <button class="hud-btn" onclick="setupShortcut(false)">⚡ ACCESO DIRECTO</button>
    <button class="hud-btn" onclick="setupShortcut(true)">🚀 AUTO-ARRANQUE</button>
    <div id="ollamaBadge" class="badge">● GEMINI SOTA: ACTIVO</div>
  </div>
</header>

<main>
  <!-- COLUMNA IZQUIERDA -->
  <section class="panel">
    <div class="panel-title"><span>01 // TELEMETRÍA Y DISPATCHER</span><span>/telemetry</span></div>
    <div class="gauges">
      <div class="gauge-card">
        <div id="cpuVal" class="gauge-val">--%</div>
        <div class="gauge-lbl">CPU</div>
      </div>
      <div class="gauge-card">
        <div id="ramVal" class="gauge-val">--%</div>
        <div class="gauge-lbl">RAM</div>
      </div>
      <div class="gauge-card">
        <div id="batVal" class="gauge-val">--%</div>
        <div class="gauge-lbl">BAT</div>
      </div>
      <div class="gauge-card">
        <div id="toolVal" class="gauge-val" style="color:var(--amber); font-size:0.78rem;">NONE</div>
        <div class="gauge-lbl">TOOL</div>
      </div>
    </div>

    <div class="panel-title">
      <span>02 // MEMORIA COGNITIVA (SQLITE)</span>
      <span style="font-size:0.68rem; color:var(--amber);">AUTO-LEARN</span>
    </div>
    <div id="memoryList" class="scroll-list"></div>
    <div style="display:flex; gap:6px;">
      <input id="memInput" type="text" placeholder="Guardar recuerdo permanente..." style="flex:1; background:#030b17; border:1px solid #1b4965; color:#fff; padding:6px 10px; font-family:'Rajdhani';">
      <button class="hud-btn" onclick="addMemoryManual()">+ MEMORIA</button>
    </div>

    <div class="panel-title">
      <span>03 // AGENDA LOCAL + NOTION API</span>
      <span id="notionBadge" style="font-size:0.68rem; color:var(--emerald);">SYNC</span>
    </div>
    <div id="calendarList" class="scroll-list" style="max-height:105px;"></div>

    <div class="quick-grid">
      <button class="hud-btn" onclick="sendCmd('Mira mi pantalla y dime qué estoy haciendo o si ves algún problema')">👁️ VER MI PANTALLA</button>
      <button class="hud-btn" onclick="sendCmd('Analiza mi portapapeles')">📋 PORTAPAPELES</button>
      <button class="hud-btn" onclick="sendCmd('Busca en internet noticias tecnológicas de hoy')">🌐 WEB EN VIVO</button>
      <button class="hud-btn" onclick="sendCmd('Qué pendientes tengo hoy en mi agenda y Notion')">📅 AGENDA / NOTION</button>
    </div>
  </section>

  <!-- COLUMNA CENTRAL: REACTOR HOLOGRÁFICO -->
  <section class="center-stage">
    <canvas id="reactorCanvas" width="420" height="420" onclick="triggerVoiceListen()"></canvas>
    <div id="stateBanner" class="state-banner">● NÚCLEO EN ESPERA (CLIC PARA HABLAR)</div>
    <div id="lastActionBanner" class="sub-banner">VAD ANTI-CORTES (1.75s PAUSA) + TRAZABILIDAD EN VIVO ACTIVOS</div>
    <div class="voice-controls">
      <button class="btn-primary" onclick="triggerVoiceListen()">🎙️ HABLAR AHORA</button>
      <button class="btn-primary" onclick="stopVoice()" style="border-color:var(--crimson);">⏹️ SILENCIAR</button>
      <button id="btnHandsfree" class="btn-primary" onclick="toggleHandsfree()">🔄 ESCUCHA CONTINUA: OFF</button>
    </div>
  </section>

  <!-- COLUMNA DERECHA: CONSOLA NEURONAL + TRAZABILIDAD ESTILO CHATGPT -->
  <section class="panel">
    <div class="panel-title">
      <span>04 // CONSOLA NEURONAL Y TRAZABILIDAD</span>
      <span id="modelLabel" style="color:var(--emerald);">GEMINI</span>
    </div>
    <div id="chatStream"></div>

    <!-- WIDGET DE PROCESAMIENTO EN VIVO ESTILO CHATGPT -->
    <div id="liveTraceBox">
      <div class="trace-header">
        <span id="traceTitle"><span class="spinner"></span>EJECUTANDO TAREA EN TIEMPO REAL...</span>
        <span id="traceTimer">0.0s</span>
      </div>
      <div id="traceStepsList"></div>
    </div>

    <div class="input-row">
      <input id="cmdInput" type="text" placeholder="Escribe o habla (ej. 'Mira mi pantalla', 'Busca X y anota en Notion...')..." onkeydown="if(event.key==='Enter') sendFromInput()">
      <button class="btn-primary" onclick="sendFromInput()">TRANSMITIR ➤</button>
    </div>
  </section>
</main>

<script>
  let agentState = "IDLE";
  let lastLogCount = 0;
  let lastMemSignature = "";
  let lastCalSignature = "";
  let handsfreeActive = false;

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const canvas = document.getElementById("reactorCanvas");
  const ctx = canvas.getContext("2d");
  let t = 0;

  function drawReactor() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    let mainColor = "#00f0ff";
    let speed = 0.015;
    if (agentState === "LISTENING") { mainColor = "#ffbe0b"; speed = 0.035; }
    else if (agentState === "THINKING" || agentState === "TOOL_EXEC") { mainColor = "#ff0055"; speed = 0.055; }
    else if (agentState === "SPEAKING") { mainColor = "#00f5d4"; speed = 0.04; }

    t += speed;

    ctx.save();
    ctx.shadowBlur = 18;
    ctx.shadowColor = mainColor;

    ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 186, 0, Math.PI * 2);
    ctx.stroke();

    for (let i = 0; i < 60; i++) {
      const ang = (i * 6 * Math.PI) / 180 + t * 0.2;
      const r1 = i % 5 === 0 ? 174 : 180;
      ctx.strokeStyle = i % 5 === 0 ? mainColor : "rgba(0,240,255,0.3)";
      ctx.beginPath();
      ctx.moveTo(cx + r1 * Math.cos(ang), cy + r1 * Math.sin(ang));
      ctx.lineTo(cx + 186 * Math.cos(ang), cy + 186 * Math.sin(ang));
      ctx.stroke();
    }

    ctx.strokeStyle = mainColor;
    ctx.lineWidth = 5;
    for (let i = 0; i < 4; i++) {
      const start = t + (i * Math.PI) / 2;
      ctx.beginPath();
      ctx.arc(cx, cy, 154, start, start + 0.9);
      ctx.stroke();
    }

    ctx.strokeStyle = "#0077ff";
    ctx.lineWidth = 3;
    for (let i = 0; i < 3; i++) {
      const start = -t * 1.4 + (i * Math.PI * 2) / 3;
      ctx.beginPath();
      ctx.arc(cx, cy, 124, start, start + 1.3);
      ctx.stroke();
    }

    const bars = 48;
    for (let i = 0; i < bars; i++) {
      const ang = (i * Math.PI * 2) / bars - t * 0.5;
      let amp = 8 + Math.sin(t * 4 + i * 0.5) * 5;
      if (agentState === "SPEAKING") {
        amp = 12 + Math.abs(Math.sin(t * 10 + i * 1.1)) * 35;
      } else if (agentState === "LISTENING") {
        amp = 10 + Math.abs(Math.cos(t * 8 + i)) * 22;
      }
      const rStart = 76;
      const rEnd = rStart + amp;
      ctx.strokeStyle = mainColor;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(cx + rStart * Math.cos(ang), cy + rStart * Math.sin(ang));
      ctx.lineTo(cx + rEnd * Math.cos(ang), cy + rEnd * Math.sin(ang));
      ctx.stroke();
    }

    const pulse = agentState === "SPEAKING" ? Math.sin(t * 8) * 8 : Math.sin(t * 2) * 3;
    const coreRadius = 54 + pulse;
    const grad = ctx.createRadialGradient(cx, cy, 8, cx, cy, coreRadius);
    grad.addColorStop(0, "rgba(0, 240, 255, 0.45)");
    grad.addColorStop(1, "rgba(3, 12, 28, 0.92)");

    ctx.fillStyle = grad;
    ctx.strokeStyle = mainColor;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#e2f9ff";
    ctx.font = "900 15px 'Orbitron'";
    ctx.textAlign = "center";
    ctx.fillText("ARGON 4", cx, cy - 3);
    ctx.fillStyle = mainColor;
    ctx.font = "11px 'Share Tech Mono'";
    ctx.fillText(agentState, cx, cy + 15);

    ctx.restore();
    requestAnimationFrame(drawReactor);
  }
  requestAnimationFrame(drawReactor);

  async function pollState() {
    try {
      const res = await fetch("/api/state");
      const data = await res.json();

      agentState = data.state;
      document.getElementById("stateBanner").innerText = "● ESTADO DEL NÚCLEO: " + data.state;
      document.getElementById("lastActionBanner").innerText = "ACCIÓN: " + data.last_action;
      document.getElementById("cpuVal").innerText = data.telemetry.cpu_percent + "%";
      document.getElementById("ramVal").innerText = data.telemetry.ram_percent + "%";
      document.getElementById("batVal").innerText = data.telemetry.battery_percent + "%";
      document.getElementById("toolVal").innerText = data.active_tool;
      document.getElementById("modelLabel").innerText = data.model;
      document.getElementById("notionBadge").innerText = data.notion_enabled ? "NOTION ONLINE" : "LOCAL JSON";

      // Actualizar Trazabilidad en Vivo estilo ChatGPT
      const traceBox = document.getElementById("liveTraceBox");
      const traceList = document.getElementById("traceStepsList");
      const traceTimer = document.getElementById("traceTimer");
      const traceTitle = document.getElementById("traceTitle");

      if (data.live_steps && data.live_steps.length > 0 && (data.is_processing || data.state !== "IDLE")) {
        traceBox.style.display = "block";
        const lastStep = data.live_steps[data.live_steps.length - 1];
        traceTimer.innerText = lastStep.elapsed || "";
        traceTitle.innerHTML = data.is_processing
          ? `<span class="spinner"></span>EJECUTANDO PIPELINE AGÉNTICO...`
          : `✓ PIPELINE COMPLETADO`;

        traceList.innerHTML = data.live_steps.map(s => {
          const icon = s.status === "done" ? "✓" : `<span class="spinner"></span>`;
          return `<div class="trace-step ${s.status}">
            <span>${icon} ${escapeHtml(s.label)}</span>
            <span style="opacity:0.65;">${escapeHtml(s.elapsed)}</span>
          </div>`;
        }).join("");
      } else {
        traceBox.style.display = "none";
      }

      // Actualizar memorias solo si cambiaron (preserva scroll)
      const memSig = JSON.stringify(data.memories);
      if (memSig !== lastMemSignature) {
        lastMemSignature = memSig;
        const memBox = document.getElementById("memoryList");
        memBox.innerHTML = data.memories.length === 0
          ? "<div style='color:var(--text-dim)'>Sin memorias registradas aún.</div>"
          : data.memories.map(m => `<div class="mem-item"><strong>[${escapeHtml(m.category)}]</strong> ${escapeHtml(m.note)}</div>`).join("");
      }

      // Actualizar calendario solo si cambió (preserva scroll)
      const calSig = JSON.stringify(data.calendar);
      if (calSig !== lastCalSignature) {
        lastCalSignature = calSig;
        const calBox = document.getElementById("calendarList");
        calBox.innerHTML = data.calendar.length === 0
          ? "<div style='color:var(--text-dim)'>Sin pendientes activos.</div>"
          : data.calendar.map(c => `<div class="cal-item">#${escapeHtml(c.id)} - ${escapeHtml(c.title)}</div>`).join("");
      }

      if (data.logs.length !== lastLogCount) {
        lastLogCount = data.logs.length;
        const stream = document.getElementById("chatStream");
        stream.innerHTML = data.logs.map(item => `
          <div class="msg ${escapeHtml(item.tag)}">
            <div class="msg-sender">${escapeHtml(item.sender)}</div>
            <div>${escapeHtml(item.text)}</div>
          </div>
        `).join("");
        stream.scrollTop = stream.scrollHeight;
      }
    } catch (e) {}
  }
  setInterval(pollState, 450);
  pollState();

  async function sendCmd(text) {
    if (!text.trim()) return;
    await fetch("/api/command", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text})
    });
  }

  function sendFromInput() {
    const inp = document.getElementById("cmdInput");
    const val = inp.value.trim();
    if (!val) return;
    inp.value = "";
    sendCmd(val);
  }

  async function triggerVoiceListen() {
    await fetch("/api/listen", {method: "POST"});
  }

  async function stopVoice() {
    await fetch("/api/stop_voice", {method: "POST"});
  }

  async function toggleHandsfree() {
    const res = await fetch("/api/handsfree", {method: "POST"});
    const data = await res.json();
    handsfreeActive = data.handsfree;
    const btn = document.getElementById("btnHandsfree");
    btn.innerText = handsfreeActive
      ? "🔄 ESCUCHA CONTINUA: ON"
      : "🔄 ESCUCHA CONTINUA: OFF";
    btn.classList.toggle("active", handsfreeActive);
  }

  async function changeVoice() {
    const raw = document.getElementById("voiceSelect").value;
    const [voice, pitch, rate] = raw.split("|");
    await fetch("/api/voice", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({voice, pitch, rate})
    });
  }

  async function addMemoryManual() {
    const inp = document.getElementById("memInput");
    if (!inp.value.trim()) return;
    const note = inp.value.trim();
    inp.value = "";
    sendCmd("Recuerda que " + note);
  }

  async function setupShortcut(startup) {
    const res = await fetch("/api/shortcut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({startup: startup})
    });
    const data = await res.json();
    alert(data.message || data.error);
  }
</script>
</body>
</html>
"""