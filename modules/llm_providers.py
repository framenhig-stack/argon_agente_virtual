"""
Ruta: modules/llm_providers.py
Descripción: Abstracción común de proveedores LLM (Ollama local y Google Gemini remoto)
y enrutador con control de privacidad Local-First (Fase 2).
"""
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Literal, Optional
import requests
from config import Config

logger = logging.getLogger("LLMProviders")

ErrorType = Literal[
    "none",
    "auth",
    "network",
    "timeout",
    "invalid_response",
    "policy_blocked",
    "unsupported",
    "unavailable",
]


@dataclass
class LLMResponse:
    ok: bool
    provider: str
    model: str
    text: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""
    error_type: ErrorType = "none"


class OllamaProvider:
    """Adaptador para inferencia 100% local mediante Ollama."""

    name: str = "ollama"

    def __init__(self, http_session: Optional[requests.Session] = None) -> None:
        self.http = http_session or requests.Session()
        self.active_model: str = Config.OLLAMA_MODEL
        self.vision_model: str = Config.OLLAMA_VISION_MODEL

    def is_available(self) -> bool:
        try:
            resp = self.http.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", []) if m.get("name")]
                if models:
                    if Config.OLLAMA_MODEL in models:
                        self.active_model = Config.OLLAMA_MODEL
                    else:
                        self.active_model = models[0]
                    return True
        except requests.RequestException:
            pass
        return False

    def generate_text(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: float = 0.4,
    ) -> LLMResponse:
        full_messages: List[Dict[str, str]] = []
        if system_prompt and (not messages or messages[0].get("role") != "system"):
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": self.active_model,
            "messages": full_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = self.http.post(
                f"{Config.OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=Config.OLLAMA_TIMEOUT,
            )
            if resp.status_code != 200:
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=self.active_model,
                    error=f"Ollama HTTP {resp.status_code}",
                    error_type="invalid_response",
                )
            reply = resp.json().get("message", {}).get("content", "").strip()
            if not reply:
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=self.active_model,
                    error="Respuesta vacía de Ollama.",
                    error_type="invalid_response",
                )
            return LLMResponse(ok=True, provider=self.name, model=self.active_model, text=reply)
        except requests.Timeout:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error="Tiempo de espera agotado en Ollama local.",
                error_type="timeout",
            )
        except requests.RequestException as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error=f"Error de red con Ollama local: {exc}",
                error_type="network",
            )
        except Exception as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error=f"Respuesta inesperada de Ollama: {exc}",
                error_type="invalid_response",
            )

    def generate_tool_calls(
        self,
        user_text: str,
        system_prompt: str,
        ollama_tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        payload = {
            "model": self.active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "tools": ollama_tools,
            "stream": False,
        }
        try:
            resp = self.http.post(
                f"{Config.OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=Config.OLLAMA_TIMEOUT,
            )
            if resp.status_code != 200:
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=self.active_model,
                    error=f"Ollama Tool HTTP {resp.status_code}",
                    error_type="invalid_response",
                )
            msg = resp.json().get("message", {})
            raw_calls = msg.get("tool_calls", []) or []
            normalized_calls: List[Dict[str, Any]] = []
            for c in raw_calls:
                fn_info = c.get("function", {})
                raw_args = fn_info.get("arguments", {})
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                normalized_calls.append({"name": fn_info.get("name", ""), "args": args})

            return LLMResponse(
                ok=True,
                provider=self.name,
                model=self.active_model,
                text=msg.get("content", "").strip(),
                tool_calls=normalized_calls,
            )
        except requests.Timeout:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error="Timeout en Tool Calling de Ollama.",
                error_type="timeout",
            )
        except requests.RequestException as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error=f"Error de conexión con Ollama: {exc}",
                error_type="network",
            )
        except Exception as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error=f"Error procesando Tool Calls de Ollama: {exc}",
                error_type="invalid_response",
            )

    def analyze_image(self, prompt_text: str, base64_png: str, system_prompt: str = "") -> LLMResponse:
        target_model = self.vision_model
        if not target_model:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=self.active_model,
                error="No se ha configurado un modelo de visión local (OLLAMA_VISION_MODEL).",
                error_type="unsupported",
            )
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text, "images": [base64_png]},
            ],
            "stream": False,
        }
        try:
            resp = self.http.post(
                f"{Config.OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=Config.OLLAMA_TIMEOUT,
            )
            if resp.status_code == 200:
                reply = resp.json().get("message", {}).get("content", "").strip()
                if reply:
                    return LLMResponse(ok=True, provider=self.name, model=target_model, text=reply)
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=target_model,
                error=f"Ollama Vision HTTP {resp.status_code}",
                error_type="invalid_response",
            )
        except requests.Timeout:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=target_model,
                error="Timeout en Ollama Vision.",
                error_type="timeout",
            )
        except requests.RequestException as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=target_model,
                error=f"Error de red en Ollama Vision: {exc}",
                error_type="network",
            )


