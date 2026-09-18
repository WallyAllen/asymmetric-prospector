"""Marcar a mano que un lead contestó, y que el sistema no le escriba nunca más.

El `PLAN_OUTREACH_V3` lo dice sin vueltas: *"cualquier camino por el que un
lead que respondió reciba el toque 2 es un bug de severidad máxima"*. Hasta
ahora no había ningún camino para evitarlo — no existía el estado.

El bucle IMAP de la Fase 1 va a detectar las respuestas de correo solas. Para
WhatsApp nunca va a hacer falta: las respuestas las ve la persona que manda,
en el mismo momento. Así que esto es lo que tapa el agujero hoy, con un
comando de una línea, y sigue sirviendo después para los casos que la
detección automática no cubra (una llamada, un mensaje por otro lado,
alguien que contesta desde otra dirección).

    py -m prospector respondio rodolfomonte.com
    py -m prospector respondio leandro@rodolfomonte.com --nota "pidió el boceto"
    py -m prospector respondio otracosa.com --baja       # no le interesa

`--baja` además lo manda a la lista de supresión, que es para siempre y vale
para los dos canales. Una respuesta normal NO suprime: contestó, que es
justamente a quien sí querés volver a escribirle.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .config import COMPOSED_FILE, SENT_DIR
from .logging_setup import get_logger
from .models import Lead
from .storage import add_to_suppression, load_leads, read_json, save_leads, write_json

log = get_logger("respuestas")

RESPUESTAS_FILE = SENT_DIR / "respuestas.json"


def _coincide(lead: Lead, clave: str) -> bool:
    """Se acepta el id, el dominio, el email o el teléfono, para no tener que
    ir a buscar el id exacto al JSON con un mensaje sin contestar esperando."""
    clave = clave.strip().lower()
    candidatos = {lead.id.lower(), (lead.email or "").lower(), (lead.telefono or "").lower()}
    candidatos |= {c.lower() for c in lead.emails}
    if lead.url:
        candidatos.add(lead.url.lower())
    return clave in candidatos or any(clave and clave in c for c in candidatos if c)


def marcar(clave: str, nota: str = "", baja: bool = False) -> Lead | None:
    """Marca al lead como respondido (o dado de baja) y lo saca de toda cola."""
    leads = load_leads(COMPOSED_FILE)
    encontrados = [lead for lead in leads if _coincide(lead, clave)]
    if not encontrados:
        log.error("No encontré ningún lead para %r", clave)
        return None
    if len(encontrados) > 1:
        log.error("%r coincide con %d leads: %s", clave, len(encontrados),
                  ", ".join(l.id for l in encontrados[:5]))
        return None

    lead = encontrados[0]
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lead.estado = "baja" if baja else "respondido"
    lead.respondido_el = ahora
    if nota:
        lead.nota_respuesta = nota

    registro = read_json(RESPUESTAS_FILE, []) or []
    registro.append({
        "id": lead.id,
        "nombre": lead.nombre,
        "canal": lead.canal or ("email" if lead.email else "whatsapp"),
        "enviado_el": lead.enviado_el,
        "respondido_el": ahora,
        "tipo": "baja" if baja else "respuesta",
        "nota": nota,
        "score": lead.audit.score if lead.audit else None,
        "nicho": lead.nicho,
    })
    write_json(RESPUESTAS_FILE, registro)
    save_leads(COMPOSED_FILE, leads)

    if baja:
        # La supresión es para siempre y vale para los dos canales.
        for entrada in filter(None, [lead.email, lead.telefono, lead.id]):
            add_to_suppression(entrada, motivo="pidió la baja")
        log.info("✖ %s dado de baja y suprimido en los dos canales", lead.etiqueta)
    else:
        log.info("✔ %s marcado como respondido: fuera de toda cola", lead.etiqueta)
        if lead.enviado_el:
            log.info("  contactado el %s · respondió %s",
                     lead.enviado_el[:10], ahora[:10])
    return lead
