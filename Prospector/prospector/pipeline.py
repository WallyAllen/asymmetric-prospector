"""Las cuatro etapas, encadenables y reanudables.

Todas leen y escriben el mismo almacén por etapa, fusionando por `lead.id`.
Se puede cortar la ejecución en cualquier punto y retomarla sin duplicar trabajo.
"""
from __future__ import annotations

import asyncio

from .audit import auditar
from .compose import redactar_todos, redactar_whatsapp
from .config import (AUDITED_FILE, COMPOSED_FILE, RAW_FILE, Settings, ensure_dirs, settings)
from .deliver import enviar, exportar_whatsapp
from .logging_setup import get_logger
from .models import Lead
from .sources import enrich_contacts, mine_google_maps, mine_search_engine
from .storage import load_leads, merge_leads, save_leads

log = get_logger("pipeline")


def _resumen(leads: list[Lead], titulo: str) -> None:
    conteo: dict[str, int] = {}
    for lead in leads:
        conteo[lead.estado] = conteo.get(lead.estado, 0) + 1
    detalle = ", ".join(f"{v} {k}" for k, v in sorted(conteo.items()))
    log.info("%s → %d leads (%s)", titulo, len(leads), detalle or "sin estados")


# ─────────────────────────────── Etapa 1 ───────────────────────────────

def minar(query: str, cfg: Settings = settings, fuente: str = "maps", enriquecer: bool | None = None) -> list[Lead]:
    ensure_dirs()
    if fuente == "buscador":
        nuevos = mine_search_engine(query, cfg.mining)
    else:
        nuevos = asyncio.run(mine_google_maps(query, cfg.mining))
        if not nuevos:
            log.warning("Maps no devolvió nada; probando con el buscador como respaldo")
            nuevos = mine_search_engine(query, cfg.mining)

    if not cfg.mining.include_without_site:
        nuevos = [lead for lead in nuevos if lead.url]

    quiere_enriquecer = cfg.mining.fetch_contacts if enriquecer is None else enriquecer
    if quiere_enriquecer:
        # Guardar los leads que ya llegaron ANTES de enriquecer,
        # así si se interrumpe el enriquecimiento no se pierde nada.
        leads_pre = merge_leads(load_leads(RAW_FILE), nuevos)
        save_leads(RAW_FILE, leads_pre)

        async def _guardar_progreso(leads_actuales: list) -> None:
            """Persiste el estado tras procesar cada lead individualmente."""
            save_leads(RAW_FILE, merge_leads(load_leads(RAW_FILE), leads_actuales))

        nuevos = asyncio.run(
            enrich_contacts(nuevos, cfg.mining, on_lead_done=_guardar_progreso)
        )

    leads = merge_leads(load_leads(RAW_FILE), nuevos)
    save_leads(RAW_FILE, leads)
    _resumen(leads, "Minado")
    con_email = sum(1 for lead in leads if lead.contactable)
    sin_web = sum(1 for lead in leads if not lead.url)
    log.info("  %d con email · %d sin web (los de mayor valor)", con_email, sin_web)
    return leads


def enriquecer_contactos(cfg: Settings = settings) -> list[Lead]:
    """Segunda pasada de contacto sobre lo ya minado."""
    ensure_dirs()
    leads = load_leads(RAW_FILE)

    async def _guardar_progreso(leads_actuales: list) -> None:
        # Sin esto, si el proceso se corta a mitad de camino (Ctrl+C, timeout,
        # corte de red) se pierde CADA email ya encontrado hasta ese momento.
        save_leads(RAW_FILE, merge_leads(load_leads(RAW_FILE), leads_actuales))

    asyncio.run(enrich_contacts(leads, cfg.mining, on_lead_done=_guardar_progreso))
    save_leads(RAW_FILE, leads)
    _resumen(leads, "Enriquecido")
    return leads


# ─────────────────────────────── Etapa 2 ───────────────────────────────

def auditar_leads(cfg: Settings = settings, forzar: bool = False, limite: int | None = None) -> list[Lead]:
    ensure_dirs()
    crudos = load_leads(RAW_FILE)
    auditados = load_leads(AUDITED_FILE)
    leads = merge_leads(auditados, crudos)

    # Preservamos el trabajo previo: merge_leads da prioridad al lead ya auditado.
    objetivo = leads if limite is None else leads[:limite]
    asyncio.run(auditar(objetivo, cfg, forzar=forzar))

    save_leads(AUDITED_FILE, leads)
    _resumen(leads, "Auditoría")
    calificados = [l for l in leads if l.estado == "auditado" and l.audit]
    if calificados:
        mejor = max(calificados, key=lambda l: l.audit.score)
        log.info("  Mejor oportunidad: %s (score %d)", mejor.etiqueta, mejor.audit.score)
    return leads


# ─────────────────────────────── Etapa 3 ───────────────────────────────

def redactar_correos(cfg: Settings = settings, forzar: bool = False) -> list[Lead]:
    ensure_dirs()
    leads = merge_leads(load_leads(COMPOSED_FILE), load_leads(AUDITED_FILE))
    redactar_todos(leads, cfg, forzar=forzar)
    redactar_whatsapp(leads, cfg, forzar=forzar)
    exportar_whatsapp(leads)
    save_leads(COMPOSED_FILE, leads)
    _resumen(leads, "Redacción")
    return leads


# ─────────────────────────────── Etapa 4 ───────────────────────────────

def enviar_correos(cfg: Settings = settings, simular: bool = True, limite: int | None = None) -> list[Lead]:
    ensure_dirs()
    leads = load_leads(COMPOSED_FILE)
    enviar(leads, cfg, simular=simular, limite=limite)
    save_leads(COMPOSED_FILE, leads)
    return leads


# ─────────────────────────────── Todo seguido ───────────────────────────────

def ejecutar_todo(
    query: str,
    cfg: Settings = settings,
    fuente: str = "maps",
    simular: bool = True,
    limite_envio: int | None = None,
) -> list[Lead]:
    log.info("═══ Prospección completa para: %s ═══", query)
    minar(query, cfg, fuente=fuente)
    auditar_leads(cfg)
    redactar_correos(cfg)
    return enviar_correos(cfg, simular=simular, limite=limite_envio)
