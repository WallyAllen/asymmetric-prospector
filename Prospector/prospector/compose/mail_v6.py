"""Mail v6 para todos los rubros (specs 010–012).

El formato formal es el que trajo las dos señas: responde menos que el WhatsApp
corto, pero las charlas llegan más lejos. Cuerpo de la v5 (una falla que el
prospecto comprueba abriendo su web, una consecuencia de inmobiliaria) y firma
completa sin la credencial académica. Sin adjunto: las capturas anotadas traen
dibujado el hallazgo de la auditoría vieja.
"""
from __future__ import annotations

from datetime import date

from ..audit.sistema import perfil_sistema
from ..models import EmailDraft, Lead
from .lexicon import (CIERRE_INACCESIBLE, CIERRE_MAIL_V6, CONSECUENCIA_INMOBILIARIA,
                      GENERICO, NOMBRE_SISTEMA, OBSERVACION, OFERTA, PROPIEDADES_MAIL_V6, PRESENTACIONES_MAIL_V6, QUE_HAGO_MAIL_V6, REPUTACION_MAIL_V6,
                      SALUDOS_MAIL_V6, VERBO, VERBO_CELU, elegir, rubro_de)
from .whatsapp import OFERTAS_CON_WEB, MAX_DIAS_AUDITORIA, _auditoria_vieja, _segundos, estilo_felipe, hallazgo_generico, regla_toque1
from .writer import asunto_para, dominio_de, limpiar, reputacion, validar

VERSION_MAIL = "plantilla-mail-v6"


def firma_v6(cfg, oficio="webs para inmobiliarias") -> str:
    lineas = [cfg.sender_name, oficio[0].upper() + oficio[1:], cfg.sender_site, cfg.sender_phone]
    return "\n".join(l for l in lineas if l)


def componer_mail_v6(lead: Lead, cfg) -> EmailDraft:
    rubro = rubro_de(lead.nicho, nombre=lead.nombre)
    oficio = "páginas web" if rubro is GENERICO else f"webs para {rubro.plural}"
    principal = regla_toque1(lead)
    regla = principal.rule_id
    d = dominio_de(lead)
    campos = dict(d=d, s=_segundos(lead),
                  v=elegir(VERBO, lead.id, "verbo").format(d=d),
                  vc=elegir(VERBO_CELU, lead.id, "verbo").format(d=d))
    saludo = elegir(SALUDOS_MAIL_V6, lead.id, "saludo_mail")
    presentacion = elegir(PRESENTACIONES_MAIL_V6, lead.id, "presentacion_mail").format(nombre=cfg.sender_name.split()[0], oficio=oficio)
    rep = reputacion(lead) if ((lead.resenas or 0) >= 30 and (lead.rating or 0) >= 4.5) else ""
    linea_rep = elegir(REPUTACION_MAIL_V6, lead.id, "rep_mail").format(rep=rep) if rep else ""
    observacion = elegir(OBSERVACION[regla], lead.id, "observacion").format(**campos)
    consecuencia = elegir(CONSECUENCIA_INMOBILIARIA[regla], lead.id, "consecuencia")
    hallazgo = " ".join(x for x in (observacion, consecuencia) if x)
    if not _es_inmobiliaria(lead):
        hallazgo = hallazgo_generico(lead, principal)
    sistema = ""
    if regla == "sitio_inaccesible":
        bloques = [f"{saludo} {presentacion}", hallazgo,
                   elegir(CIERRE_INACCESIBLE, lead.id, "cierre_mail")]
    else:
        oferta = (elegir(OFERTA[regla], lead.id, "oferta_wa") if _es_inmobiliaria(lead)
                  else elegir(OFERTAS_CON_WEB, lead.id, "oferta_wa"))
        if _es_inmobiliaria(lead):
            # Spec 012: con CRM nombra el suyo; sin saberlo, una frase cierta en los dos casos.
            medido = lead.audit.metrics.sistema_web if lead.audit else None
            linea = elegir(PROPIEDADES_MAIL_V6[perfil_sistema(medido)], lead.id, "propiedades")
            oferta = f"{linea.format(sistema=NOMBRE_SISTEMA.get(medido, ''))} {oferta}"
            sistema = medido or "no_medido"
        bloques = [f"{saludo} {presentacion}", " ".join(x for x in (linea_rep, hallazgo) if x),
                   *([elegir(QUE_HAGO_MAIL_V6, lead.id, "que_hago")] if _es_inmobiliaria(lead) else []),
                   f"{oferta} {elegir(CIERRE_MAIL_V6, lead.id, 'cierre_mail')}"]
    cuerpo = "\n\n".join(bloques) + "\n\n" + firma_v6(cfg, oficio)
    return EmailDraft(asunto=estilo_felipe(asunto_para(lead, principal)),
                      cuerpo=estilo_felipe(limpiar(cuerpo)), generado_por=VERSION_MAIL,
                      regla=regla, sistema=sistema)


def _es_inmobiliaria(lead: Lead) -> bool:
    return rubro_de(lead.nicho, nombre=lead.nombre).plural == "inmobiliarias"


def redactar_mail_v6(leads, cfg, forzar: bool = False, hoy: date | None = None):
    """Negocios con email y web: mismas puertas que el toque 1 de WhatsApp (009)."""
    hoy = hoy or date.today()
    for lead in leads:
        if not (lead.contactable and lead.url
                and lead.estado in {"auditado", "listo"}):
            continue
        if not forzar and lead.email_draft and lead.email_draft.generado_por == VERSION_MAIL:
            continue
        # Un `auditado` CON borrador es una retención a mano (la página «No soy bot»,
        # las afirmaciones de riesgo de Zona Norte): se libera pasándolo a `listo`.
        if lead.estado == "auditado" and lead.email_draft is not None:
            continue
        if _auditoria_vieja(lead, hoy):
            lead.email_draft, lead.estado = None, "auditado"
            lead.motivo_descarte = (f"auditoría de más de {MAX_DIAS_AUDITORIA} días: "
                                    "re-auditar antes de redactar")
            continue
        http = lead.audit.metrics.http_status if lead.audit else None
        if http and http >= 400:
            lead.email_draft, lead.estado = None, "revisar_web"
            lead.motivo_descarte = f"la web respondió HTTP {http} al auditor: revisar a mano"
            continue
        if regla_toque1(lead) is None:
            lead.email_draft, lead.estado = None, "descartado"
            lead.motivo_descarte = "sin falla verificable para toque 1"
            continue
        lead.email_draft = componer_mail_v6(lead, cfg.compose)
        lead.email_draft.variante = "formal"
        lead.estado, lead.motivo_descarte = "listo", None
    return leads
