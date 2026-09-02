"""Volcado a texto plano de los correos listos, para revisar antes de mandar.

Los correos viven en leads_listos.json, que no es cómodo para leer a mano.
Esto genera el mismo tipo de vista legible que ya existe para WhatsApp en
whatsapp.py, así que revisar ambos canales antes de enviar es la misma
rutina: abrir una carpeta y leer archivos de texto.
"""
from __future__ import annotations

from pathlib import Path

from ..config import COMPOSED_DIR
from ..logging_setup import get_logger
from ..models import Lead
from ..storage import to_absolute
from ..utils import slugify

log = get_logger("preview")

PREVIEW_DIR = COMPOSED_DIR / "preview"
INDICE_FILE = "_INDICE.txt"


def _archivo(lead: Lead) -> Path:
    return PREVIEW_DIR / f"{slugify(lead.id, max_len=60)}.txt"


def _contenido(lead: Lead) -> str:
    borrador = lead.email_draft
    auditoria = lead.audit
    adjunto = to_absolute(borrador.adjunto) if borrador.adjunto else None
    return (
        f"NEGOCIO:   {lead.etiqueta}\n"
        f"EMAIL:     {lead.email}\n"
        f"ADJUNTO:   {adjunto.name if adjunto and adjunto.exists() else '(ninguno)'}\n"
        f"SCORE:     {auditoria.score if auditoria else '?'}/100 ({auditoria.veredicto if auditoria else '?'})\n"
        f"MOTOR:     {borrador.generado_por}\n"
        f"{'─' * 60}\n"
        f"ASUNTO: {borrador.asunto}\n\n"
        f"{borrador.cuerpo}\n"
    )


def _limpiar_huerfanos(vigentes: set[str]) -> None:
    """Borra .txt de leads que ya no califican (p. ej. un re-audit bajó el
    score bajo el umbral). Sin esto, un correo descartado se queda en la
    carpeta como si todavía estuviera listo para mandar."""
    if not PREVIEW_DIR.exists():
        return
    for archivo in PREVIEW_DIR.glob("*.txt"):
        if archivo.name != INDICE_FILE and archivo.name not in vigentes:
            archivo.unlink()


def exportar(leads: list[Lead]) -> list[Lead]:
    """Escribe un .txt por correo listo más un índice ordenado por score.
    Idempotente: se reescribe todo en cada corrida a partir del estado actual."""
    listos = [l for l in leads if l.estado == "listo" and l.email_draft]
    _limpiar_huerfanos({_archivo(l).name for l in listos})
    if not listos:
        (PREVIEW_DIR / INDICE_FILE).unlink(missing_ok=True)
        return leads

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    listos.sort(key=lambda l: -(l.audit.score if l.audit else 0))

    lineas = [
        "ÍNDICE — ordenado por oportunidad (score de auditoría)",
        "Revisá cada archivo antes de correr 'send'. Nada se envía desde acá.",
        "=" * 70,
        "",
    ]
    for lead in listos:
        ruta = _archivo(lead)
        ruta.write_text(_contenido(lead), encoding="utf-8")
        score = lead.audit.score if lead.audit else 0
        lineas.append(f"{score:>3}/100  {lead.etiqueta[:38]:<38} {lead.email:<32} {ruta.name}")

    (PREVIEW_DIR / INDICE_FILE).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    log.info("Preview: %d correos listos para revisar en %s", len(listos), PREVIEW_DIR)
    return leads
