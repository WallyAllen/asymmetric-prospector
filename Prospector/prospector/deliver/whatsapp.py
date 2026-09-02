"""Volcado a texto plano del segmento sin email: contacto manual por WhatsApp.

No hay envío automático acá — Maps da teléfono pero no email para negocios
sin web, así que ese segmento (el de mayor valor según la propia tesis del
sistema) queda fuera de la cola de `mailer.py`. En vez de perderlo, se
redacta igual (mismo motor, mismo texto que un correo) y se deja listo en
`data/05_whatsapp/` para que la persona lo mande a mano.
"""
from __future__ import annotations

from pathlib import Path

from ..config import WHATSAPP_DIR
from ..logging_setup import get_logger
from ..models import Lead
from ..utils import slugify

log = get_logger("whatsapp")

INDICE_FILE = "_INDICE.txt"


def _archivo(lead: Lead) -> Path:
    # Nombre estable por lead.id: no depende del score ni de nada que pueda
    # cambiar entre corridas, así nunca queda un archivo viejo huérfano.
    return WHATSAPP_DIR / f"{slugify(lead.id, max_len=60)}.txt"


def _contenido(lead: Lead) -> str:
    borrador = lead.email_draft
    auditoria = lead.audit
    rating = f"{lead.rating:.1f}".replace(".", ",") if lead.rating else "sin dato"
    resenas = str(lead.resenas) if lead.resenas else "?"
    return (
        f"NEGOCIO:   {lead.etiqueta}\n"
        f"TELÉFONO:  {lead.telefono or 'sin dato'}\n"
        f"RATING:    {rating} en Maps ({resenas} reseñas)\n"
        f"SCORE:     {auditoria.score if auditoria else '?'}/100 ({auditoria.veredicto if auditoria else '?'})\n"
        f"{'─' * 60}\n"
        f"(gancho de referencia, no se manda: \"{borrador.asunto}\")\n\n"
        f"{borrador.cuerpo}\n"
    )


def exportar(leads: list[Lead]) -> list[Lead]:
    """Escribe un .txt por lead listo para WhatsApp más un índice ordenado
    por score. Idempotente: se reescribe todo en cada corrida a partir del
    estado actual, así el índice nunca queda desactualizado."""
    listos = [l for l in leads if l.estado == "listo_whatsapp" and l.email_draft]
    if not listos:
        return leads

    WHATSAPP_DIR.mkdir(parents=True, exist_ok=True)
    listos.sort(key=lambda l: -(l.audit.score if l.audit else 0))

    lineas = [
        "ÍNDICE — ordenado por oportunidad (score de auditoría)",
        "Copiá el texto del archivo y pegalo en WhatsApp Web al teléfono indicado.",
        "=" * 70,
        "",
    ]
    for lead in listos:
        ruta = _archivo(lead)
        ruta.write_text(_contenido(lead), encoding="utf-8")
        score = lead.audit.score if lead.audit else 0
        tel = lead.telefono or "(sin tel)"
        lineas.append(f"{score:>3}/100  {lead.etiqueta[:38]:<38} {tel:<18} {ruta.name}")

    (WHATSAPP_DIR / INDICE_FILE).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    log.info("WhatsApp: %d mensajes listos en %s", len(listos), WHATSAPP_DIR)
    return leads
