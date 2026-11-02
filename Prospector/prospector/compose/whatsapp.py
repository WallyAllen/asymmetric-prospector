"""Redacción nativa de WhatsApp.

Hasta ahora este canal no tenía redactor: `scripts/send_whatsapp.py` metía
`lead.email_draft.cuerpo` —el cuerpo del correo, tal cual— en un `wa.me`.
Medido sobre los 251 mensajes en cola, eso significaba mandar al celular de un
desconocido: 704 caracteres de mediana (máximo 1.151), cinco párrafos, el
enlace de LinkedIn en los 251, el teléfono propio en los 251 (a alguien que ya
lo está viendo en el encabezado del chat) y un saludo en plural seguido de un
cuerpo en singular.

En correo eso cuesta tasa de respuesta. Acá cuesta el número: un enlace en el
primer mensaje de un remitente no agendado, repetido palabra por palabra a
cientos de destinatarios, es la definición operativa de spam para la
plataforma. Y el 73% de este segmento no tiene web, así que tampoco hay
captura que adjuntar: el argumento tiene que sostenerse solo con el texto.

Formato del canal, cuatro movimientos y menos de 95 palabras:

    1 · quién sos, en seis palabras          → baja la alarma del número raro
    2 · qué viste, concreto y verificable    → el hallazgo medido
    3 · qué le cuesta, en su vocabulario     → la consecuencia, UNA vez
    4 · una pregunta de bajo compromiso      → sin enlace, sin firma

La captura, cuando existe, se manda como imagen aparte (lo hace
`scripts/send_whatsapp.py`) y el texto no la menciona: así funciona sola si la
imagen no llega, y no hay forma de prometer una marca que no está.
"""
from __future__ import annotations

from datetime import date

from ..config import ComposeSettings
from ..logging_setup import get_logger
from ..models import EmailDraft, Finding, Lead
from ..utils import dialecto_por_url
from .lexicon import (CIERRE, CIERRE_INACCESIBLE, CONSECUENCIA_INMOBILIARIA, GENERICO,
                      IDENTIDAD_V6, OBSERVACION, OFERTA, PRESENTACIONES_V5, SALUDOS_V5, VERBO,
                      VERBO_CELU, busqueda_de, elegir, rubro_de)
from .writer import (dominio_de, enlace_corto, frase_prueba, limpiar, mayuscula_inicial,
                     minuscula_inicial, reputacion, validar)

log = get_logger("whatsapp-redactor")

VERSION = "plantilla-whatsapp-v6"

# Spec 010. La mitad de las inmobiliarias recibe el LinkedIn en el primer bloque:
# los dos que pagaron seña habían recibido nombre completo, LinkedIn y teléfono.
VARIANTES_V6 = ("corta", "identidad")



# Spec 009. Solo lidera lo que el prospecto comprueba abriendo su web. Quedan
# afuera el LCP de 2,5 a 4 s (no se nota), el texto chico y los tap targets
# (hay que medirlos), y `sin_cta_fold`: en una inmobiliaria el buscador hace de
# botón, el auditor no lo cuenta, y "no hay ningún botón" puede ser falso.
REGLAS_TOQUE1 = ("carga_lenta", "sin_contacto", "sin_tel_movil", "overflow_mobile",
                 "sin_viewport", "popup_intrusivo", "sitio_inaccesible")

# El mensaje afirma algo que el prospecto comprueba hoy. Al 26/10, 135 de las
# 244 inmobiliarias con web de la cola tenían la auditoría de hace 21-27 días:
# un "no cargó" de hace tres semanas puede ser falso, y quema el contacto.
MAX_DIAS_AUDITORIA = 14

_SIN_TILDE = str.maketrans("áéíóúÁÉÍÓÚüÜ", "aeiouAEIOUuU", "¿¡")


def estilo_felipe(texto: str) -> str:
    """Sin tildes y sin «¿» ni «¡», como escribe Felipe en el celular. La ñ queda."""
    return texto.translate(_SIN_TILDE)


def regla_toque1(lead: Lead) -> Finding | None:
    """El primer hallazgo argumentable que se comprueba abriendo la web."""
    for hallazgo in (lead.audit.argumentables if lead.audit else []):
        if hallazgo.rule_id not in REGLAS_TOQUE1:
            continue
        if hallazgo.rule_id == "carga_lenta" and hallazgo.categoria != "killer":
            continue
        return hallazgo
    return None


