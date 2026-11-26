"""
Ruta: modules/voip_caller.py
Descripción: Enrutador de llamadas VoIP/SIP y WebRTC de costo cero mediante Linphone CLI,
protocolos nativos del sistema operativo (sip:/tel:) y salas WebRTC abiertas.
"""
import re
import uuid
import shutil
import subprocess
import webbrowser
import logging
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger("VoIPCaller")


class VoIPCaller:
    def __init__(self) -> None:
        self.softphone_bin = Config.SIP_SOFTPHONE_BIN
        self.cli_available = shutil.which(self.softphone_bin) is not None
        if self.cli_available:
            logger.info(f"Binario VoIP CLI detectado: {self.softphone_bin}")
        else:
            logger.info(
                "Linphone CLI no detectado en PATH. Se usará despacho por protocolo SIP/TEL nativo y WebRTC."
            )

    @staticmethod
    def format_target(raw_target: str) -> Optional[str]:
        """
        Determina si el destino es una dirección SIP (usuario@dominio) o un número telefónico.
        """
        cleaned = raw_target.strip().replace(" ", "")
        if not cleaned:
            return None

        # Si es una cuenta SIP (ej. usuario@sip.linphone.org)
        if "@" in cleaned:
            return cleaned if cleaned.startswith("sip:") else f"sip:{cleaned}"

        # Si es un número telefónico
        digits = re.sub(r"[^\d+]", "", cleaned)
        if len(digits) >= 6:
            if not digits.startswith("+") and len(digits) == 9:
                digits = f"{Config.DEFAULT_COUNTRY_CODE}{digits}"
            return digits

        return None

    def start_call(self, target: str, mode: str = "auto") -> Dict[str, Any]:
        """
        Inicia una llamada gratuita usando:
        - 'cli': Linphone CLI local (si está disponible)
        - 'protocol': URI sip: o tel: (abre softphone de escritorio o Enlace Móvil de Windows)
        - 'webrtc': Crea una sala de voz WebRTC instantánea sin registro
        """
        if mode == "webrtc":
            return self.start_webrtc_room()

        formatted = self.format_target(target)
        if not formatted:
            return {
                "ok": False,
                "error": f"Destino de llamada inválido ('{target}'). Indica un número o cuenta SIP."
            }

        # 1. Intentar por Linphone CLI si está instalado en el sistema
        if self.cli_available and mode in ("auto", "cli"):
            try:
                subprocess.run(
                    [self.softphone_bin, "init"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
                res = subprocess.run(
                    [self.softphone_bin, "generic", f"call {formatted}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    logger.info(f"Llamada SIP originada por CLI hacia {formatted}")
                    return {"ok": True, "method": "Linphone CLI", "target": formatted}
            except Exception as exc:
                logger.warning(f"Fallo en llamada CLI ({exc}). Conmutando a protocolo nativo...")

        # 2. Enrutamiento por protocolo nativo del SO (sip: o tel:)
        try:
            uri = formatted if formatted.startswith("sip:") else f"tel:{formatted}"
            webbrowser.open(uri)
            logger.info(f"Protocolo de llamada invocado: {uri}")
            return {"ok": True, "method": "Protocolo Nativo (SIP/TEL)", "target": uri}
        except Exception as exc:
            logger.error(f"Error al disparar protocolo de llamada: {exc}")
            return {"ok": False, "error": str(exc)}

    def hangup_call(self) -> Dict[str, Any]:
        """Corta una llamada activa en Linphone CLI."""
        if not self.cli_available:
            return {
                "ok": False,
                "error": "El corte por comando requiere Linphone CLI activo; cierra desde la ventana del softphone."
            }
        try:
            subprocess.run(
                [self.softphone_bin, "generic", "terminate"],
                capture_output=True,
                text=True,
                timeout=4
            )
            logger.info("Llamada finalizada por comando CLI.")
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def start_webrtc_room() -> Dict[str, Any]:
        """
        Genera y abre un canal de llamada de voz/video WebRTC gratuito sin cuenta ni tarjeta.
        """
        try:
            room_id = f"Argon4-Voice-{uuid.uuid4().hex[:8]}"
            room_url = f"https://meet.jit.si/{room_id}#config.startWithVideoMuted=true"
            webbrowser.open(room_url)
            logger.info(f"Sala de voz WebRTC abierta: {room_url}")
            return {"ok": True, "method": "WebRTC Directo", "url": room_url}
        except Exception as exc:
            logger.error(f"Error al crear sala WebRTC: {exc}")
            return {"ok": False, "error": str(exc)}