"""Envío SMTP sigiloso, reanudable y a prueba de meteduras de pata.

Diferencias clave con la versión anterior:
  · No mantiene la conexión SMTP abierta durante las esperas largas (se caía).
  · Cuota diaria persistente y ventana horaria laborable.
  · Modo simulación por defecto: nada sale hasta que lo pides explícitamente.
  · Multipart HTML + texto plano con la captura embebida (se ve sin descargar).
  · Lista de supresión y registro idempotente por lead.
"""
from __future__ import annotations

import mimetypes
import random
import smtplib
import ssl
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from ..config import SENT_DIR, SENT_FILE, MailSettings, Settings
from ..logging_setup import get_logger
from ..models import Lead
from ..storage import add_to_suppression, load_suppression, read_json, to_absolute, write_json
from ..utils import registrable_domain
from .quota import Quota

log = get_logger("cartero")

QUOTA_FILE = SENT_DIR / "cuota_diaria.json"

HTML_WRAPPER = """\
<html><body style="margin:0;padding:0;background:#ffffff;">
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
            font-size:15px;line-height:1.55;color:#1a1a1a;max-width:560px;">
{cuerpo}
{imagen}
</div></body></html>"""


def _texto_a_html(texto: str) -> str:
    from html import escape

    parrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    return "".join(
        f'<p style="margin:0 0 14px 0;">{escape(p).replace(chr(10), "<br>")}</p>' for p in parrafos
    )


def construir_mensaje(lead: Lead, cfg: MailSettings) -> EmailMessage:
    borrador = lead.email_draft
    if borrador is None:
        raise ValueError(f"{lead.etiqueta} no tiene correo redactado")

    mensaje = EmailMessage()
    mensaje["Subject"] = borrador.asunto
    mensaje["From"] = formataddr((cfg.from_name, cfg.user))
    mensaje["To"] = lead.email
    mensaje["Message-ID"] = make_msgid(domain=(cfg.user.split("@")[-1] or "localhost"))
    if cfg.reply_to:
        mensaje["Reply-To"] = cfg.reply_to
    mensaje["X-Entity-Ref-ID"] = lead.id

    # Texto plano primero: es lo que ven los clientes que bloquean HTML.
    mensaje.set_content(borrador.cuerpo)

    adjunto = to_absolute(borrador.adjunto)
    bloque_imagen = ""
    cid = None
    if adjunto and adjunto.exists():
        cid = make_msgid()[1:-1]
        bloque_imagen = (
            f'<p style="margin:18px 0 0 0;"><img src="cid:{cid}" '
            f'style="max-width:100%;border:1px solid #e4e4e4;border-radius:6px;" '
            f'alt="Captura de la web con la zona señalada"></p>'
        )

    mensaje.add_alternative(
        HTML_WRAPPER.format(cuerpo=_texto_a_html(borrador.cuerpo), imagen=bloque_imagen),
        subtype="html",
    )

    if adjunto and adjunto.exists() and cid:
        tipo, _ = mimetypes.guess_type(adjunto.name)
        maintype, subtype = (tipo or "image/png").split("/", 1)
        parte_html = mensaje.get_payload()[-1]
        parte_html.add_related(
            adjunto.read_bytes(), maintype=maintype, subtype=subtype, cid=f"<{cid}>",
            filename=f"analisis-{registrable_domain(lead.url) or lead.id}.png",
        )
    return mensaje


