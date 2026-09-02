"""El jurado visual: Gemini confirma (o desmiente) lo que midieron las reglas.

Se invoca SOLO sobre los leads que ya superaron el umbral objetivo, así el
coste de IA se concentra donde hay negocio real. Su trabajo no es descubrir
el problema —eso ya está medido— sino ponerle palabras humanas y decir dónde
mirar en la captura.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..ai import AIUnavailable, GeminiClient
from ..logging_setup import get_logger
from ..models import Finding, Lead

log = get_logger("jurado")

PROMPT = """\
Eres director creativo y especialista en CRO. Te doy dos capturas de la misma web
(1: escritorio, 2: móvil) y una auditoría técnica ya medida con instrumentos.

Negocio: {nombre}
Sector: {nicho}
Auditoría objetiva (datos reales, no opiniones):
{hallazgos}

SÉ ESCÉPTICO POR DEFECTO. La mayoría de las webs de negocios reales son landing
pages funcionales y profesionales, aunque tengan detalles mejorables. Tu urgencia
por defecto para una web que se ve profesional, con un CTA claro y sin errores
visuales evidentes es BAJA (2-4), no alta. Solo sube a 7+ si ves con tus propios
ojos algo que un cliente potencial notaría de inmediato y que le haría dudar de
contactar: un hueco vacío donde debería haber una llamada a la acción, texto
ilegible o cortado, un elemento roto, un aviso que tapa todo, o una jerarquía tan
confusa que no queda claro qué hace el negocio. "Podría verse mejor" o "el diseño
es genérico" NO son motivo de urgencia alta: son opiniones de diseño, no fugas de
clientes. Si la auditoría objetiva marca pocos hallazgos, es señal de que la web
va bien: no busques un problema donde no lo hay para justificar el correo.

Tu trabajo NO es repetir los datos ni inflar la urgencia para justificar un correo.
Es:
1. Confirmar si lo que se ve respalda el diagnóstico (`confirma_diagnostico`).
   Si la web se ve profesional y funcional pese a las métricas, dilo con
   franqueza, pon `confirma_diagnostico: false` y una urgencia baja: es preferible
   descartar un lead dudoso que enviar un correo con un argumento falso que el
   dueño del negocio va a rebatir en diez segundos mirando su propia pantalla.
2. Solo si de verdad hay algo grave: elegir EL problema visual más sangrante de la
   primera pantalla, el que un dueño de negocio entendería sin saber nada de diseño.
3. Escribirlo en una frase concreta, en español neutro, sin jerga técnica, sin
   adjetivos de marketing y sin sonar a plantilla. Menciona algo específico que se
   vea en la captura (un color, un texto, un espacio vacío, una foto) para que sea
   imposible confundirlo con un correo masivo.
4. Indicar la zona de la captura de ESCRITORIO donde está ese problema, en
   coordenadas normalizadas 0-1.

Devuelve solo este JSON:
{{
  "confirma_diagnostico": true,
  "urgencia": 8,
  "problema_visual": "frase concreta y específica",
  "detalle_observado": "qué se ve exactamente en la captura, una frase",
  "zona": {{"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.35}},
  "calidad_percibida": "amateur|correcta|profesional"
}}"""


def _formatear(hallazgos: list[Finding]) -> str:
    if not hallazgos:
        return "- (sin hallazgos objetivos relevantes)"
    return "\n".join(
        f"- {h.titulo} · {h.evidencia}" for h in sorted(hallazgos, key=lambda f: -f.severidad)[:6]
    )


def juzgar(
    cliente: GeminiClient,
    lead: Lead,
    hallazgos: list[Finding],
    capturas: dict[str, Path],
    ancho_desktop: int,
    alto_desktop: int,
) -> dict:
    """Devuelve el dictamen del jurado, o {} si la IA no está disponible."""
    imagenes = [p for p in (capturas.get("desktop_fold"), capturas.get("mobile_fold")) if p]
    if not imagenes:
        return {}

    prompt = PROMPT.format(
        nombre=lead.nombre or lead.url,
        nicho=lead.nicho or "no especificado",
        hallazgos=_formatear(hallazgos),
    )
    try:
        dictamen = cliente.generar_json(prompt, imagenes=imagenes, temperatura=0.2)
    except (AIUnavailable, json.JSONDecodeError) as exc:
        log.warning("Jurado IA no disponible para %s (%s)", lead.etiqueta, exc)
        return {}

    zona = dictamen.get("zona") or {}
    if all(isinstance(zona.get(k), (int, float)) for k in ("x", "y", "width", "height")):
        dictamen["zona_px"] = {
            "x": max(0.0, float(zona["x"])) * ancho_desktop,
            "y": max(0.0, float(zona["y"])) * alto_desktop,
            "width": min(1.0, float(zona["width"])) * ancho_desktop,
            "height": min(1.0, float(zona["height"])) * alto_desktop,
        }
    return dictamen


def a_finding(dictamen: dict) -> Finding | None:
    """Convierte el dictamen en un hallazgo más del expediente."""
    problema = (dictamen or {}).get("problema_visual")
    if not problema:
        return None
    urgencia = int(dictamen.get("urgencia") or 6)
    return Finding(
        rule_id="jurado_visual",
        titulo="Diagnóstico visual",
        severidad=max(1, min(10, urgencia)),
        peso=0,  # No suma al score: el score es solo de datos duros.
        evidencia=dictamen.get("detalle_observado") or "Revisión visual de la primera pantalla",
        argumento=problema,
        zona=dictamen.get("zona_px"),
    )
