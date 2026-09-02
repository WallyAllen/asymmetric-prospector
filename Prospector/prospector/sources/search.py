"""Fuente de respaldo: buscador web, ya filtrado de directorios.

Sirve cuando Maps bloquea o cuando el nicho vive fuera de Maps (B2B, SaaS local).
A diferencia de la versión anterior, aquí se descartan agregadores, se deduplica
por dominio registrable y se recorren varias páginas de resultados.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from ..logging_setup import get_logger
from ..models import Lead
from ..utils import is_directory, normalize_url, registrable_domain

log = get_logger("buscador")

ENDPOINT = "https://lite.duckduckgo.com/lite/"


def _unwrap(href: str) -> str:
    """DuckDuckGo envuelve enlaces en /l/?uddg=<url>."""
    if "duckduckgo.com/l/" in href or href.startswith("//duckduckgo.com/l/"):
        query = parse_qs(urlparse("https:" + href if href.startswith("//") else href).query)
        destino = query.get("uddg", [""])[0]
        return destino or href
    return href


def mine_search_engine(query: str, cfg, paginas: int = 2) -> list[Lead]:
    from scrapling.fetchers import Fetcher

    encontrados: dict[str, Lead] = {}
    for pagina in range(paginas):
        data = {"q": query, "s": str(pagina * 30), "kl": "es-es"}
        try:
            respuesta = Fetcher.post(ENDPOINT, data=data)
        except Exception as exc:  # noqa: BLE001
            log.error("El buscador falló en la página %d: %s", pagina + 1, exc)
            break

        for href in respuesta.css("a::attr(href)").getall():
            url = normalize_url(_unwrap(href or ""))
            if not url or is_directory(url):
                continue
            dominio = registrable_domain(url)
            if not dominio or dominio in encontrados:
                continue
            # Nos quedamos con la home: es lo que auditaremos.
            home = f"https://{dominio}"
            encontrados[dominio] = Lead(
                nombre=dominio, url=home, nicho=query, fuente="buscador"
            )
            if len(encontrados) >= cfg.max_leads:
                break
        if len(encontrados) >= cfg.max_leads:
            break

    log.info("Buscador: %d dominios de negocio (directorios descartados)", len(encontrados))
    return list(encontrados.values())
