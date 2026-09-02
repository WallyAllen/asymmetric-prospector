"""Orquestador de la auditoría: señales → reglas → jurado IA → capturas anotadas."""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..ai import get_client
from ..config import DESKTOP_VIEWPORT, SHOTS_DIR, Settings
from ..logging_setup import get_logger
from ..models import Audit, Lead
from ..storage import to_relative
from ..utils import registrable_domain, slugify
from . import rules
from .capture import anotar
from .signals import ProbeResult, SiteProbe
from .vision import a_finding, juzgar

log = get_logger("auditor")


def _slug(lead: Lead) -> str:
    return slugify(registrable_domain(lead.url) or lead.nombre or lead.id)


def _auditar_sin_web(lead: Lead) -> Lead:
    hallazgo = rules.finding_sin_web(lead.nombre or "El negocio")
    lead.audit = Audit(score=100, veredicto="sin_web", findings=[hallazgo])
    lead.estado = "auditado"
    log.info("★ %s · sin web → prospecto de máximo valor", lead.etiqueta)
    return lead


def _aplicar_resultado(lead: Lead, res: ProbeResult, cfg: Settings) -> Lead:
    score, veredicto, hallazgos = rules.evaluar(res)

    # Descarte temprano: si la regla detectó un directorio, no tiene sentido
    # calcular score ni generar argumentos de venta — no hay prospecto aquí.
    hallazgo_dir = next((h for h in hallazgos if h.rule_id == "es_directorio"), None)
    if hallazgo_dir:
        lead.audit = Audit(
            score=0,
            veredicto="directorio",
            findings=[hallazgo_dir],
            metrics=res.metrics,
            capturas={k: to_relative(v) or "" for k, v in res.capturas.items()},
        )
        lead.estado = "descartado"
        lead.motivo_descarte = f"directorio: {hallazgo_dir.evidencia}"
        log.info("⊘ %s · descartado — página directorio (%s)", lead.etiqueta, hallazgo_dir.evidencia)
        return lead

    auditoria = Audit(
        score=score,
        veredicto=veredicto,
        findings=hallazgos,
        metrics=res.metrics,
        capturas={k: to_relative(v) or "" for k, v in res.capturas.items()},
    )
    lead.audit = auditoria
    lead.estado = "auditado"

    icono = {"critico": "✖", "inaccesible": "⚠", "mejorable": "•", "sano": "✓"}.get(veredicto, "•")
    log.info(
        "%s %s · score %d/100 (%s) → %s",
        icono, lead.etiqueta, score, veredicto, rules.resumen(hallazgos) or "sin defectos relevantes",
    )
    if score < cfg.audit.min_score:
        lead.estado = "descartado"
        lead.motivo_descarte = f"score {score} por debajo del umbral {cfg.audit.min_score}"
    return lead


