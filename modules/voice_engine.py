"""
Ruta: modules/voice_engine.py
Descripción: Motor de voz neuronal con modulación de tono grave futurista (Pitch/Rate DSP),
VAD acústico anti-cortes, soporte Barge-In (<10ms) y sincronización con el HUD Holográfico.
"""
import asyncio
import logging
import os
import tempfile
import threading
from typing import Optional, Callable
import speech_recognition as sr
import pyttsx3
import edge_tts
import pygame
from config import Config

logger = logging.getLogger("VoiceEngine")


class VoiceEngine:
    def __init__(self, on_state_change: Optional[Callable[[str], None]] = None) -> None:
        self.on_state_change = on_state_change
        self.recognizer = sr.Recognizer()

        # Ajuste SOTA para evitar cortes mientras el usuario piensa o toma aire
        self.recognizer.pause_threshold = 1.75          # Espera 1.75s de silencio real antes de cerrar la frase
        self.recognizer.non_speaking_duration = 0.6     # Mantiene margen previo y posterior de audio
        self.recognizer.energy_threshold = 280          # Sensibilidad base óptima para voz humana
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5

        self.mic_available = False
        self.tts_available = False
        self._ambient_calibrated = False
        self._speak_lock = threading.Lock()
        self._listen_lock = threading.Lock()
        self._abort_speech = threading.Event()

        # Configuración de timbre grave futurista (estilo J.A.R.V.I.S.)
        self.voice_name: str = getattr(Config, "ASSISTANT_VOICE", "es-ES-AlvaroNeural")
        if self.voice_name == "es-PE-AlexNeural":
            self.voice_name = "es-ES-AlvaroNeural"
        self.voice_pitch: str = getattr(Config, "VOICE_PITCH", "-14Hz")
        self.voice_rate: str = getattr(Config, "VOICE_RATE_STR", "+6%")

        try:
            pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=1024)
            self.neural_audio_ready = True
        except Exception as exc:
            logger.warning(f"No se pudo iniciar pygame.mixer ({exc}).")
            self.neural_audio_ready = False

        self._init_fallback_tts()
        self._check_and_calibrate_microphone()

    def set_voice_profile(self, voice_name: str, pitch: str = "-14Hz", rate: str = "+6%") -> None:
        """Permite ajustar la profundidad de la voz en caliente desde el HUD."""
        self.voice_name = voice_name
        self.voice_pitch = pitch
        self.voice_rate = rate
        logger.info(f"Perfil de voz actualizado: {voice_name} | Pitch: {pitch} | Rate: {rate}")

    def stop_speaking(self) -> None:
        """Interrupción instantánea (Barge-In): corta cualquier locución activa en <10ms."""
        self._abort_speech.set()
        if self.neural_audio_ready:
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
            except Exception:
                pass
        if self.tts_available:
            try:
                self.engine.stop()
            except Exception:
                pass
        self._notify_state("IDLE")

    def _notify_state(self, state: str) -> None:
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception:
                pass

    def _init_fallback_tts(self) -> None:
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 165)
            self.engine.setProperty("volume", 1.0)
            self.tts_available = True
        except Exception:
            self.tts_available = False

    def _check_and_calibrate_microphone(self) -> None:
        """Calibra el ruido de fondo una sola vez al arrancar para no comer las primeras sílabas."""
        try:
            mics = sr.Microphone.list_microphone_names()
            self.mic_available = bool(mics)
            if self.mic_available:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                    # Evitar que un pico de ruido inicial deje el micrófono sordo
                    if self.recognizer.energy_threshold > 900:
                        self.recognizer.energy_threshold = 350
                    self._ambient_calibrated = True
                logger.info(f"Micrófono calibrado (Umbral de energía: {round(self.recognizer.energy_threshold)})")
        except Exception as exc:
            logger.warning(f"No se pudo calibrar micrófono al inicio: {exc}")
            self.mic_available = False

    async def _synthesize_edge_tts(self, text: str, output_path: str) -> None:
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice_name,
            pitch=self.voice_pitch,
            rate=self.voice_rate
        )
        await communicate.save(output_path)

    def speak(self, text: str) -> None:
        """Sintetiza voz neuronal con frecuencia grave (-14Hz) e interrupción Barge-In."""
        if not text:
            return
        clean_text = text.replace("*", "").replace("#", "").strip()
        if not clean_text:
            return

        self.stop_speaking()

        with self._speak_lock:
            self._abort_speech.clear()
            print(f"\n[{Config.AGENT_NAME}]: {clean_text}")
            self._notify_state("SPEAKING")

            if self.neural_audio_ready:
                temp_file = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                        temp_file = fp.name

                    asyncio.run(self._synthesize_edge_tts(clean_text, temp_file))

                    if self._abort_speech.is_set():
                        if temp_file and os.path.exists(temp_file):
                            os.remove(temp_file)
                        self._notify_state("IDLE")
                        return

                    pygame.mixer.music.load(temp_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        if self._abort_speech.is_set():
                            pygame.mixer.music.stop()
                            break
                        pygame.time.Clock().tick(30)
                    pygame.mixer.music.unload()
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                    self._notify_state("IDLE")
                    return
                except Exception as exc:
                    logger.warning(f"Fallo en síntesis neuronal ({exc}). Usando respaldo.")
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except OSError:
                            pass

            if self.tts_available and not self._abort_speech.is_set():
                try:
                    self.engine.say(clean_text)
                    self.engine.runAndWait()
                except Exception as exc:
                    logger.error(f"Error TTS offline: {exc}")

            self._notify_state("IDLE")

    def listen(self, timeout: int = 8, phrase_time_limit: int = 45) -> Optional[str]:
        """
        Escucha la instrucción completa del usuario permitiendo pausas naturales de hasta 1.75s
        y dictados largos de hasta 45 segundos continuos.
        """
        if not self.mic_available:
            return None
        self.stop_speaking()

        if not self._listen_lock.acquire(blocking=False):
            return None
        try:
            self._notify_state("LISTENING")
            with sr.Microphone() as source:
                if not self._ambient_calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.35)
                    self._ambient_calibrated = True

                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            self._notify_state("THINKING")
            query = self.recognizer.recognize_google(audio, language=Config.LANGUAGE_CODE)
            logger.info(f"Voz reconocida: '{query}'")
            self._notify_state("IDLE")
            return query.strip()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            self._notify_state("IDLE")
            return None
        except Exception as exc:
            logger.error(f"Error en captura de voz: {exc}")
            self._notify_state("IDLE")
            return None
        finally:
            self._listen_lock.release()