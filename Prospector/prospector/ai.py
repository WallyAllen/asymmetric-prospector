"""Cliente Gemini con reintentos, throttling y degradación elegante.

Regla del proyecto: la IA nunca es un punto único de fallo. Si no hay clave,
si el modelo cae o si devuelve basura, el pipeline sigue con las reglas
deterministas y las plantillas.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Sequence

from .config import AISettings
from .logging_setup import get_logger

log = get_logger("ia")

_JSON_EN_TEXTO = re.compile(r"\{.*\}", re.S)


class AIUnavailable(RuntimeError):
    """No hay IA disponible: el llamador debe usar su plan B."""


class GeminiClient:
    def __init__(self, cfg: AISettings) -> None:
        self.cfg = cfg
        self._client = None
        self._lock = threading.Lock()
        self._ultima_llamada = 0.0

    # ---------------------------------------------------------------- interno
    def _ensure(self):
        if self._client is not None:
            return self._client
        if not self.cfg.enabled:
            raise AIUnavailable("GEMINI_API_KEY no configurada")
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise AIUnavailable("El paquete google-genai no está instalado") from exc
        self._client = genai.Client(api_key=self.cfg.api_key)
        return self._client

    def _throttle(self) -> None:
        with self._lock:
            espera = self.cfg.min_interval_s - (time.monotonic() - self._ultima_llamada)
            if espera > 0:
                time.sleep(espera)
            self._ultima_llamada = time.monotonic()

    @staticmethod
    def _parse_json(texto: str) -> dict[str, Any]:
        texto = (texto or "").strip()
        if texto.startswith("```"):
            texto = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", texto).strip()
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            encontrado = _JSON_EN_TEXTO.search(texto)
            if not encontrado:
                raise
            return json.loads(encontrado.group(0))

    # ---------------------------------------------------------------- público
    @property
    def disponible(self) -> bool:
        return self.cfg.enabled

    def generar_json(
        self,
        prompt: str,
        imagenes: Sequence[Path] | None = None,
        temperatura: float | None = None,
        esquema: dict | None = None,
    ) -> dict[str, Any]:
        cliente = self._ensure()
        from google.genai import types

        contenidos: list[Any] = []
        for ruta in imagenes or []:
            ruta = Path(ruta)
            if not ruta.exists():
                continue
            contenidos.append(
                types.Part.from_bytes(data=ruta.read_bytes(), mime_type="image/png")
            )
        contenidos.append(prompt)

        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": self.cfg.temperature_copy if temperatura is None else temperatura,
        }
        if esquema:
            config["response_schema"] = esquema

        ultimo_error: Exception | None = None
        for intento in range(1, self.cfg.max_retries + 1):
            self._throttle()
            try:
                respuesta = cliente.models.generate_content(
                    model=self.cfg.model,
                    contents=contenidos,
                    config=types.GenerateContentConfig(**config),
                )
                return self._parse_json(respuesta.text)
            except Exception as exc:  # noqa: BLE001 - cuota, red, JSON inválido...
                ultimo_error = exc
                mensaje = str(exc)
                if "RESOURCE_EXHAUSTED" in mensaje or "429" in mensaje:
                    espera = min(60, 8 * intento)
                    log.warning("Cuota de Gemini agotada; esperando %ds", espera)
                    time.sleep(espera)
                elif "NOT_FOUND" in mensaje or "404" in mensaje:
                    log.error("El modelo '%s' no existe o no está disponible", self.cfg.model)
                    break
                else:
                    log.debug("Intento %d fallido: %s", intento, mensaje)
                    time.sleep(1.5 * intento)
        raise AIUnavailable(f"Gemini no respondió tras {self.cfg.max_retries} intentos: {ultimo_error}")


_cliente_global: GeminiClient | None = None


def get_client(cfg: AISettings) -> GeminiClient:
    global _cliente_global
    if _cliente_global is None:
        _cliente_global = GeminiClient(cfg)
    return _cliente_global