class GeminiProvider:
    """Adaptador para inferencia remota opcional mediante Google Gemini API."""

    name: str = "gemini"

    def __init__(self, http_session: Optional[requests.Session] = None) -> None:
        self.http = http_session or requests.Session()

    def is_available(self) -> bool:
        return bool(Config.GEMINI_API_KEY)

    def _endpoint(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
        )

    def generate_text(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        temperature: float = 0.4,
    ) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="GEMINI_API_KEY no configurada.",
                error_type="auth",
            )

        gemini_contents = []
        for m in messages:
            role = m.get("role")
            if role == "user":
                gemini_contents.append({"role": "user", "parts": [{"text": m.get("content", "")}]})
            elif role == "assistant":
                gemini_contents.append({"role": "model", "parts": [{"text": m.get("content", "")}]})

        payload: Dict[str, Any] = {
            "contents": gemini_contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 450},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            resp = self.http.post(self._endpoint(), json=payload, timeout=25)
            if resp.status_code in (401, 403):
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=Config.GEMINI_MODEL,
                    error=f"Error de autenticación en Gemini API ({resp.status_code}).",
                    error_type="auth",
                )
            if resp.status_code != 200:
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=Config.GEMINI_MODEL,
                    error=f"Gemini API HTTP {resp.status_code}",
                    error_type="invalid_response",
                )

            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                reply = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                if reply:
                    return LLMResponse(ok=True, provider=self.name, model=Config.GEMINI_MODEL, text=reply)

            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="Gemini API devolvió una respuesta sin texto.",
                error_type="invalid_response",
            )
        except requests.Timeout:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="Tiempo de espera agotado consultando Gemini API.",
                error_type="timeout",
            )
        except requests.RequestException as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error=f"Error de red hacia Gemini API: {exc}",
                error_type="network",
            )
        except Exception as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error=f"Error procesando respuesta de Gemini: {exc}",
                error_type="invalid_response",
            )

    def generate_tool_calls(
        self,
        user_text: str,
        system_prompt: str,
        function_declarations: List[Dict[str, Any]],
    ) -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="GEMINI_API_KEY no configurada.",
                error_type="auth",
            )

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "tools": [{"functionDeclarations": function_declarations}],
        }
        try:
            resp = self.http.post(self._endpoint(), json=payload, timeout=20)
            if resp.status_code in (401, 403):
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=Config.GEMINI_MODEL,
                    error=f"Error de autenticación en Gemini ({resp.status_code}).",
                    error_type="auth",
                )
            if resp.status_code != 200:
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=Config.GEMINI_MODEL,
                    error=f"Gemini Tool HTTP {resp.status_code}",
                    error_type="invalid_response",
                )

            candidates = resp.json().get("candidates", [])
            if not candidates:
                return LLMResponse(ok=True, provider=self.name, model=Config.GEMINI_MODEL, tool_calls=[])

            parts = candidates[0].get("content", {}).get("parts", [])
            calls = [
                {"name": p["functionCall"]["name"], "args": p["functionCall"].get("args", {})}
                for p in parts
                if "functionCall" in p
            ]
            text_reply = "".join(p.get("text", "") for p in parts if "text" in p).strip()
            return LLMResponse(
                ok=True,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                text=text_reply,
                tool_calls=calls,
            )
        except requests.Timeout:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="Timeout en Tool Calling de Gemini.",
                error_type="timeout",
            )
        except requests.RequestException as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error=f"Error de red con Gemini: {exc}",
                error_type="network",
            )
        except Exception as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error=f"Respuesta inválida en Tool Calling de Gemini: {exc}",
                error_type="invalid_response",
            )

    def analyze_image(self, prompt_text: str, base64_png: str, system_prompt: str = "") -> LLMResponse:
        if not self.is_available():
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="GEMINI_API_KEY no configurada.",
                error_type="auth",
            )

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt_text},
                        {"inlineData": {"mimeType": "image/png", "data": base64_png}},
                    ],
                }
            ],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 450},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            resp = self.http.post(self._endpoint(), json=payload, timeout=30)
            if resp.status_code in (401, 403):
                return LLMResponse(
                    ok=False,
                    provider=self.name,
                    model=Config.GEMINI_MODEL,
                    error="Error de autenticación en Gemini Vision.",
                    error_type="auth",
                )
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    reply = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if reply:
                        return LLMResponse(ok=True, provider=self.name, model=Config.GEMINI_MODEL, text=reply)
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error=f"Gemini Vision respondió con código {resp.status_code}.",
                error_type="invalid_response",
            )
        except requests.Timeout:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error="Tiempo de espera agotado en Gemini Vision.",
                error_type="timeout",
            )
        except requests.RequestException as exc:
            return LLMResponse(
                ok=False,
                provider=self.name,
                model=Config.GEMINI_MODEL,
                error=f"Error de red en Gemini Vision: {exc}",
                error_type="network",
            )


