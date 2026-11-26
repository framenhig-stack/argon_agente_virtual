"""
Ruta: modules/whatsapp_bridge.py
Descripción: Automatización local de WhatsApp Web sin APIs de pago, con normalización
de números internacionales y respaldo por protocolo URI.
"""
import os
import re
import time
import urllib.parse
import webbrowser
import logging
from typing import Dict, Any, Optional
import pyautogui
import pywhatkit
import requests
from config import Config

logger = logging.getLogger("WhatsAppBridge")


class WhatsAppBridge:
    def __init__(self) -> None:
        # Agenda rápida local: puedes agregar aquí tus contactos frecuentes
        self.contacts: Dict[str, str] = {
            "prueba": os.getenv("TEST_PHONE", ""),
        }

    @staticmethod
    def normalize_phone(raw_input: str) -> Optional[str]:
        """
        Limpia el texto dictado o escrito y lo convierte a formato E.164.
        """
        digits = re.sub(r"[^\d+]", "", raw_input.strip())
        if not digits:
            return None

        if digits.startswith("+"):
            return digits if len(digits) >= 10 else None

        # Si ya incluye el código de país sin el '+'
        clean_cc = Config.DEFAULT_COUNTRY_CODE.replace("+", "")
        if digits.startswith(clean_cc) and len(digits) >= 11:
            return f"+{digits}"

        # Número celular local (ej. 9 dígitos en Perú)
        if len(digits) >= 9:
            return f"{Config.DEFAULT_COUNTRY_CODE}{digits}"

        return None

    def send_message(self, target_phone: str, message: str, wait_time: int = 15) -> Dict[str, Any]:
        """
        Envía un mensaje de WhatsApp intentando primero el puente REST local (Baileys)
        y conmutando a automatización web (pywhatkit / PyAutoGUI) si no está activo.
        """
        phone = self.normalize_phone(target_phone)
        if not phone:
            return {
                "ok": False,
                "error": f"Número inválido ('{target_phone}'). Dicta o escribe al menos 9 dígitos."
            }

        if not message or not message.strip():
            return {"ok": False, "error": "El mensaje está vacío."}

        logger.info(f"Iniciando envío de WhatsApp a {phone}...")

        # 1. Intento vía puente REST local (Baileys)
        try:
            bridge_url = f"{Config.WHATSAPP_BRIDGE_URL}/send"
            payload = {
                "session": Config.WHATSAPP_SESSION,
                "phone": phone,
                "message": message.strip()
            }
            resp = requests.post(bridge_url, json=payload, timeout=4)
            if resp.status_code == 200:
                logger.info(f"WhatsApp enviado con éxito vía puente REST local a {phone}.")
                return {"ok": True, "phone": phone, "message": message.strip()}
            logger.warning(f"Puente REST respondió con código {resp.status_code}. Continuando con navegador...")
        except requests.RequestException as exc:
            logger.info(f"Puente REST local de Baileys no disponible ({exc}). Continuando con flujo de navegador...")

        # 2. Flujo de navegador (pywhatkit + respaldo por URL)
        try:
            # Método principal: abre WhatsApp Web, espera carga, escribe, envía y cierra pestaña
            pywhatkit.sendwhatmsg_instantly(
                phone_no=phone,
                message=message.strip(),
                wait_time=wait_time,
                tab_close=True,
                close_time=3
            )
            logger.info(f"WhatsApp enviado con éxito a {phone}.")
            return {"ok": True, "phone": phone, "message": message.strip()}

        except Exception as exc:
            logger.warning(f"Fallo en pywhatkit ({exc}). Intentando respaldo por URL directa...")
            return self._fallback_web_send(phone, message.strip(), wait_time)

    @staticmethod
    def _fallback_web_send(phone: str, message: str, wait_time: int) -> Dict[str, Any]:
        """Respaldo directo abriendo la URL de WhatsApp Web y presionando Enter con PyAutoGUI."""
        try:
            encoded_msg = urllib.parse.quote(message)
            url = f"https://web.whatsapp.com/send?phone={phone.replace('+', '')}&text={encoded_msg}"
            webbrowser.open(url)
            time.sleep(wait_time)
            pyautogui.press("enter")
            logger.info(f"WhatsApp enviado por vía de respaldo a {phone}.")
            return {"ok": True, "phone": phone, "message": message}
        except Exception as exc:
            logger.error(f"Error crítico enviando WhatsApp: {exc}")
            return {"ok": False, "error": str(exc)}