"""
Ruta: tests/test_phase2_providers.py
Descripción: Pruebas unitarias de la Fase 2 (Proveedores intercambiables, modo strict_local,
política de fallback local_first, protección de capturas/datos sensibles y clasificación de errores).
No realiza llamadas de red reales ni requiere GEMINI_API_KEY.
"""
import unittest
from unittest.mock import MagicMock
import requests

from modules.llm_providers import (
    GeminiProvider,
    LLMResponse,
    OllamaProvider,
    ProviderRouter,
)


class TestPhase2ProvidersAndPrivacy(unittest.TestCase):
    # ---------------- 1. GARANTÍA DE CERO LLAMADAS REMOTAS EN STRICT_LOCAL ----------------
    def test_strict_local_never_calls_cloud_even_when_local_fails(self) -> None:
        mock_local = MagicMock(spec=OllamaProvider)
        mock_local.active_model = "llama3.1:latest"
        mock_local.vision_model = ""
        mock_local.generate_text.return_value = LLMResponse(
            ok=False, provider="ollama", model="llama3.1:latest", error="Conexión rechazada", error_type="network"
        )

        mock_cloud = MagicMock(spec=GeminiProvider)
        mock_cloud.is_available.return_value = True

        router = ProviderRouter(
            local_provider=mock_local,
            cloud_provider=mock_cloud,
            mode="strict_local",
            cloud_fallback="auto",
            allow_cloud_sensitive=True,
        )

        # Prueba en chat
        chat_res = router.chat([{"role": "user", "content": "Hola"}])
        self.assertFalse(chat_res.ok)
        self.assertIn("Modo Estricto Local", chat_res.error)
        mock_cloud.generate_text.assert_not_called()

        # Prueba en visión de pantalla
        vis_res = router.analyze_screen_image("¿Qué hay en mi pantalla?", base64_png="iVBORw0KGgo=")
        self.assertFalse(vis_res.ok)
        self.assertEqual(vis_res.error_type, "policy_blocked")
        mock_cloud.analyze_image.assert_not_called()

    # ---------------- 2. PRIORIDAD LOCAL Y POLÍTICA DE FALLBACK EN LOCAL_FIRST ----------------
    def test_local_first_uses_ollama_without_touching_cloud_when_healthy(self) -> None:
        mock_local = MagicMock(spec=OllamaProvider)
        mock_local.active_model = "llama3.1:latest"
        mock_local.generate_text.return_value = LLMResponse(
            ok=True, provider="ollama", model="llama3.1:latest", text="Respuesta 100% local."
        )
        mock_cloud = MagicMock(spec=GeminiProvider)
        mock_cloud.is_available.return_value = True

        router = ProviderRouter(
            local_provider=mock_local,
            cloud_provider=mock_cloud,
            mode="local_first",
            cloud_fallback="auto",
        )

        res = router.chat([{"role": "user", "content": "Resumen del día"}])
        self.assertTrue(res.ok)
        self.assertEqual(res.provider, "ollama")
        mock_cloud.generate_text.assert_not_called()

    def test_local_first_blocks_automatic_cloud_fallback_when_manual_approval_required(self) -> None:
        mock_local = MagicMock(spec=OllamaProvider)
        mock_local.active_model = "llama3.1:latest"
        mock_local.generate_text.return_value = LLMResponse(
            ok=False, provider="ollama", model="llama3.1:latest", error="Ollama apagado", error_type="network"
        )
        mock_cloud = MagicMock(spec=GeminiProvider)
        mock_cloud.is_available.return_value = True
        mock_cloud.generate_text.return_value = LLMResponse(
            ok=True, provider="gemini", model="gemini-2.5-flash", text="Respuesta desde la nube tras aprobar."
        )

        router = ProviderRouter(
            local_provider=mock_local,
            cloud_provider=mock_cloud,
            mode="local_first",
            cloud_fallback="manual_approval",
        )

        # Sin aprobación: bloquea el salto automático a la nube
        blocked = router.chat([{"role": "user", "content": "Hola"}])
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.error_type, "policy_blocked")
        mock_cloud.generate_text.assert_not_called()

        # Con aprobación de un solo uso: permite el fallback
        router.approve_cloud_once()
        approved = router.chat([{"role": "user", "content": "Hola"}])
        self.assertTrue(approved.ok)
        self.assertEqual(approved.provider, "gemini")
        mock_cloud.generate_text.assert_called_once()

    # ---------------- 3. PROTECCIÓN DE CAPTURAS Y DATOS SENSIBLES ----------------
    def test_sensitive_data_and_screenshots_require_explicit_permission_for_cloud(self) -> None:
        mock_local = MagicMock(spec=OllamaProvider)
        mock_local.active_model = "llama3.1:latest"
        mock_local.vision_model = ""
        mock_cloud = MagicMock(spec=GeminiProvider)
        mock_cloud.is_available.return_value = True
        mock_cloud.analyze_image.return_value = LLMResponse(
            ok=True, provider="gemini", model="gemini-2.5-flash", text="Veo VS Code abierto."
        )

        router = ProviderRouter(
            local_provider=mock_local,
            cloud_provider=mock_cloud,
            mode="cloud_first",
            allow_cloud_sensitive=False,
        )

        # Intento de subir captura de pantalla sin permiso -> bloqueado
        snap_blocked = router.analyze_screen_image("Mira mi pantalla", base64_png="dummy_b64")
        self.assertFalse(snap_blocked.ok)
        self.assertEqual(snap_blocked.error_type, "policy_blocked")
        mock_cloud.analyze_image.assert_not_called()

        # Al otorgar aprobación puntual -> se permite una vez
        router.approve_cloud_once()
        snap_ok = router.analyze_screen_image("Mira mi pantalla", base64_png="dummy_b64")
        self.assertTrue(snap_ok.ok)
        mock_cloud.analyze_image.assert_called_once()

    # ---------------- 4. DISTINCIÓN DE ERRORES DE RED, TIMEOUT Y AUTENTICACIÓN ----------------
    def test_providers_distinguish_auth_timeout_and_network_errors(self) -> None:
        mock_http = MagicMock(spec=requests.Session)

        # Simular error 403 de autenticación en Gemini
        resp_403 = MagicMock()
        resp_403.status_code = 403
        mock_http.post.return_value = resp_403
        gemini = GeminiProvider(http_session=mock_http)
        # Forzar disponibilidad simulada para la prueba sin clave real
        gemini.is_available = lambda: True  # type: ignore[method-assign]

        auth_res = gemini.generate_text([{"role": "user", "content": "Test"}])
        self.assertFalse(auth_res.ok)
        self.assertEqual(auth_res.error_type, "auth")

        # Simular Timeout en Ollama
        mock_http.post.side_effect = requests.Timeout("Timeout simulado")
        ollama = OllamaProvider(http_session=mock_http)
        timeout_res = ollama.generate_text([{"role": "user", "content": "Test"}])
        self.assertFalse(timeout_res.ok)
        self.assertEqual(timeout_res.error_type, "timeout")


if __name__ == "__main__":
    unittest.main()