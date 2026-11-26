"""
Ruta: modules/notion_bridge.py
Descripción: Conector bidireccional para Notion API y generador automático de la Skin Rainmeter.
"""
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
import requests
from config import Config, SKINS_DIR

logger = logging.getLogger("NotionBridge")


class NotionBridge:
    BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self) -> None:
        self.enabled = bool(Config.NOTION_API_KEY and Config.NOTION_DATABASE_ID)
        self.headers = {
            "Authorization": f"Bearer {Config.NOTION_API_KEY}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self._cached_tasks: List[Dict[str, str]] = []
        self._last_fetch_ts: float = 0.0
        self._session = requests.Session()

    def fetch_tasks(self, limit: int = 5) -> List[Dict[str, str]]:
        """Obtiene tareas desde Notion si está configurado en .env."""
        if not self.enabled:
            return []
        if time.time() - self._last_fetch_ts < 60:
            return self._cached_tasks

        url = f"{self.BASE_URL}/databases/{Config.NOTION_DATABASE_ID}/query"
        try:
            resp = self._session.post(url, headers=self.headers, json={"page_size": limit}, timeout=8)
            if resp.status_code != 200:
                logger.warning(f"Notion API respondió {resp.status_code}: {resp.text[:120]}")
                return []
            results = resp.json().get("results", [])
            tasks: List[Dict[str, str]] = []
            for idx, page in enumerate(results, start=1):
                props = page.get("properties", {})
                title = self._extract_title(props)
                tasks.append({
                    "id": f"N{idx}",
                    "title": f"[Notion] {title}",
                    "datetime": self._extract_date(props),
                    "status": "pendiente",
                })
            self._cached_tasks = tasks
            self._last_fetch_ts = time.time()
            return self._cached_tasks
        except Exception as exc:
            logger.error(f"Error consultando Notion: {exc}")
            return []

    def create_task(self, title: str, iso_date: str = "") -> Dict[str, Any]:
        """Crea una página/tarea directamente en la base de datos de Notion."""
        if not self.enabled:
            return {"ok": False, "error": "Notion no configurado en .env (usando agenda local)."}

        date_val = iso_date or datetime.now().strftime("%Y-%m-%d")
        url = f"{self.BASE_URL}/pages"
        payload = {
            "parent": {"database_id": Config.NOTION_DATABASE_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": title.strip()}}]},
            },
        }
        try:
            resp = self._session.post(url, headers=self.headers, json=payload, timeout=8)
            if resp.status_code in (200, 201):
                self._last_fetch_ts = 0.0
                data = resp.json()
                logger.info(f"Tarea sincronizada en Notion: {title}")
                return {"ok": True, "url": data.get("url", ""), "date": date_val}
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _extract_title(props: Dict[str, Any]) -> str:
        for prop in props.values():
            if prop.get("type") == "title":
                arr = prop.get("title", [])
                return "".join(t.get("plain_text", "") for t in arr) or "Sin título"
        return "Sin título"

    @staticmethod
    def _extract_date(props: Dict[str, Any]) -> str:
        for prop in props.values():
            if prop.get("type") == "date" and prop.get("date"):
                return prop["date"].get("start", "Hoy")
        return "Hoy"

    @staticmethod
    def export_rainmeter_skin() -> str:
        """Genera el archivo skins/HUD_Agent.ini listo para cargar en Rainmeter."""
        skin_path = SKINS_DIR / "HUD_Agent.ini"
        port = Config.HUD_PORT
        ini_content = f"""[Rainmeter]
Update=1000
AccurateText=1
DynamicWindowSize=1
BackgroundMode=2
SolidColor=4,12,24,220

[Variables]
FontTitle=Orbitron
FontMono=Consolas
Cyan=0,240,255,255
Amber=255,190,11,255
White=226,249,255,255
Dim=100,136,164,255

[MeasureTelemetryJSON]
Measure=WebParser
URL=http://127.0.0.1:{port}/telemetry
RegExp=(?siU)"status"\\s*:\\s*"(.*)".*"tool"\\s*:\\s*"(.*)".*"last_action"\\s*:\\s*"(.*)".*"updated_at"\\s*:\\s*"(.*)".*"cpu"\\s*:\\s*([0-9.]+).*"ram"\\s*:\\s*([0-9.]+)
UpdateRate=1

[MeasureStatus]
Measure=WebParser
URL=[MeasureTelemetryJSON]
StringIndex=1
Substitute="":"OFFLINE"

[MeasureTool]
Measure=WebParser
URL=[MeasureTelemetryJSON]
StringIndex=2
Substitute="":"NONE"

[MeasureAction]
Measure=WebParser
URL=[MeasureTelemetryJSON]
StringIndex=3
Substitute="":"Sistema Argon 4 en espera..."

[MeasureTime]
Measure=WebParser
URL=[MeasureTelemetryJSON]
StringIndex=4

[MeasureCPU]
Measure=WebParser
URL=[MeasureTelemetryJSON]
StringIndex=5

[MeasureRAM]
Measure=WebParser
URL=[MeasureTelemetryJSON]
StringIndex=6

[MeterBorderTop]
Meter=Shape
Shape=Rectangle 0,0,430,3,0 | Fill Color #Cyan# | StrokeWidth 0

[MeterHeader]
Meter=String
X=16
Y=12
FontFace=#FontTitle#
FontSize=11
FontColor=#Cyan#
FontWeight=800
Text=❖ ARGON 4 // HERMES TELEMETRY HUD
AntiAlias=1

[MeterStatusBadge]
Meter=String
MeasureName=MeasureStatus
X=414
Y=12
StringAlign=Right
FontFace=#FontMono#
FontSize=10
FontColor=#Amber#
Text=[%1]
AntiAlias=1

[MeterMetrics]
Meter=String
MeasureName=MeasureCPU
MeasureName2=MeasureRAM
MeasureName3=MeasureTool
X=16
Y=42
FontFace=#FontMono#
FontSize=10
FontColor=#White#
Text=CPU: %1%   |   RAM: %2%   |   TOOL: %3
AntiAlias=1

[MeterDivider]
Meter=Shape
Shape=Line 16,68,414,68 | StrokeWidth 1 | Stroke Color 0,240,255,70

[MeterLastActionLabel]
Meter=String
MeasureName=MeasureTime
X=16
Y=76
FontFace=#FontMono#
FontSize=8
FontColor=#Dim#
Text=ÚLTIMA ACCIÓN (%1):
AntiAlias=1

[MeterLastActionBody]
Meter=String
MeasureName=MeasureAction
X=16
Y=94
W=398
H=45
ClipString=2
FontFace=#FontMono#
FontSize=9
FontColor=#White#
Text=%1
AntiAlias=1
"""
        skin_path.write_text(ini_content, encoding="utf-8")
        return str(skin_path)