def _auditoria_vieja(lead: Lead, hoy: date) -> bool:
    try:
        auditado = date.fromisoformat((lead.audit.auditado_el or "")[:10])
    except (AttributeError, ValueError):
        return True
    return (hoy - auditado).days > MAX_DIAS_AUDITORIA


SALUDOS = (
    "Hola, ¿qué tal?",
    "Hola, buenas.",
    "Hola, ¿cómo va?",
)

# La presentación reemplaza a la firma. `sender_role` no sirve acá: trae el
# cargo largo y la credencial académica que la regla 4 del PROMPT prohíbe
# expresamente ("la autoridad la dan el hallazgo medido y la evidencia, no un
# título"), y en WhatsApp además suena a estudiante buscando práctica.
PRESENTACIONES = (
    "Soy {nombre}, {pitch}.",
    "Soy {nombre} y {pitch}.",
    "Te escribo por algo puntual. Soy {nombre}, {pitch}.",
)

CIERRES_CON_BOCETO = (
    "¿Te lo paso?",
    "¿Querés que te lo mande?",
    "Si te sirve te lo paso y lo mirás. ¿Va?",
    "¿Te lo mando y lo ves con calma?",
    "Si querés te lo paso, sin compromiso.",
)

# La misma oración cerraba los 312 mensajes sin web. En correo eso cuesta
# reputación de dominio; acá lo busca el detector de spam de la plataforma, y
# lo detecta el prospecto cuando se lo cruza con el del negocio de al lado.
FUGAS_SIN_WEB = (
    "{Cliente} ve la ficha, no encuentra cómo {accion} y termina en la del de al lado.",
    "{Cliente} entra a la ficha, no ve cómo {accion} y se va al siguiente resultado.",
    "El que quiere {accion} no tiene dónde hacerlo, y ese cliente se lo lleva el de al lado.",
    "{Cliente} mira la ficha, no encuentra cómo {accion}, y prueba con el próximo de la lista.",
)

OFERTAS_CON_WEB = (
    "Te armo un boceto de cómo quedaría esa portada, sin cargo.",
    "Puedo armarte un boceto de esa pantalla arreglada para que la veas.",
    "Te hago un boceto de cómo se vería ordenada y te lo muestro.",
)

OFERTAS_SIN_WEB = (
    "Te armo un boceto de una página de una sola pantalla para que lo veas.",
    "Puedo armarte un boceto de cómo se vería una página simple tuya.",
    "Te hago un boceto de una página de una pantalla y te lo muestro.",
)

APERTURAS_SIN_WEB = (
    "Te encontré en Maps buscando {busqueda}",
    "Estaba buscando {busqueda} y llegué a tu ficha de Maps",
    "Buscando {busqueda} di con tu ficha en Maps",
)

APERTURAS_CON_WEB = (
    "Entré a {dominio} buscando {busqueda} y vi que",
    "Estaba buscando {busqueda}, llegué a {dominio} y noté que",
    "Buscando {busqueda} caí en {dominio}. Vi que",
)


def _presentacion(lead: Lead, cfg: ComposeSettings, plural: str | None = None) -> str:
    # Con rubro reconocido, la presentación nombra el rubro ("hago webs para
    # inmobiliarias") en vez del pitch configurado, que en la v4 decía "webs y
    # sistemas" y abría la puerta al "ya tenemos sistema".
    if plural:
        marco = elegir(PRESENTACIONES_V5, lead.id, "presentacion")
        return marco.format(nombre=cfg.sender_name, plural=plural)
    pitch = (cfg.sender_pitch or "armo páginas web").strip().rstrip(".")
    marco = elegir(PRESENTACIONES, lead.id, "presentacion")
    return marco.format(nombre=cfg.sender_name, pitch=pitch, Pitch=mayuscula_inicial(pitch))


def _segundos(lead: Lead) -> str:
    lcp = (lead.audit.metrics.lcp_ms or 0) / 1000 if lead.audit else 0
    return f"{lcp:.1f}".replace(".", ",")


