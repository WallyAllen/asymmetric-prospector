"""Minado de Google Maps con Scrapling (navegador sigiloso).

Maps es la mejor fuente para esta tesis: da negocios reales, con nombre y
teléfono, y —lo más valioso— delata a los que NO tienen web. Ese es el
prospecto perfecto: no hay nada que criticar, hay todo que construir.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import quote_plus, urlparse

from ..config import MiningSettings
from ..logging_setup import get_logger
from ..models import Lead
from ..utils import clean_phone, is_directory, normalize_url

log = get_logger("maps")

MAPS_URL = "https://www.google.com/maps/search/{query}?hl={lang}"

# El scroll del panel de resultados: Maps carga por lotes al hacer scroll.
_SCROLL_JS = """
async ([maxScrolls]) => {
  const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  const feed = document.querySelector('div[role="feed"]')
             || document.querySelector('div[aria-label][role="region"]');
  if (!feed) return 0;
  let previous = -1, stable = 0;
  for (let i = 0; i < maxScrolls; i++) {
    feed.scrollTo(0, feed.scrollHeight);
    await sleep(1400 + Math.random() * 900);
    const count = feed.querySelectorAll('a[href*="/maps/place/"]').length;
    if (count === previous) { stable++; if (stable >= 2) break; } else { stable = 0; }
    previous = count;
  }
  return previous;
}
"""

_CONSENT_SELECTORS = (
    'button[aria-label*="Aceptar todo"]',
    'button[aria-label*="Accept all"]',
    'form[action*="consent"] button',
    'button:has-text("Aceptar todo")',
    'button:has-text("Accept all")',
    'button[jsname="b3VHJd"]',   # botón "Aceptar todo" del muro de consentimiento de Google
)


def _make_page_action(cfg: MiningSettings):
    async def page_action(page):
        # 1. Muro de consentimiento (aparece según país/IP).
        for selector in _CONSENT_SELECTORS:
            try:
                boton = await page.query_selector(selector)
                if boton:
                    await boton.click()
                    await page.wait_for_timeout(1500)
                    break
            except Exception:  # noqa: BLE001 - el consentimiento es best effort
                continue
        # 2. Esperar al panel de resultados y desplegar todos los lotes.
        try:
            await page.wait_for_selector('a[href*="/maps/place/"]', timeout=cfg.nav_timeout_ms)
        except Exception:
            log.warning("Maps no devolvió tarjetas de resultado para esta consulta")
            return page
        await page.evaluate(_SCROLL_JS, [cfg.max_scrolls])
        await page.wait_for_timeout(800)
        return page

    return page_action


def _first(node, *selectors: str) -> str | None:
    for selector in selectors:
        try:
            value = node.css(selector).first
        except Exception:  # noqa: BLE001 - selector no soportado, probamos el siguiente
            continue
        if value is None:
            continue
        text = value if isinstance(value, str) else getattr(value, "text", None)
        text = (str(text) if text is not None else "").strip()
        if text:
            return text
    return None


def _parse_card(card, nicho: str) -> Lead | None:
    """Extrae un lead de una tarjeta del panel de resultados.

    El nombre se busca en varias fuentes porque Google no expone siempre la
    misma: el más fiable es el aria-label del propio enlace (lo lee un lector
    de pantalla, así que Google lo mantiene), pero se cae a su texto visible
    y a un par de clases alternativas por si esa etiqueta falta.
    """
    try:
        anchor = card.css('a[href*="/maps/place/"]').first
    except Exception:  # noqa: BLE001
        anchor = None
    if anchor is None:
        return None

    nombre = (anchor.attrib.get("aria-label") or "").strip()
    if not nombre:
        nombre = _first(
            card,
            "span.xxVWCe::text", "div.qBF1Pd::text", "div.fontHeadlineSmall::text",
        ) or ""
    if not nombre:
        texto_ancla = getattr(anchor, "text", None)
        nombre = (str(texto_ancla).strip() if texto_ancla else "")
    if not nombre:
        log.debug("Tarjeta sin nombre extraíble (posible cambio de layout de Maps): %s",
                   (anchor.attrib.get("href") or "")[:120])
        return None

    place_url = anchor.attrib.get("href")

    # La web del negocio es el único enlace de la tarjeta que no apunta a Google.
    website = None
    try:
        hrefs = [a.attrib.get("href", "") for a in card.css("a[href]")]
    except Exception:  # noqa: BLE001
        hrefs = []
    for href in hrefs:
        if not href or href.startswith("/"):
            continue
        host = urlparse(href).netloc.lower()
        if "google." in host or "gstatic" in host or not host:
            continue
        website = href
        break

    texto = " ".join((card.get_all_text() or "").split()) if hasattr(card, "get_all_text") else ""
    rating, resenas = None, None
    # El rating es más fiable por el aria-label de su propio span ("4,5 estrellas")
    # que por regex sobre el texto: Maps no siempre muestra el nº de reseñas al
    # lado, así que exigir ambos juntos (como antes) perdía el rating igual.
    try:
        estrellas = card.css('span[aria-label*="estrella"], span[aria-label*="star"]').first
    except Exception:  # noqa: BLE001
        estrellas = None
    rating_match = None
    if estrellas is not None:
        rating_match = re.search(r"([0-5][.,]\d)", estrellas.attrib.get("aria-label") or "")
    if not rating_match:
        rating_match = re.search(r"([0-5][.,]\d)\s*(?:\(|estrellas|stars|$)", texto)
    if rating_match:
        rating = float(rating_match.group(1).replace(",", "."))

    resenas_match = re.search(r"\(([\d.,]+)\)", texto)
    if resenas_match:
        try:
            resenas = int(re.sub(r"\D", "", resenas_match.group(1)))
        except ValueError:
            resenas = None

    telefono = None
    phone_match = re.search(r"(\+?\d[\d\s\-().]{7,17}\d)", texto)
    if phone_match:
        telefono = clean_phone(phone_match.group(1))

    website_norm = normalize_url(website)
    if website_norm and is_directory(website_norm):
        # Su "web" es una ficha de directorio: cuenta como no tener web propia.
        website_norm = None

    lead = Lead(
        nombre=nombre,
        url=website_norm,
        telefono=telefono,
        rating=rating,
        resenas=resenas,
        nicho=nicho,
        fuente="google_maps",
    )
    lead.direccion = None
    if place_url:
        lead.categoria = None
    return lead


def _dedupe(leads: list[Lead]) -> list[Lead]:
    vistos: dict[str, Lead] = {}
    for lead in leads:
        if lead.id not in vistos:
            vistos[lead.id] = lead
    return list(vistos.values())


async def mine_google_maps(
    query: str,
    cfg: MiningSettings,
    lang: str = "es",
) -> list[Lead]:
    """Devuelve los negocios que Google Maps lista para la consulta dada."""
    from scrapling.fetchers import AsyncStealthySession  # import perezoso: arranque rápido

    url = MAPS_URL.format(query=quote_plus(query), lang=lang)
    log.info("Minando Google Maps: %s", query)

    async with AsyncStealthySession(
        headless=cfg.headless,
        humanize=True,
        disable_resources=False,
        os_randomize=True,
    ) as session:
        try:
            page = await session.fetch(
                url,
                timeout=cfg.nav_timeout_ms,
                network_idle=False,
                load_dom=True,
                page_action=_make_page_action(cfg),
            )
        except Exception as exc:  # noqa: BLE001 - Maps puede bloquear o expirar
            log.error("Falló la carga de Google Maps: %s", exc)
            return []

    tarjetas: list[Any] = []
    for selector in ('div[role="feed"] > div', 'div[role="feed"] div.Nv2PK', "div.Nv2PK"):
        try:
            tarjetas = list(page.css(selector))
        except Exception:  # noqa: BLE001
            tarjetas = []
        if tarjetas:
            break

    if not tarjetas:
        log.warning(
            "Sin tarjetas parseables (Maps cambió el layout, hubo bloqueo por "
            "bot, o quedó atascado en el muro de consentimiento)"
        )
        return []

    leads = []
    for card in tarjetas:
        lead = _parse_card(card, query)
        if lead:
            leads.append(lead)

    descartadas = len(tarjetas) - len(leads)
    if tarjetas and descartadas / len(tarjetas) > 0.3:
        log.warning(
            "%d de %d tarjetas se descartaron sin nombre extraíble: revisar si "
            "Maps cambió el layout (activa --visible para inspeccionar)",
            descartadas, len(tarjetas),
        )

    leads = _dedupe(leads)[: cfg.max_leads]
    sin_web = sum(1 for lead in leads if not lead.url)
    sin_nombre = sum(1 for lead in leads if not lead.nombre)
    if sin_nombre:
        log.warning("%d leads quedaron sin nombre de negocio", sin_nombre)
    log.info("Maps: %d negocios (%d sin web propia)", len(leads), sin_web)
    return leads


def mine_google_maps_sync(query: str, cfg: MiningSettings, lang: str = "es") -> list[Lead]:
    return asyncio.run(mine_google_maps(query, cfg, lang))
