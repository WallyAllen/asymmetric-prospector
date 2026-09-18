"""Cola, volcado y registro del canal WhatsApp.

No hay envío automático acá —Maps da teléfono pero no email para los negocios
sin web, así que ese segmento (el de mayor valor según la tesis del sistema)
queda fuera de la cola de `mailer.py`—, pero sí hay todo lo demás: cola
ordenada por oportunidad, cuota diaria, ventana horaria, supresión y registro
de lo enviado.

Antes faltaba justamente eso: `scripts/send_whatsapp.py` marcaba
`estado = "enviado"` —el mismo valor que usa el correo— y nada más. Ni fecha,
ni canal, ni registro. Resultado: 56 mensajes mandados sin ningún rastro y un
`registro_envios.json` que describía 49 contactos cuando se habían hecho 105.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..config import SENT_DIR, WHATSAPP_DIR, WHATSAPP_SENT_FILE, Settings, settings
from ..logging_setup import get_logger
from ..models import Lead
from ..storage import load_suppression, read_json, write_json
from ..telefono import para_whatsapp
from ..utils import slugify
from .quota import Quota

log = get_logger("whatsapp")

INDICE_FILE = "_INDICE.txt"
CUOTA_FILE = SENT_DIR / "cuota_whatsapp.json"


def _archivo(lead: Lead) -> Path:
    # Nombre estable por lead.id: no depende del score ni de nada que pueda
    # cambiar entre corridas, así nunca queda un archivo viejo huérfano.
    return WHATSAPP_DIR / f"{slugify(lead.id, max_len=60)}.txt"


def _contenido(lead: Lead) -> str:
    borrador = lead.email_draft
    auditoria = lead.audit
    if lead.rating:
        rating_txt = f"{lead.rating:.1f}".replace(".", ",")
        rating_txt += f" en Maps ({lead.resenas} reseñas)" if lead.resenas else " en Maps"
    else:
        rating_txt = "sin dato"
    adjunto = borrador.adjunto or "(sin captura)"
    numero = para_whatsapp(lead)
    return (
        f"NEGOCIO:   {lead.etiqueta}\n"
        f"TELÉFONO:  +{numero.e164} · {numero.etiqueta}\n"
        f"RATING:    {rating_txt}\n"
        f"SCORE:     {auditoria.score if auditoria else '?'}/100 ({auditoria.veredicto if auditoria else '?'})\n"
        f"IMAGEN:    {adjunto}\n"
        f"LARGO:     {len(borrador.cuerpo.split())} palabras · {len(borrador.cuerpo)} caracteres\n"
        f"{'─' * 60}\n"
        f"{borrador.cuerpo}\n"
    )


def _limpiar_huerfanos(vigentes: set[str]) -> None:
    """Borra .txt de leads que ya no califican (p. ej. un re-audit bajó el
    score bajo el umbral). Sin esto, un lead descartado se queda en la
    carpeta como si todavía estuviera listo para contactar."""
    if not WHATSAPP_DIR.exists():
        return
    for archivo in WHATSAPP_DIR.glob("*.txt"):
        if archivo.name != INDICE_FILE and archivo.name not in vigentes:
            archivo.unlink()


# ─────────────────────────────── Cola ───────────────────────────────

def cola_pendiente(leads: list[Lead], cfg: Settings = settings) -> list[Lead]:
    """Leads listos para escribir por WhatsApp, ordenados por oportunidad.

    Aplica la lista de supresión, que este canal ignoraba por completo: quien
    pidió que no le escriban lo pidió para todos los canales, no solo para el
    correo.
    """
    suprimidos = load_suppression()

    def esta_suprimido(lead: Lead) -> bool:
        candidatos = {(lead.telefono or "").strip().lower(), lead.id.lower()}
        candidatos |= {c.lower() for c in lead.emails}
        return bool(candidatos & suprimidos)

    listos = [
        lead for lead in leads
        if lead.estado == "listo_whatsapp" and lead.email_draft
        and not esta_suprimido(lead)
        and para_whatsapp(lead, cfg.whatsapp.country_code)
    ]
    # Primero la confianza del número, después el score. Un lead de 100/100 al
    # que no se le puede escribir vale menos que uno de 80 con el WhatsApp
    # publicado en su propia web: el orden de la cola es una decisión
    # económica cuando hay tope diario.
    listos.sort(key=lambda l: (
        -para_whatsapp(l, cfg.whatsapp.country_code).confianza,
        -(l.audit.score if l.audit else 0),
    ))
    return listos


def cuota(cfg: Settings = settings) -> Quota:
    return Quota(cfg.whatsapp, CUOTA_FILE)


# ─────────────────────────────── Registro ───────────────────────────────

def registrar_envio(lead: Lead) -> None:
    """Deja rastro del contacto: sin esto no hay forma de medir el canal.

    Se guarda `message_id` no porque WhatsApp lo dé, sino para que el formato
    del registro sea el mismo que el del correo y `stats` pueda leer los dos.
    """
    registro = read_json(WHATSAPP_SENT_FILE, []) or []
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if any(entrada.get("id") == lead.id for entrada in registro):
        return  # idempotente: reenviar no duplica la fila
    registro.append({
        "id": lead.id,
        "nombre": lead.nombre,
        "telefono": lead.telefono,
        "url": lead.url,
        "nicho": lead.nicho,
        "score": lead.audit.score if lead.audit else None,
        "veredicto": lead.audit.veredicto if lead.audit else None,
        "palabras": len(lead.email_draft.cuerpo.split()) if lead.email_draft else 0,
        "con_imagen": bool(lead.email_draft and lead.email_draft.adjunto),
        "toque": 1,
        "enviado_el": ahora,
    })
    write_json(WHATSAPP_SENT_FILE, registro)
    lead.estado = "enviado_whatsapp"
    lead.canal = "whatsapp"
    lead.enviado_el = ahora


def ya_enviados() -> set[str]:
    return {e.get("id") for e in (read_json(WHATSAPP_SENT_FILE, []) or []) if e.get("id")}


# ─────────────────────────────── Volcado ───────────────────────────────

def exportar(leads: list[Lead], cfg: Settings = settings) -> list[Lead]:
    """Escribe un .txt por lead listo para WhatsApp más un índice ordenado
    por score. Idempotente: se reescribe todo en cada corrida a partir del
    estado actual, así el índice nunca queda desactualizado."""
    listos = cola_pendiente(leads, cfg)
    _limpiar_huerfanos({_archivo(l).name for l in listos})
    if not listos:
        (WHATSAPP_DIR / INDICE_FILE).unlink(missing_ok=True)
        return leads

    WHATSAPP_DIR.mkdir(parents=True, exist_ok=True)
    tope = cfg.whatsapp.daily_cap
    lineas = [
        "ÍNDICE — ordenado por oportunidad (score de auditoría)",
        "✓wa = WhatsApp publicado en su web · ok = celular · ? = línea fija, puede no tener WhatsApp",
        "Copiá el texto del archivo y pegalo en WhatsApp Web al teléfono indicado,",
        f"o usá `py scripts/send_whatsapp.py`. Tope diario sugerido: {tope} mensajes.",
        "=" * 70,
        "",
    ]
    for i, lead in enumerate(listos, 1):
        ruta = _archivo(lead)
        ruta.write_text(_contenido(lead), encoding="utf-8")
        score = lead.audit.score if lead.audit else 0
        numero = para_whatsapp(lead, cfg.whatsapp.country_code)
        marca = {3: "✓wa", 2: " ok", 1: " ? "}.get(numero.confianza, "   ")
        corte = "  ← tope diario" if i == tope else ""
        lineas.append(f"{marca} {score:>3}/100  {lead.etiqueta[:36]:<36} "
                      f"+{numero.e164:<15} {ruta.name}{corte}")

    (WHATSAPP_DIR / INDICE_FILE).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    log.info("WhatsApp: %d mensajes listos en %s (tope diario %d)", len(listos), WHATSAPP_DIR, tope)
    return leads