def _conectar(cfg: MailSettings) -> smtplib.SMTP:
    contexto = ssl.create_default_context()
    if cfg.port == 465:
        servidor: smtplib.SMTP = smtplib.SMTP_SSL(cfg.server, cfg.port, context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(cfg.server, cfg.port, timeout=30)
        servidor.ehlo()
        servidor.starttls(context=contexto)
        servidor.ehlo()
    servidor.login(cfg.user, cfg.password)
    return servidor


def _previsualizar(lead: Lead) -> None:
    borrador = lead.email_draft
    adjunto = to_absolute(borrador.adjunto if borrador else None)
    score = lead.audit.score if lead.audit else "?"
    print("\n" + "─" * 74)
    print(f"Para:    {lead.email}  ({lead.etiqueta} · score {score}/100)")
    print(f"Asunto:  {borrador.asunto}")
    print(f"Adjunto: {adjunto.name if adjunto else '(ninguno)'}")
    print("─" * 74)
    print(borrador.cuerpo)


def _claves_enviadas(registro: list[dict]) -> set[str]:
    """IDs y, como red de seguridad, emails de envíos previos.

    Los registros del script anterior (antes de este paquete) no tienen
    campo 'id': si solo comparásemos por id, esos envíos no protegerían
    contra un reenvío duplicado. Se indexa por las dos claves.
    """
    claves: set[str] = set()
    for item in registro:
        if item.get("id"):
            claves.add(item["id"])
        if item.get("email"):
            claves.add(item["email"].strip().lower())
    return claves


def cola_pendiente(leads: list[Lead]) -> list[Lead]:
    """Leads listos, no enviados y no suprimidos, ordenados por oportunidad."""
    registro = read_json(SENT_FILE, [])
    ya_enviados = _claves_enviadas(registro)
    supresion = load_suppression()
    cola = [
        lead for lead in leads
        if lead.estado == "listo" and lead.email_draft and lead.contactable
        and lead.id not in ya_enviados
        and (lead.email or "").lower() not in ya_enviados
        and (lead.email or "").lower() not in supresion
        and registrable_domain(lead.url) not in supresion
    ]
    return sorted(cola, key=lambda l: -(l.audit.score if l.audit else 0))


def enviar(leads: list[Lead], cfg: Settings, simular: bool = True, limite: int | None = None) -> list[Lead]:
    """Procesa la cola. `simular=True` (por defecto) no envía nada real."""
    correo = cfg.mail
    cola = cola_pendiente(leads)
    if not cola:
        log.info("No hay correos pendientes en la cola")
        return leads

    cuota = Quota(correo, QUOTA_FILE)

    if simular:
        tope = min(len(cola), limite or len(cola))
        log.info("SIMULANDO %d de %d correos en cola", tope, len(cola))
        for lead in cola[:tope]:
            _previsualizar(lead)
        print()
        log.info("Simulación terminada. Para enviar de verdad añade --enviar-de-verdad")
        return leads

    disponible, motivo = cuota.en_ventana()
    if not disponible:
        log.warning("Envío detenido: %s", motivo)
        return leads
    if not correo.user or not correo.password:
        log.error("Faltan SMTP_USER y SMTP_PASSWORD (usa una contraseña de aplicación)")
        return leads

    tope = min(len(cola), cuota.restantes, limite or len(cola))
    if tope <= 0:
        log.warning("Cuota diaria agotada (%d/%d hoy)", cuota.enviados_hoy, correo.daily_cap)
        return leads

    log.info("Enviando %d de %d correos (cuota restante hoy: %d)", tope, len(cola), cuota.restantes)
    registro = read_json(SENT_FILE, [])

    for indice, lead in enumerate(cola[:tope]):
        disponible, motivo = cuota.en_ventana()
        if not disponible:
            log.warning("Pausa: %s. La cola se conserva, retómala más tarde.", motivo)
            break

        try:
            mensaje = construir_mensaje(lead, correo)
        except Exception as exc:  # noqa: BLE001
            log.error("No se pudo construir el correo de %s: %s", lead.etiqueta, exc)
            continue

        try:
            # Se conecta y desconecta por correo: una sesión SMTP abierta durante
            # las pausas largas se cae, y ese fallo antes tumbaba toda la tanda.
            servidor = _conectar(correo)
            servidor.send_message(mensaje)
            servidor.quit()
        except smtplib.SMTPRecipientsRefused:
            log.error("Dirección rechazada: %s (va a la lista de supresión)", lead.email)
            add_to_suppression(lead.email, "destinatario rechazado")
            lead.estado = "rebotado"
            continue
        except smtplib.SMTPAuthenticationError as exc:
            log.error("Autenticación SMTP rechazada, no sigo: %s", exc)
            break
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo al enviar a %s: %s", lead.email, exc)
            continue

        lead.estado = "enviado"
        lead.enviado_el = datetime.now().isoformat(timespec="seconds")
        registro.append({
            "id": lead.id,
            "nombre": lead.nombre,
            "email": lead.email,
            "url": lead.url,
            "asunto": lead.email_draft.asunto,
            "score": lead.audit.score if lead.audit else None,
            "enviado_el": lead.enviado_el,
        })
        write_json(SENT_FILE, registro)
        cuota.anotar()
        log.info("✉ %s (%s) · %d/%d hoy", lead.etiqueta, lead.email,
                 cuota.enviados_hoy, correo.daily_cap)

        if indice < tope - 1:
            espera = random.randint(correo.jitter_min_s, correo.jitter_max_s)
            log.info("  Pausa de %dm %02ds antes del siguiente", espera // 60, espera % 60)
            time.sleep(espera)

    return leads
