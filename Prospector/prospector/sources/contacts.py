"""Enriquecimiento de contacto: encontrar el correo real del negocio.

Estrategia en capas, de la más barata a la más cara:
  1. HTML crudo (mailto:, texto plano, JSON-LD).
  2. Páginas típicas de contacto/aviso legal (donde el email casi siempre está).
  3. Desofuscación de patrones "nombre (arroba) dominio (punto) com".
"""
from __future__ import annotations

import asyncio
import html
import json
import re
from urllib.parse import urljoin

from ..logging_setup import get_logger
from ..models import Lead
from ..utils import EMAIL_RE, clean_emails, clean_phone, domain_of

log = get_logger("contactos")

CONTACT_PATHS = (
    "/contacto", "/contact", "/contactanos", "/contacto.html", "/aviso-legal",
    "/legal", "/privacidad", "/politica-de-privacidad", "/quienes-somos", "/about",
)
CONTACT_LINK_XPATH = (
    "//a[contains(translate(., 'CONTAOLEGIVPRDAD', 'contaolegivprdad'), 'contact')"
    " or contains(translate(., 'AVISOLEGAL', 'avisolegal'), 'legal')"
    " or contains(translate(., 'PRIVACIDAD', 'privacidad'), 'privacidad')]/@href"
)

_DEOBFUSCATE = [
    (re.compile(r"\s*\(\s*(?:arroba|at)\s*\)\s*", re.I), "@"),
    (re.compile(r"\s*\[\s*(?:arroba|at)\s*\]\s*", re.I), "@"),
    (re.compile(r"\s+(?:arroba|at)\s+", re.I), "@"),
    (re.compile(r"\s*\(\s*(?:punto|dot)\s*\)\s*", re.I), "."),
    (re.compile(r"\s*\[\s*(?:punto|dot)\s*\]\s*", re.I), "."),
    (re.compile(r"\s+(?:punto|dot)\s+", re.I), "."),
]


def _extract_emails(raw_html: str) -> list[str]:
    texto = html.unescape(raw_html or "")
    candidatos = set(EMAIL_RE.findall(texto))

    # mailto: incluidos los codificados en entidades o con parámetros.
    for match in re.findall(r"mailto:([^\"'?>\s]+)", texto, re.I):
        candidatos.add(match)

    # JSON-LD (schema.org) suele traer el email oficial del negocio.
    for bloque in re.findall(
        r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', texto, re.S | re.I
    ):
        try:
            data = json.loads(bloque.strip())
        except (json.JSONDecodeError, ValueError):
            candidatos.update(EMAIL_RE.findall(bloque))
            continue
        pila = [data]
        while pila:
            nodo = pila.pop()
            if isinstance(nodo, dict):
                if isinstance(nodo.get("email"), str):
                    candidatos.add(nodo["email"].replace("mailto:", ""))
                pila.extend(nodo.values())
            elif isinstance(nodo, list):
                pila.extend(nodo)

    # Desofuscación: "hola (arroba) negocio (punto) com"
    ofuscado = texto
    for patron, reemplazo in _DEOBFUSCATE:
        ofuscado = patron.sub(reemplazo, ofuscado)
    if ofuscado != texto:
        candidatos.update(EMAIL_RE.findall(ofuscado))

    return clean_emails(candidatos)


def _extract_phone(raw_html: str) -> str | None:
    for match in re.findall(r'href="tel:([^"]+)"', raw_html or "", re.I):
        telefono = clean_phone(match)
        if telefono:
            return telefono
    return None


def _prioritize(emails: list[str], sitio: str | None) -> list[str]:
    """Prefiere correos del propio dominio antes que gmail/hotmail sueltos."""
    host = domain_of(sitio)
    if not host:
        return emails
    propios = [e for e in emails if e.endswith("@" + host) or host.split(".")[0] in e.split("@")[1]]
    ajenos = [e for e in emails if e not in propios]
    return propios + ajenos


async def enrich_contacts(
    leads: list[Lead],
    cfg,
    max_paginas: int = 3,
    on_lead_done=None,
) -> list[Lead]:
    """Visita cada web y rellena email/teléfono. Modifica los leads en sitio.

    Args:
        on_lead_done: callable opcional ``async def (leads) -> None`` que se
            invoca tras procesar cada lead. Úsalo para guardar progreso
            incremental y no perder datos si se interrumpe la ejecución.
    """
    from scrapling.fetchers import AsyncStealthySession

    from ..utils import is_directory

    # Un directorio no es un negocio: visitarlo no da un email útil y, peor,
    # es justo el tipo de sitio (mucho tráfico de bots, anti-scraping) que
    # más se cuelga. Ya está identificado en otras partes del pipeline; acá
    # nunca se chequeaba, así que enrich igual perdía tiempo en ellos.
    objetivos = [lead for lead in leads if lead.url and not lead.email and not is_directory(lead.url)]
    if not objetivos:
        return leads

    # Techo duro por lead: si un fetch individual no respeta su propio
    # timeout (pasó con un directorio real), esto evita que UN sitio
    # colgado bloquee el resto de la ronda para siempre.
    techo_s = max(60.0, (cfg.nav_timeout_ms / 1000) * (max_paginas + 1))

    log.info("Buscando correo público en %d webs", len(objetivos))
    async with AsyncStealthySession(headless=cfg.headless, humanize=False, disable_resources=True) as session:
        for lead in objetivos:
            try:
                await asyncio.wait_for(_enrich_one(session, lead, cfg, max_paginas), timeout=techo_s)
            except asyncio.TimeoutError:
                log.warning("%s: se colgó más de %.0fs, se salta", lead.url, techo_s)
            except Exception as exc:  # noqa: BLE001 - un fallo no debe tumbar la ronda
                log.debug("Sin contacto en %s: %s", lead.url, exc)
            if on_lead_done is not None:
                try:
                    await on_lead_done(leads)
                except Exception as exc:  # noqa: BLE001
                    log.debug("Error guardando progreso: %s", exc)
            await asyncio.sleep(0.5)
    return leads


async def _enrich_one(session, lead: Lead, cfg, max_paginas: int) -> None:
    pagina = await session.fetch(lead.url, timeout=cfg.nav_timeout_ms, network_idle=False)
    raw = pagina.html_content if hasattr(pagina, "html_content") else str(pagina)
    emails = _extract_emails(raw)
    telefono = _extract_phone(raw)

    if not emails:
        vistas: set[str] = set()
        candidatas: list[str] = []
        try:
            for href in pagina.xpath(CONTACT_LINK_XPATH).getall()[:4]:
                destino = urljoin(lead.url, href)
                if destino not in vistas and domain_of(destino) == domain_of(lead.url):
                    vistas.add(destino)
                    candidatas.append(destino)
        except Exception:  # noqa: BLE001
            pass
        for ruta in CONTACT_PATHS:
            destino = urljoin(lead.url, ruta)
            if destino not in vistas:
                vistas.add(destino)
                candidatas.append(destino)

        for destino in candidatas[:max_paginas]:
            try:
                sub = await session.fetch(destino, timeout=cfg.nav_timeout_ms, network_idle=False)
            except Exception:  # noqa: BLE001
                continue
            sub_raw = sub.html_content if hasattr(sub, "html_content") else str(sub)
            emails = _extract_emails(sub_raw)
            telefono = telefono or _extract_phone(sub_raw)
            if emails:
                break

    emails = _prioritize(emails, lead.url)
    if emails:
        lead.emails = emails
        lead.email = emails[0]
        log.info("  %s → %s", lead.etiqueta, lead.email)
    if telefono and not lead.telefono:
        lead.telefono = telefono
