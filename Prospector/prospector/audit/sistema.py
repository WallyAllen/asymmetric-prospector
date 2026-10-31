"""Qué usa la web del prospecto para mostrar las propiedades (spec 012).

Solo se mira lo que la página carga: dominios y rutas de sus recursos, y el
`meta generator`. Si no hay firma conocida es `sin_detectar`, que no significa
"no usa nada": desde afuera no se distingue de un CRM que no reconocemos.
"""
from __future__ import annotations

from urllib.parse import urlparse

# Sumar un CRM es una línea acá (y su nombre en `compose.lexicon.NOMBRE_SISTEMA`).
CRMS = {
    "tokko": ("tokkobroker.com",),
    "wasi": ("wasi.co",),
}
CONSTRUCTORES_POR_HOST = {
    "wix": ("wixstatic.com", "parastorage.com"),
    "squarespace": ("squarespace.com", "squarespace-cdn.com"),
    "webflow": ("website-files.com",),
}
CONSTRUCTORES_POR_RUTA = {
    "wordpress": ("/wp-content/", "/wp-includes/"),
}
GENERADORES = ("wordpress", "wix", "squarespace", "webflow")


def _es_de(host: str, dominios) -> bool:
    return any(host == d or host.endswith("." + d) for d in dominios)


def detectar_sistema(generador: str | None, recursos) -> str:
    urls = [urlparse((u or "").strip()) for u in recursos or []]
    hosts = [(u.hostname or "").lower() for u in urls]
    for nombre, dominios in CRMS.items():
        if any(_es_de(h, dominios) for h in hosts):
            return nombre
    gen = (generador or "").strip().lower()
    for nombre in GENERADORES:
        if gen.startswith(nombre) or f"{nombre}.com" in gen:
            return nombre
    for nombre, dominios in CONSTRUCTORES_POR_HOST.items():
        if any(_es_de(h, dominios) for h in hosts):
            return nombre
    rutas = [(u.path or "").lower() for u in urls]
    for nombre, marcas in CONSTRUCTORES_POR_RUTA.items():
        if any(m in r for r in rutas for m in marcas):
            return nombre
    return "sin_detectar"


def perfil_sistema(sistema: str | None) -> str:
    return "crm" if sistema in CRMS else "desconocido"
