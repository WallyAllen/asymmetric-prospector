"""Utilidades transversales: normalización de URLs, dominios, emails, texto."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Iterable
from urllib.parse import urlparse, urlunparse

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4}")

# Portales, agregadores y directorios: nunca son el cliente final.
DIRECTORY_DOMAINS = {
    "yelp.com", "yelp.es", "tripadvisor.com", "tripadvisor.es", "paginasamarillas.es",
    "cylex.es", "cylex.com", "lawzana.com", "rankingabogados.es", "abogado.org",
    "doctoralia.es", "doctoralia.com", "milanuncios.com", "indeed.com", "glassdoor.com",
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "youtube.com", "pinterest.com", "wikipedia.org", "google.com", "goo.gl", "maps.app.goo.gl",
    "booking.com", "airbnb.com", "amazon.com", "ebay.com", "mercadolibre.com",
    "empresite.eleconomista.es", "axesor.es", "infoempresa.com", "einforma.com",
    "qdq.com", "11870.com", "hotfrog.es", "solofarma.com", "trustpilot.com",
    "bing.com", "duckduckgo.com", "yahoo.com", "reddit.com", "medium.com",
    "wa.me", "whatsapp.com", "t.me", "linktr.ee",
    # Directorios argentinos conocidos
    "contadoresya.com.ar", "cercademi.ar", "infoisinfo-ar.com", "redargentina.com.ar",
    "paginasamarillas.com.ar", "guiaurbana.com.ar", "guiaoleo.com.ar", "dondeir.com",
    "vivendo.com.ar", "turismoentrerios.com", "directorio.com.ar",
}

# Palabras en el dominio que delatan un directorio/agregador.
_DIRECTORY_DOMAIN_KEYWORDS = (
    "directorio", "guia", "guía", "amarillas", "cercademi", "buscador",
    "encuentra", "listado", "ranking", "infoisinfo", "redargentina",
    "dondeir", "vivendo", "hotfrog", "cylex", "yelp",
)

# Patrón /nicho/ciudad en la URL: indica una página de categoría dentro de un directorio.
_DIRECTORY_PATH_RE = re.compile(
    r"/(?:contadores?|abogados?|medicos?|dentistas?|clinicas?|psicologos?|"
    r"arquitectos?|ingenieros?|plomeros?|electricistas?|fontaneros?|"
    r"notarios?|escribanos?|veterinarios?|kinesio|fisio|nutricionistas?|"
    r"estudios?-contables?|estudios?-juridicos?)/",
    re.I,
)

# Marcadores de que el "sitio" es en realidad un perfil dentro de otra plataforma.
PLATFORM_MARKERS = ("business.site", "negocio.site", "sites.google.com", "wixsite.com/",
                    "myshopify.com", "square.site", "linktr.ee")

# Emails genéricos de plataformas / basura que la regex atrapa.
EMAIL_BLOCKLIST_DOMAINS = {
    "sentry.io", "example.com", "domain.com", "email.com", "wixpress.com",
    "godaddy.com", "wordpress.org", "sentry-next.wixpress.com", "your-domain.com",
}
EMAIL_BLOCKLIST_PREFIXES = ("noreply", "no-reply", "donotreply", "postmaster", "mailer-daemon")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico")


def normalize_url(url: str | None) -> str | None:
    """Devuelve una URL canónica (https, sin fragmentos ni parámetros de tracking)."""
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if not parsed.netloc:
        return None
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, netloc, path, "", "", ""))


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    try:
        netloc = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    except ValueError:
        return ""
    return netloc[4:] if netloc.startswith("www.") else netloc


def registrable_domain(url: str | None) -> str:
    """Aproximación al dominio registrable (suficiente para deduplicar)."""
    host = domain_of(url)
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # Maneja sufijos compuestos habituales: co.uk, com.ar, com.es...
    if parts[-2] in {"co", "com", "org", "net", "gob", "gov", "edu"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_directory(url: str | None) -> bool:
    """True si la URL pertenece a un directorio/agregador y no a un negocio.

    Tres capas de detección:
    1. Lista fija de dominios conocidos.
    2. Palabras clave en el dominio (guia, directorio, amarillas...).
    3. Patrón /nicho/ciudad en la ruta (indica categoría de directorio).
    """
    if not url:
        return False
    host = registrable_domain(url)
    if host in DIRECTORY_DOMAINS:
        return True
    # Heurística por palabras clave en el dominio
    host_lower = host.lower()
    if any(kw in host_lower for kw in _DIRECTORY_DOMAIN_KEYWORDS):
        return True
    # Heurística por patrón /nicho/ciudad en la ruta
    if _DIRECTORY_PATH_RE.search(url):
        return True
    return any(marker in (url or "").lower() for marker in PLATFORM_MARKERS)


def is_platform_profile(url: str | None) -> bool:
    """Web hospedada en un constructor gratuito: casi siempre 'sin landing real'."""
    return any(marker in (url or "").lower() for marker in PLATFORM_MARKERS)


def clean_emails(candidates: Iterable[str]) -> list[str]:
    """Filtra falsos positivos y ordena poniendo primero los buzones útiles."""
    seen: dict[str, None] = {}
    for raw in candidates:
        email = raw.strip().strip(".,;:()<>[]\"'").lower()
        if not EMAIL_RE.fullmatch(email):
            continue
        if email.endswith(IMAGE_SUFFIXES):
            continue
        local, _, host = email.partition("@")
        if host in EMAIL_BLOCKLIST_DOMAINS or local.startswith(EMAIL_BLOCKLIST_PREFIXES):
            continue
        if len(local) > 64 or len(email) > 254:
            continue
        if re.fullmatch(r"[0-9a-f]{16,}", local):  # hashes de tracking
            continue
        seen.setdefault(email, None)

    preferred = ("info", "contacto", "hola", "contact", "comercial", "administracion", "cita")

    def rank(email: str) -> tuple[int, int]:
        local = email.split("@", 1)[0]
        return (0 if local.startswith(preferred) else 1, len(email))

    return sorted(seen, key=rank)


def clean_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.count("+") > 1:
        digits = "+" + digits.replace("+", "")
    return digits if 7 <= len(re.sub(r"\D", "", digits)) <= 15 else None


def slugify(value: str, max_len: int = 60) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = re.sub(r"[^\w\s\-.]", "", value).strip().lower()
    value = re.sub(r"[\s_]+", "-", value)
    return (value[:max_len] or "sin-nombre").strip("-.")


def lead_id(url: str | None, name: str = "", email: str | None = None) -> str:
    """Identificador estable: dominio si lo hay, si no nombre+email hasheados."""
    host = registrable_domain(url)
    if host:
        return host
    seed = f"{name}|{email or ''}".lower()
    return f"noweb-{slugify(name, 32)}-{hashlib.sha1(seed.encode()).hexdigest()[:8]}"


def dialecto_por_url(url: str | None) -> str:
    """'voseo' (rioplatense, vos) por defecto; 'tuteo' solo para dominios .es.

    Sender y plantillas son de Argentina, así que rioplatense es el default
    razonable cuando no se puede inferir el país (sin URL, TLD genérico).
    Solo se detecta explícitamente el caso peninsular porque fue el que se
    coló mezclado con leads argentinos en la primera corrida.
    """
    host = registrable_domain(url)
    if host.endswith(".es") or host == "es":
        return "tuteo"
    return "voseo"


def truncate(text: str, limit: int = 280) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