def hallazgo_generico(lead: Lead, principal: Finding | None) -> str:
    rubro = rubro_de(lead.nicho, nombre=lead.nombre)
    dominio, busqueda = dominio_de(lead), busqueda_de(lead.nicho)
    if rubro is GENERICO:
        busqueda = "tu negocio"
    if principal and principal.rule_id == "sitio_inaccesible":
        return (f"Quise entrar a {dominio} buscando {busqueda} y no cargó, probé dos veces. "
                "El que te busca y se encuentra con eso no vuelve a probar: entra al siguiente resultado.")
    apertura = elegir(APERTURAS_CON_WEB, lead.id, "apertura_wa").format(
        dominio=dominio, busqueda=busqueda)
    observacion = minuscula_inicial(principal.observacion if principal else "").rstrip(".")
    # Un hallazgo de una auditoría vieja trae la consecuencia dentro de la
    # observación: agregarle otra la diría dos veces en 73 palabras.
    consecuencia = "" if (principal and principal.legado) else (
        (principal.consecuencia if principal else "")
        or f"{rubro.cliente} se va sin {rubro.accion}"
    )
    cuerpo_medio = f"{apertura} {observacion}."
    if consecuencia:
        cuerpo_medio += f" {mayuscula_inicial(consecuencia).rstrip('.')}."
    return cuerpo_medio


def componer_whatsapp(lead: Lead, cfg: ComposeSettings) -> EmailDraft:
    """Un mensaje pensado para el celular del dueño, no un correo reenviado.

    Con web, tres bloques: quién sos · la falla medida y UNA consecuencia ·
    el boceto de esa falla arreglada y una pregunta que se contesta con sí o no.
    Quien llama decide antes si hay falla que contar (`regla_toque1`).
    """
    rubro = rubro_de(lead.nicho, nombre=lead.nombre)
    busqueda = busqueda_de(lead.nicho)
    dominio = dominio_de(lead)
    dialecto = dialecto_por_url(lead.url)
    principal = regla_toque1(lead) if lead.url else None
    regla = principal.rule_id if principal else ("sin_web" if not lead.url else "")
    inaccesible = regla == "sitio_inaccesible"
    inmobiliaria = rubro.plural == "inmobiliarias"
    prueba = frase_prueba(cfg)

    plural = rubro.plural if (lead.url and rubro is not GENERICO) else None
    saludos = SALUDOS_V5 if plural else SALUDOS
    variante = elegir(VARIANTES_V6, lead.id, "variante_v6") if (inmobiliaria and cfg.sender_site) else "corta"
    if variante == "identidad":
        cabecera = f"{elegir(saludos, lead.id, 'saludo_wa')} {_presentacion(lead, cfg, plural)} " + \
            elegir(IDENTIDAD_V6, lead.id, "identidad").format(enlace=enlace_corto(cfg.sender_site))
    else:
        cabecera = f"{elegir(saludos, lead.id, 'saludo_wa')} {_presentacion(lead, cfg, plural)}"
    cierre = elegir(CIERRE if lead.url else CIERRES_CON_BOCETO, lead.id, "cierre_wa")

    if not lead.url:
        rep = reputacion(lead)
        apertura = elegir(APERTURAS_SIN_WEB, lead.id, "apertura_wa").format(busqueda=busqueda)
        dato = f": {rep} y sin web enlazada." if rep else " y vi que no tenés web enlazada."
        fuga = elegir(FUGAS_SIN_WEB, lead.id, "fuga").format(
            Cliente=mayuscula_inicial(rubro.cliente), accion=rubro.accion)
        cuerpo_medio = f"{apertura}{dato} {fuga}"
        oferta = ("Te armo un boceto de un catálogo con prendas, talles y pedidos para revisar en WhatsApp."
                  if rubro.plural == "tiendas de ropa" else elegir(OFERTAS_SIN_WEB, lead.id, "oferta_wa"))
    elif inmobiliaria and principal:
        campos = dict(d=dominio, s=_segundos(lead),
                      v=elegir(VERBO, lead.id, "verbo").format(d=dominio),
                      vc=elegir(VERBO_CELU, lead.id, "verbo").format(d=dominio))
        observacion = elegir(OBSERVACION[regla], lead.id, "observacion").format(**campos)
        consecuencia = elegir(CONSECUENCIA_INMOBILIARIA[regla], lead.id, "consecuencia")
        cuerpo_medio = f"{observacion} {consecuencia}"
        if inaccesible:
            oferta, cierre = "", elegir(CIERRE_INACCESIBLE, lead.id, "cierre_wa")
        else:
            oferta = elegir(OFERTA[regla], lead.id, "oferta_wa")
    elif inaccesible:
        cuerpo_medio = hallazgo_generico(lead, principal)
        oferta, cierre = "Si querés te paso exactamente qué error me apareció.", "¿Te sirve?"
    else:
        cuerpo_medio = hallazgo_generico(lead, principal)
        oferta = ("Puedo mostrarte un boceto para facilitar la elección de prendas y el pedido."
                  if rubro.plural == "tiendas de ropa" else elegir(OFERTAS_CON_WEB, lead.id, "oferta_wa"))

    bloques = [cabecera, cuerpo_medio]
    if prueba:
        bloques.append(prueba)
    bloques.append(f"{oferta} {cierre}".strip())

    # Sin firma, sin enlace, sin asunto: el nombre y el número ya están en el
    # encabezado del chat, y el asunto no se manda por este canal (el .txt lo
    # imprimía como "gancho de referencia", o sea: trabajo tirado).
    cuerpo = estilo_felipe(limpiar("\n\n".join(b for b in bloques if b), dialecto))
    return EmailDraft(asunto="", cuerpo=cuerpo, generado_por=VERSION, regla=regla, variante=variante)


