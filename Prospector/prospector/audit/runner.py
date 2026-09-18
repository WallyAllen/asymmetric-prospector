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
from .capture import anotar, anotar_overflow_movil
from .signals import ProbeResult, SiteProbe
from .vision import a_finding, juzgar

# Cada cuántos leads terminados se persiste el avance. 10 es un compromiso:
# guardar en cada uno reescribe un JSON de 3 MB cientos de veces.
_CADA = 10

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

    icono = {"critico": "✖", "inaccesible": "⚠", "mejorable": "•", "sano": "✓",
             "no_medido": "?"}.get(veredicto, "•")
    log.info(
        "%s %s · score %d/100 (%s) → %s",
        icono, lead.etiqueta, score, veredicto, rules.resumen(hallazgos) or "sin defectos relevantes",
    )
    if veredicto == "no_medido":
        lead.estado = "descartado"
        lead.motivo_descarte = f"no se pudo medir: {res.error or 'sin detalle'}"
    elif score < cfg.audit.min_score:
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
        ruta, dibujados = resultado
        auditoria.capturas["anotada"] = to_relative(ruta) or ""
        if dibujados > 0:
            auditoria.captura_marcada = True

    hallazgos_movil = [h for h in prioridad if h.viewport == "mobile"]
    if hallazgos_movil:
        principal_movil = hallazgos_movil[0]
        destino_movil = SHOTS_DIR / _slug(lead) / "anotada-movil.png"
        resultado_movil = None

        # El desborde horizontal no se puede probar con la captura de
        # viewport (recorta justo lo que se sale): si es el hallazgo que
        # lidera el argumento móvil, se usa la captura full_page en su lugar.
        origen_full = res.capturas.get("mobile_full")
        if principal_movil.rule_id == "overflow_mobile" and origen_full and Path(origen_full).exists():
            resultado_movil = anotar_overflow_movil(
                Path(origen_full), destino_movil, principal_movil, pie=principal_movil.argumento,
            )

        if resultado_movil is None:
            movil = res.capturas.get("mobile_fold")
            if movil and Path(movil).exists():
                resultado_movil = anotar(
                    Path(movil), destino_movil, hallazgos_movil, movil=True,
                    pie=principal_movil.argumento,
                )

        if resultado_movil:
            ruta_movil, dibujados_movil = resultado_movil
            auditoria.capturas["anotada_movil"] = to_relative(ruta_movil) or ""
            if dibujados_movil > 0:
                auditoria.captura_marcada = True

    # La captura que se adjunta al correo es la que ilustra el hallazgo principal:
    # si el defecto más grave es de móvil, se manda la del móvil.
    principal = auditoria.capturas.get("anotada")
    if prioridad and prioridad[0].viewport == "mobile" and auditoria.capturas.get("anotada_movil"):
        principal = auditoria.capturas["anotada_movil"]
    if principal:
        auditoria.capturas["principal"] = principal

    # Eliminar capturas originales duplicadas para ahorrar espacio
    for clave, ruta_abs in res.capturas.items():
        if clave not in ("anotada", "anotada_movil", "principal"):
            try:
                Path(ruta_abs).unlink(missing_ok=True)
                if clave in auditoria.capturas:
                    del auditoria.capturas[clave]
            except Exception:
                pass


async def auditar(leads: list[Lead], cfg: Settings, forzar: bool = False,
                  solo_veredicto: str | None = None, reanudar: bool = False,
                  on_progreso=None) -> list[Lead]:
    """Audita los leads pendientes. Idempotente: no repite trabajo ya hecho.

    `solo_veredicto` re-mide únicamente los que quedaron con ese veredicto.
    Sirve para volver sobre los "inaccesible" y los "no_medido" sin rehacer
    una tanda de una hora: son los dos grupos que un tropiezo de red puede
    haber marcado mal, y de los que no conviene fiarse sin una segunda mirada.

    `reanudar` retoma una tanda cortada: salta los que ya se midieron en la
    corrida más reciente y sigue por los que quedaron con auditoría vieja.

    `on_progreso` se llama cada `_CADA` leads terminados. Antes no existía y
    la función guardaba recién al final: un Ctrl+C a los cuarenta minutos
    tiraba los cuarenta minutos, y encima el mensaje de salida decía "el
    progreso quedó guardado", que para esta etapa era falso.
    """
    from ..utils import is_directory

    if solo_veredicto:
        pendientes = [l for l in leads if l.audit and l.audit.veredicto == solo_veredicto]
        log.info("Re-midiendo %d leads con veredicto «%s»", len(pendientes), solo_veredicto)
    elif reanudar:
        # "Ya medido en esta tanda" = su auditoría es del mismo día que la más
        # nueva del archivo. Lo demás quedó pendiente cuando se cortó.
        fechas = [l.audit.auditado_el for l in leads if l.audit and l.audit.auditado_el]
        corte = max(fechas)[:10] if fechas else ""
        pendientes = [
            l for l in leads
            if not (l.audit and (l.audit.auditado_el or "")[:10] == corte)
        ]
        log.info("Reanudando: %d ya medidos el %s, quedan %d",
                 len(leads) - len(pendientes), corte or "?", len(pendientes))
    else:
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
    terminados = 0

    async def procesar(lead: Lead, probe: SiteProbe) -> None:
        """Mide y aplica el resultado de UN lead, sin esperar a los demás.

        Antes se esperaba a que terminaran todos y recién ahí se aplicaban los
        resultados en un segundo bucle. Así, un lead terminado ya queda
        resuelto en memoria y el guardado periódico lo persiste.
        """
        nonlocal terminados
        async with semaforo:
            res = await probe.probe(lead.url, slug=_slug(lead))
        # Un lead que vuelve a medirse sale del descarte si ahora califica.
        if lead.estado == "descartado" and (solo_veredicto or reanudar):
            lead.estado = "auditado"
            lead.motivo_descarte = None
        _aplicar_resultado(lead, res, cfg)
        # El jurado y Pillow son síncronos: se ejecutan fuera del navegador.
        await asyncio.to_thread(_jurado_y_anotacion, lead, res, cfg)
        terminados += 1
        if on_progreso and terminados % _CADA == 0:
            await asyncio.to_thread(on_progreso, leads)
            log.info("   …%d/%d medidos · guardado", terminados, len(con_web))

    async with SiteProbe(cfg.audit) as probe:
        try:
            await asyncio.gather(*(procesar(l, probe) for l in con_web),
                                 return_exceptions=True)
        finally:
            # Ctrl+C incluido: lo medido hasta acá se guarda igual.
            if on_progreso:
                await asyncio.to_thread(on_progreso, leads)
    log.info("Auditoría terminada: %d/%d medidos", terminados, len(con_web))
    return leads