class ProviderRouter:
    """
    Coordinador central de proveedores LLM.
    Garantiza que el modo 'strict_local' jamás realice llamadas a la nube y que
    los datos sensibles (capturas, portapapeles, archivos) no se envíen a proveedores
    externos sin permiso explícito.
    """

    def __init__(
        self,
        local_provider: Optional[OllamaProvider] = None,
        cloud_provider: Optional[GeminiProvider] = None,
        mode: Optional[str] = None,
        cloud_fallback: Optional[str] = None,
        allow_cloud_sensitive: Optional[bool] = None,
    ) -> None:
        self.local = local_provider or OllamaProvider()
        self.cloud = cloud_provider or GeminiProvider()
        self.mode = (mode or Config.ARGON_MODE).lower()
        self.cloud_fallback = (cloud_fallback or Config.CLOUD_FALLBACK).lower()
        self.allow_cloud_sensitive = (
            Config.ALLOW_CLOUD_SENSITIVE_DATA if allow_cloud_sensitive is None else allow_cloud_sensitive
        )
        self._cloud_Fallback_approved_once: bool = False

    def approve_cloud_once(self) -> None:
        """Autoriza por única vez el envío de una solicitud o captura a la nube."""
        self._cloud_Fallback_approved_once = True

    def _consume_cloud_approval(self) -> bool:
        if self._cloud_Fallback_approved_once:
            self._cloud_Fallback_approved_once = False
            return True
        return False

    def can_use_cloud(self, is_fallback: bool = False, contains_sensitive_data: bool = False) -> tuple[bool, str]:
        """Evalúa si la política actual permite enviar la solicitud al proveedor en la nube."""
        if self.mode == "strict_local":
            return False, "Modo 'strict_local' activo: todas las llamadas a proveedores en la nube están deshabilitadas."

        if not self.cloud.is_available():
            return False, "Proveedor en la nube (Gemini) no tiene GEMINI_API_KEY configurada."

        has_one_time_approval = self._consume_cloud_approval()

        if contains_sensitive_data and not (self.allow_cloud_sensitive or has_one_time_approval):
            return (
                False,
                "Privacidad Local-First: Esta operación incluye datos locales sensibles (captura de pantalla, "
                "portapapeles o código local). Para autorizar su envío a la nube responde 'aprobar nube' "
                "o activa ALLOW_CLOUD_SENSITIVE_DATA=true en .env.",
            )

        if is_fallback:
            if self.cloud_fallback == "disabled":
                return False, "El fallback a la nube está deshabilitado (CLOUD_FALLBACK=disabled)."
            if self.cloud_fallback == "manual_approval" and not has_one_time_approval:
                return (
                    False,
                    "El motor local (Ollama) no está disponible y CLOUD_FALLBACK='manual_approval'. "
                    "Inicia Ollama localmente o di 'aprobar nube' para usar Gemini en esta consulta.",
                )

        return True, ""

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        contains_sensitive_data: bool = False,
    ) -> LLMResponse:
        """Enruta una solicitud de conversación según el modo configurado (strict_local, local_first, cloud_first)."""
        # 1. Modo estrictamente local: solo Ollama, prohibido tocar la nube
        if self.mode == "strict_local":
            res = self.local.generate_text(messages, system_prompt=system_prompt)
            if not res.ok:
                return LLMResponse(
                    ok=False,
                    provider="ollama",
                    model=self.local.active_model,
                    error=f"[Modo Estricto Local] Ollama no pudo responder ({res.error}). Cero datos enviados a la nube.",
                    error_type=res.error_type,
                )
            return res

        # 2. Modo Local-First: intenta primero con Ollama local
        if self.mode == "local_first":
            local_res = self.local.generate_text(messages, system_prompt=system_prompt)
            if local_res.ok:
                return local_res

            allowed, reason = self.can_use_cloud(is_fallback=True, contains_sensitive_data=contains_sensitive_data)
            if not allowed:
                return LLMResponse(
                    ok=False,
                    provider="local_first_guard",
                    model=self.local.active_model,
                    error=reason,
                    error_type="policy_blocked",
                )
            return self.cloud.generate_text(messages, system_prompt=system_prompt)

        # 3. Modo Cloud-First: usa la nube primero (si no viola privacidad de datos sensibles)
        allowed, reason = self.can_use_cloud(is_fallback=False, contains_sensitive_data=contains_sensitive_data)
        if allowed:
            cloud_res = self.cloud.generate_text(messages, system_prompt=system_prompt)
            if cloud_res.ok:
                return cloud_res
            logger.warning(f"Fallo en proveedor cloud ({cloud_res.error}), intentando respaldo local Ollama.")
            return self.local.generate_text(messages, system_prompt=system_prompt)

        # Si contiene datos sensibles no autorizados para la nube, intenta procesarlos localmente en Ollama
        local_res = self.local.generate_text(messages, system_prompt=system_prompt)
        if local_res.ok:
            return local_res

        return LLMResponse(
            ok=False,
            provider="privacy_guard",
            model=Config.GEMINI_MODEL,
            error=reason,
            error_type="policy_blocked",
        )

    def route_tools(
        self,
        user_text: str,
        system_prompt: str,
        gemini_declarations: List[Dict[str, Any]],
        ollama_tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Enruta la selección de herramientas respetando el modo de privacidad."""
        if self.mode == "strict_local":
            return self.local.generate_tool_calls(user_text, system_prompt, ollama_tools)

        if self.mode == "local_first":
            local_res = self.local.generate_tool_calls(user_text, system_prompt, ollama_tools)
            if local_res.ok and local_res.tool_calls:
                return local_res
            if not local_res.ok:
                allowed, _ = self.can_use_cloud(is_fallback=True, contains_sensitive_data=False)
                if allowed:
                    return self.cloud.generate_tool_calls(user_text, system_prompt, gemini_declarations)
            return local_res

        # cloud_first
        allowed, reason = self.can_use_cloud(is_fallback=False, contains_sensitive_data=False)
        if allowed:
            cloud_res = self.cloud.generate_tool_calls(user_text, system_prompt, gemini_declarations)
            if cloud_res.ok:
                return cloud_res
        return self.local.generate_tool_calls(user_text, system_prompt, ollama_tools)

    def analyze_screen_image(
        self,
        prompt_text: str,
        base64_png: str,
        system_prompt: str = "",
    ) -> LLMResponse:
        """
        Analiza una captura de pantalla priorizando visión local si está configurada,
        y exigiendo permiso explícito antes de subir capturas de pantalla a la nube.
        """
        # 1. Si hay un modelo de visión local configurado en Ollama, se intenta primero en modos locales
        if self.mode in ("strict_local", "local_first") and self.local.vision_model:
            local_vis = self.local.analyze_image(prompt_text, base64_png, system_prompt=system_prompt)
            if local_vis.ok or self.mode == "strict_local":
                return local_vis

        if self.mode == "strict_local":
            return LLMResponse(
                ok=False,
                provider="strict_local_guard",
                model=self.local.active_model,
                error=(
                    "Modo 'strict_local' activo: no se permite enviar capturas de pantalla a Gemini Vision. "
                    "Configura OLLAMA_VISION_MODEL (ej. llava) en .env para análisis visual 100% local."
                ),
                error_type="policy_blocked",
            )

        # 2. Compuerta de privacidad obligatoria para capturas de pantalla hacia la nube
        allowed, reason = self.can_use_cloud(
            is_fallback=(self.mode == "local_first"),
            contains_sensitive_data=True,
        )
        if not allowed:
            return LLMResponse(
                ok=False,
                provider="privacy_guard",
                model=Config.GEMINI_MODEL,
                error=reason,
                error_type="policy_blocked",
            )

        return self.cloud.analyze_image(prompt_text, base64_png, system_prompt=system_prompt)