def _jurado_y_anotacion(lead: Lead, res: ProbeResult, cfg: Settings) -> None:
    auditoria = lead.audit
    if auditoria is None:
        return

    # 1. Jurado visual, solo para los leads que ya merecen la pena.
    if (
        cfg.audit.use_vision
        and cfg.ai.enabled
        and auditoria.score >= cfg.audit.vision_threshold
        and res.capturas
    ):
        dictamen = juzgar(
            get_client(cfg.ai),
            lead,
            auditoria.findings,
            res.capturas,
            DESKTOP_VIEWPORT["width"],
            DESKTOP_VIEWPORT["height"],
        )
        if dictamen:
            auditoria.vision = dictamen
            visual = a_finding(dictamen)
            if visual:
                auditoria.findings.append(visual)
            if dictamen.get("confirma_diagnostico") is False:
                # El jurado vio la captura y dice que la web se ve profesional
                # pese a lo medido: se pesa fuerte, porque un correo con un
                # argumento que el dueño puede refutar mirando su pantalla
                # quema el contacto para siempre.
                auditoria.score = max(0, auditoria.score - 25)
                auditoria.veredicto = next(
                    nombre for umbral, nombre in rules.VEREDICTOS if auditoria.score >= umbral
                )
                log.info("  El jurado no confirma el diagnóstico: score ajustado a %d (%s)",
                         auditoria.score, auditoria.veredicto)
                if auditoria.score < cfg.audit.min_score:
                    lead.estado = "descartado"
                    lead.motivo_descarte = "el jurado visual no confirmó los defectos medidos"

    # 2. Captura anotada: la prueba que se adjunta al correo.
    if not cfg.audit.annotate or lead.estado == "descartado":
        return
    origen = res.capturas.get("desktop_fold")
    if not origen or not Path(origen).exists():
        return

    prioridad = auditoria.argumentables or auditoria.top_findings
    pie = None
    if auditoria.vision.get("problema_visual"):
        pie = auditoria.vision["problema_visual"]
    elif prioridad:
        pie = prioridad[0].argumento

    destino = SHOTS_DIR / _slug(lead) / "anotada.png"
    resultado = anotar(Path(origen), destino, prioridad, movil=False, pie=pie)
    if resultado:
        auditoria.capturas["anotada"] = to_relative(resultado) or ""

    movil = res.capturas.get("mobile_fold")
    hallazgos_movil = [h for h in prioridad if h.viewport == "mobile"]
    if movil and hallazgos_movil and Path(movil).exists():
        destino_movil = SHOTS_DIR / _slug(lead) / "anotada-movil.png"
        resultado_movil = anotar(
            Path(movil), destino_movil, hallazgos_movil, movil=True,
            pie=hallazgos_movil[0].argumento,
        )
        if resultado_movil:
            auditoria.capturas["anotada_movil"] = to_relative(resultado_movil) or ""

    # La captura que se adjunta al correo es la que ilustra el hallazgo principal:
    # si el defecto más grave es de móvil, se manda la del móvil.
    principal = auditoria.capturas.get("anotada")
    if prioridad and prioridad[0].viewport == "mobile" and auditoria.capturas.get("anotada_movil"):
        principal = auditoria.capturas["anotada_movil"]
    if principal:
        auditoria.capturas["principal"] = principal


async def auditar(leads: list[Lead], cfg: Settings, forzar: bool = False) -> list[Lead]:
    """Audita los leads pendientes. Idempotente: no repite trabajo ya hecho."""
    from ..utils import is_directory

    pendientes = [
        lead for lead in leads
        if forzar or lead.audit is None or lead.estado == "crudo"
    ]
    if not pendientes:
        log.info("No hay leads pendientes de auditar")
        return leads

    # Descartar directorios antes de abrir el navegador: los leads que
    # entraron en corridas anteriores (antes del fix) se eliminan aquí.
    sin_web, con_web = [], []
    for lead in pendientes:
        if not lead.url:
            sin_web.append(lead)
        elif is_directory(lead.url):
            lead.estado = "descartado"
            lead.motivo_descarte = "directorio detectado en pre-auditoría"
            log.info("⊘ %s · descartado sin auditar — URL de directorio", lead.etiqueta)
        else:
            con_web.append(lead)

    for lead in sin_web:
        _auditar_sin_web(lead)

    if not con_web:
        return leads

    log.info("Auditando %d webs (concurrencia %d)", len(con_web), cfg.audit.concurrency)
    semaforo = asyncio.Semaphore(max(1, cfg.audit.concurrency))
    resultados: dict[str, ProbeResult] = {}

    async with SiteProbe(cfg.audit) as probe:
        async def tarea(lead: Lead) -> None:
            async with semaforo:
                resultados[lead.id] = await probe.probe(lead.url, slug=_slug(lead))

        await asyncio.gather(*(tarea(lead) for lead in con_web), return_exceptions=True)

    for lead in con_web:
        res = resultados.get(lead.id)
        if res is None:
            lead.estado = "descartado"
            lead.motivo_descarte = "la auditoría no pudo completarse"
            continue
        _aplicar_resultado(lead, res, cfg)
        # El jurado y Pillow son síncronos: se ejecutan fuera del navegador.
        await asyncio.to_thread(_jurado_y_anotacion, lead, res, cfg)

    return leads
