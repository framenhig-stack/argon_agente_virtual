"""
Ruta: modules/system_tasks.py
Descripción: Ejecución de tareas del sistema operativo, telemetría y protocolos externos.
"""
import logging
import platform
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import psutil
import pyautogui
from config import BASE_DIR

logger = logging.getLogger("SystemTasks")

# Prevención de bloqueos de PyAutoGUI al llevar el cursor a una esquina
pyautogui.FAILSAFE = True

# Inicializar lectura base de CPU para que las llamadas posteriores con interval=None sean instantáneas (0ms)
psutil.cpu_percent(interval=None)


class SystemTasks:
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """Obtiene métricas reales de CPU, RAM, disco y batería sin bloquear el hilo."""
        try:
            cpu_usage = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(BASE_DIR))
            battery = psutil.sensors_battery()

            status = {
                "cpu_percent": cpu_usage,
                "ram_percent": memory.percent,
                "ram_available_gb": round(memory.available / (1024 ** 3), 2),
                "disk_free_gb": round(disk.free / (1024 ** 3), 2),
                "battery_percent": int(battery.percent) if battery else 100,
                "power_plugged": battery.power_plugged if battery else True,
            }
            logger.debug(f"Telemetría recolectada: {status}")
            return {"ok": True, "data": status}
        except Exception as exc:
            logger.error(f"Error al leer telemetría del sistema: {exc}")
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def take_screenshot() -> Dict[str, Any]:
        """Guarda una captura de pantalla en la carpeta local logs/."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = BASE_DIR / "logs" / f"screenshot_{timestamp}.png"
            image = pyautogui.screenshot()
            image.save(filepath)
            logger.info(f"Captura de pantalla almacenada en: {filepath}")
            return {"ok": True, "filepath": str(filepath)}
        except Exception as exc:
            logger.error(f"Fallo al capturar pantalla: {exc}")
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def open_application(app_name: str) -> Dict[str, Any]:
        """Abre aplicaciones estándar del sistema según la plataforma actual."""
        system_os = platform.system().lower()
        app_key = app_name.lower().strip()

        # Mapa seguro de binarios comunes
        app_map = {
            "windows": {
                "calculadora": ["calc.exe"],
                "bloc de notas": ["notepad.exe"],
                "explorador": ["explorer.exe"],
                "terminal": ["cmd.exe", "/c", "start", "cmd.exe"],
            },
            "linux": {
                "calculadora": ["gnome-calculator"],
                "bloc de notas": ["gedit"],
                "explorador": ["xdg-open", str(Path.home())],
                "terminal": ["x-terminal-emulator"],
            },
            "darwin": {
                "calculadora": ["open", "-a", "Calculator"],
                "bloc de notas": ["open", "-a", "TextEdit"],
                "explorador": ["open", str(Path.home())],
                "terminal": ["open", "-a", "Terminal"],
            },
        }

        commands = app_map.get(system_os, {}).get(app_key)
        if not commands:
            return {
                "ok": False,
                "error": f"Aplicación '{app_name}' no registrada en la lista blanca para {system_os}."
            }

        try:
            subprocess.Popen(
                commands,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=(system_os == "windows" and app_key == "terminal")
            )
            logger.info(f"Aplicación ejecutada: {app_name}")
            return {"ok": True, "app": app_name}
        except FileNotFoundError:
            return {"ok": False, "error": f"No se encontró el binario para '{app_name}'."}
        except Exception as exc:
            logger.error(f"Error lanzando aplicación {app_name}: {exc}")
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def open_external_protocol(uri: str) -> Dict[str, Any]:
        """
        Dispara enlaces de protocolo local (ej. sip:usuario@dominio, whatsapp://send?phone=...).
        """
        try:
            webbrowser.open(uri)
            logger.info(f"Enlace de protocolo externo invocado: {uri}")
            return {"ok": True, "uri": uri}
        except Exception as exc:
            logger.error(f"Error al abrir URI {uri}: {exc}")
            return {"ok": False, "error": str(exc)}