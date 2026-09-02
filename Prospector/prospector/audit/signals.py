"""Recolección de señales objetivas con Playwright.

Nada de opiniones aquí: solo se miden hechos (milisegundos, kilobytes, número
de CTAs, desbordes). La interpretación vive en `rules.py`.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import DESKTOP_VIEWPORT, MOBILE_UA, MOBILE_VIEWPORT, SHOTS_DIR, AuditSettings
from ..logging_setup import get_logger
from ..models import Metrics
from ..utils import registrable_domain, slugify
from .probe_js import AUDIT_JS, WEB_VITALS_INIT_JS

log = get_logger("señales")


@dataclass(slots=True)
class ProbeResult:
    url_final: str | None = None
    metrics: Metrics = field(default_factory=Metrics)
    desktop: dict[str, Any] = field(default_factory=dict)
    mobile: dict[str, Any] = field(default_factory=dict)
    capturas: dict[str, Path] = field(default_factory=dict)
    ok: bool = False
    error: str | None = None


class SiteProbe:
    """Un único navegador reutilizado para toda la tanda: mucho más rápido."""

    def __init__(self, cfg: AuditSettings) -> None:
        self.cfg = cfg
        self._pw = None
        self._browser = None

    async def __aenter__(self) -> "SiteProbe":
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.cfg.headless,
            args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def _new_context(self, mobile: bool):
        kwargs: dict[str, Any] = {
            "locale": "es-ES",
            "timezone_id": "Europe/Madrid",
            "ignore_https_errors": True,
        }
        if mobile:
            kwargs.update(
                viewport=MOBILE_VIEWPORT,
                user_agent=MOBILE_UA,
                is_mobile=True,
                has_touch=True,
                device_scale_factor=2,
            )
        else:
            kwargs.update(viewport=DESKTOP_VIEWPORT, device_scale_factor=1)
        context = await self._browser.new_context(**kwargs)
        context.set_default_timeout(self.cfg.nav_timeout_ms)
        await context.add_init_script(WEB_VITALS_INIT_JS)
        return context

    async def probe(self, url: str, slug: str | None = None) -> ProbeResult:
        resultado = ProbeResult()
        carpeta = SHOTS_DIR / (slug or slugify(registrable_domain(url) or url))
        carpeta.mkdir(parents=True, exist_ok=True)

        try:
            await self._probe_desktop(url, resultado, carpeta)
        except Exception as exc:  # noqa: BLE001 - un sitio caído es un dato, no un crash
            resultado.error = f"{type(exc).__name__}: {exc}"
            resultado.metrics.error = resultado.error
            log.warning("No se pudo auditar %s (%s)", url, resultado.error)
            return resultado

        try:
            await self._probe_mobile(resultado.url_final or url, resultado, carpeta)
        except Exception as exc:  # noqa: BLE001 - sin móvil seguimos con lo de escritorio
            log.debug("Auditoría móvil incompleta en %s: %s", url, exc)

        resultado.ok = True
        _consolidar(resultado)
        return resultado

    async def _probe_desktop(self, url: str, res: ProbeResult, carpeta: Path) -> None:
        context = await self._new_context(mobile=False)
        page = await context.new_page()
        bytes_totales = {"n": 0, "peticiones": 0, "imagenes": 0}

        def on_response(response):
            bytes_totales["peticiones"] += 1
            try:
                largo = int(response.headers.get("content-length") or 0)
            except (TypeError, ValueError):
                largo = 0
            bytes_totales["n"] += largo
            tipo = (response.headers.get("content-type") or "").lower()
            if tipo.startswith("image/"):
                bytes_totales["imagenes"] += largo

        page.on("response", on_response)

        inicio = time.perf_counter()
        respuesta = await page.goto(url, wait_until="domcontentloaded", timeout=self.cfg.nav_timeout_ms)
        try:
            await page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:  # noqa: BLE001 - webs con polling nunca quedan "idle"
            pass
        transcurrido = (time.perf_counter() - inicio) * 1000

        res.url_final = page.url
        res.metrics.http_status = respuesta.status if respuesta else None
        res.metrics.https = page.url.startswith("https://")
        if respuesta and respuesta.url != url:
            res.metrics.redirected_to = respuesta.url

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
        await page.wait_for_timeout(600)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(400)

        res.desktop = await page.evaluate(AUDIT_JS)
        vitals = await page.evaluate("() => window.__vitals || {}")

        res.metrics.load_ms = round(transcurrido, 1)
        timing = res.desktop.get("timing") or {}
        res.metrics.dom_ready_ms = _redondear(timing.get("domReady"))
        res.metrics.ttfb_ms = _redondear(timing.get("ttfb"))
        res.metrics.lcp_ms = _redondear(vitals.get("lcp"))
        res.metrics.cls = round(float(vitals.get("cls") or 0), 3)
        res.metrics.peso_kb = round(bytes_totales["n"] / 1024, 1) or None
        res.metrics.peticiones = bytes_totales["peticiones"] or None
        res.metrics.imagenes_pesadas_kb = round(bytes_totales["imagenes"] / 1024, 1) or None

        fold = carpeta / "desktop-fold.png"
        await page.screenshot(path=str(fold))
        res.capturas["desktop_fold"] = fold
        try:
            completa = carpeta / "desktop-full.png"
            await page.screenshot(path=str(completa), full_page=True)
            res.capturas["desktop_full"] = completa
        except Exception:  # noqa: BLE001 - páginas gigantes pueden reventar la captura
            pass

        await context.close()

    async def _probe_mobile(self, url: str, res: ProbeResult, carpeta: Path) -> None:
        context = await self._new_context(mobile=True)
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=self.cfg.nav_timeout_ms)
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:  # noqa: BLE001
            pass
        await page.wait_for_timeout(600)
        res.mobile = await page.evaluate(AUDIT_JS)

        fold = carpeta / "mobile-fold.png"
        await page.screenshot(path=str(fold))
        res.capturas["mobile_fold"] = fold
        await context.close()


def _redondear(valor) -> float | None:
    try:
        return round(float(valor), 1) if valor else None
    except (TypeError, ValueError):
        return None


def _consolidar(res: ProbeResult) -> None:
    """Vuelca el JS crudo en el modelo Metrics, cruzando escritorio y móvil."""
    d, m = res.desktop or {}, res.mobile or {}
    met = res.metrics
    met.tiene_viewport_meta = d.get("tieneViewportMeta")
    met.h1 = d.get("h1")
    met.title = d.get("title")
    met.meta_description = d.get("metaDescription")
    met.og_image = d.get("ogImage")
    met.favicon = d.get("favicon")
    met.imagenes_sin_alt = d.get("imagenesSinAlt")
    met.palabras_en_fold = d.get("palabrasEnFold")
    met.ctas_en_fold = d.get("ctasEnFold")
    met.tiene_formulario = bool(d.get("formularios"))
    met.tiene_tel = bool(d.get("telLinks"))
    met.tiene_whatsapp = bool(d.get("whatsapp"))
    met.generador = d.get("generador")
    met.ano_copyright = d.get("anoCopyright")
    met.popup_intrusivo = bool(d.get("popupIntrusivo"))
    met.items_menu = d.get("itemsMenu")
    met.tels_unicos = d.get("telsUnicos")
    met.emails_unicos = d.get("emailsUnicos")
    met.titulo_parece_directorio = bool(d.get("tituloDirectorio"))
    if m:
        # Sin meta viewport el móvil abre un lienzo virtual de ~1000px, así que
        # innerWidth ya viene inflado y el desborde no se detecta comparando
        # contra él: hay que medirlo contra el ancho real del teléfono.
        ancho_real = MOBILE_VIEWPORT["width"]
        ancho_scroll = m.get("anchoScroll") or 0
        met.overflow_horizontal_mobile = bool(
            m.get("overflowHorizontal") or ancho_scroll > ancho_real * 1.05
        )
        met.ancho_scroll_mobile = m.get("anchoScroll")
        met.texto_pequeno_mobile = m.get("textoPequeno")
        met.tap_targets_pequenos = m.get("tapPequenos")


async def probe_many(urls: list[str], cfg: AuditSettings) -> dict[str, ProbeResult]:
    """Audita varias URLs con concurrencia limitada."""
    resultados: dict[str, ProbeResult] = {}
    semaforo = asyncio.Semaphore(max(1, cfg.concurrency))

    async with SiteProbe(cfg) as probe:
        async def tarea(url: str) -> None:
            async with semaforo:
                resultados[url] = await probe.probe(url)

        await asyncio.gather(*(tarea(u) for u in urls), return_exceptions=True)
    return resultados