def redactar_whatsapp(leads: list[Lead], cfg, forzar: bool = False,
                      hoy: date | None = None) -> list[Lead]:
    """Redacta el segmento sin email pero con teléfono.

    Se guarda en `lead.email_draft` porque es el único campo de borrador que
    tiene el modelo, pero el texto NO es un correo: `generado_por` lo marca
    como WhatsApp para que `lint` y `stats` puedan separarlos.

    Recompone todo borrador de una versión anterior (la v4 de la cola) y nunca
    toca un lead enviado o respondido: el filtro de estado los deja afuera.
    """
    hoy = hoy or date.today()
    candidatos = [
        lead for lead in leads
        if lead.estado in {"auditado", "listo_whatsapp"}
        and (forzar or lead.email_draft is None
             or lead.email_draft.generado_por != VERSION
             # Re-auditada después de redactar: el borrador afirma lo que medía
             # la auditoría anterior (un "no cargó" sobre una web que ya carga).
             or bool(lead.audit and lead.audit.auditado_el > lead.email_draft.redactado_el))
        # Un lead con email que ya está en `listo_whatsapp` se pasó a este canal
        # a propósito: 13 inmobiliarias v4 quedaban sin recomponer por tener email.
        and (not lead.contactable or lead.estado == "listo_whatsapp") and lead.telefono
    ]
    rechazados = viejas = sin_falla = revisar = 0
    for lead in candidatos:
        if lead.url and _auditoria_vieja(lead, hoy):
            viejas += 1
            lead.email_draft, lead.estado = None, "auditado"
            lead.motivo_descarte = (f"auditoría de más de {MAX_DIAS_AUDITORIA} días: "
                                    "re-auditar antes de redactar")
            continue
        estado_http = lead.audit.metrics.http_status if (lead.url and lead.audit) else None
        if estado_http and estado_http >= 400:
            # 5 de las 20 "caídas" de la cola del 26/10 eran un 403 o un 500 con
            # contenido: casi siempre un bloqueo de bots que una persona no ve.
            # "No cargó" sería falso, y el resto se midió sobre la página de error.
            revisar += 1
            lead.email_draft, lead.estado = None, "revisar_web"
            lead.motivo_descarte = f"la web respondió HTTP {estado_http} al auditor: revisar a mano"
            continue
        if lead.url and regla_toque1(lead) is None:
            sin_falla += 1
            lead.email_draft, lead.estado = None, "descartado"
            lead.motivo_descarte = "sin falla verificable para toque 1"
            continue
        borrador = componer_whatsapp(lead, cfg.compose)
        problemas = validar(borrador, canal="whatsapp", dominio_propio=dominio_de(lead),
                            enlace_propio=enlace_corto(cfg.compose.sender_site))
        if problemas:
            rechazados += 1
            log.warning("WhatsApp con problemas para %s (%s)", lead.etiqueta, ", ".join(problemas))
        lead.email_draft = borrador
        lead.estado = "listo_whatsapp"
        lead.motivo_descarte = None
        log.info("✎ %s (WhatsApp, %s) · %d palabras",
                 lead.etiqueta, lead.telefono, len(borrador.cuerpo.split()))
    if viejas:
        log.warning("%d leads con auditoría de más de %d días: re-auditar con «audit --forzar»",
                    viejas, MAX_DIAS_AUDITORIA)
    if revisar:
        log.warning("%d leads a revisar_web: la web respondió con error HTTP al auditor", revisar)
    if sin_falla:
        log.info("%d leads descartados por no tener una falla verificable para el toque 1", sin_falla)
    if rechazados:
        log.warning("%d/%d mensajes de WhatsApp no pasan la validación del canal",
                    rechazados, len(candidatos))
    return leads
