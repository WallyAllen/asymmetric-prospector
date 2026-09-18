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

from ..config import ComposeSettings
from ..logging_setup import get_logger
from ..models import EmailDraft, Lead
from ..utils import dialecto_por_url
from .lexicon import busqueda_de, elegir, rubro_de
from .writer import (dominio_de, frase_prueba, hallazgos_de, limpiar,
                     mayuscula_inicial, minuscula_inicial, reputacion, validar)

log = get_logger("whatsapp-redactor")

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


def _presentacion(lead: Lead, cfg: ComposeSettings) -> str:
    pitch = (cfg.sender_pitch or "armo páginas web").strip().rstrip(".")
    marco = elegir(PRESENTACIONES, lead.id, "presentacion")
    return marco.format(nombre=cfg.sender_name, pitch=pitch, Pitch=mayuscula_inicial(pitch))


def componer_whatsapp(lead: Lead, cfg: ComposeSettings) -> EmailDraft:
    """Un mensaje pensado para el celular del dueño, no un correo reenviado."""
    rubro = rubro_de(lead.nicho)
    busqueda = busqueda_de(lead.nicho)
    dominio = dominio_de(lead)
    dialecto = dialecto_por_url(lead.url)
    hallazgos = hallazgos_de(lead, 1)
    principal = hallazgos[0] if hallazgos else None
    inaccesible = bool(lead.audit and lead.audit.veredicto == "inaccesible")
    prueba = frase_prueba(cfg)

    cabecera = f"{elegir(SALUDOS, lead.id, 'saludo_wa')} {_presentacion(lead, cfg)}"

    if not lead.url:
        rep = reputacion(lead)
        apertura = elegir(APERTURAS_SIN_WEB, lead.id, "apertura_wa").format(busqueda=busqueda)
        dato = f": {rep} y sin web enlazada." if rep else " y vi que no tenés web enlazada."
        fuga = elegir(FUGAS_SIN_WEB, lead.id, "fuga").format(
            Cliente=mayuscula_inicial(rubro.cliente), accion=rubro.accion)
        cuerpo_medio = f"{apertura}{dato} {fuga}"
        oferta = elegir(OFERTAS_SIN_WEB, lead.id, "oferta_wa")
    elif inaccesible:
        cuerpo_medio = (
            f"Quise entrar a {dominio} buscando {busqueda} y no cargó, probé dos veces. "
            f"El que te busca y se encuentra con eso no vuelve a probar: entra al siguiente resultado."
        )
        oferta = "Si querés te paso exactamente qué error me apareció."
    else:
        apertura = elegir(APERTURAS_CON_WEB, lead.id, "apertura_wa").format(
            dominio=dominio, busqueda=busqueda)
        observacion = minuscula_inicial(
            principal.observacion if principal else
            "la primera pantalla no está invitando a nadie a contactarte"
        ).rstrip(".")
        # Un hallazgo de una auditoría vieja trae la consecuencia dentro de la
        # observación: agregarle otra la diría dos veces en 73 palabras.
        consecuencia = "" if (principal and principal.legado) else (
            (principal.consecuencia if principal else "")
            or f"{rubro.cliente} se va sin {rubro.accion}"
        )
        cuerpo_medio = f"{apertura} {observacion}."
        if consecuencia:
            cuerpo_medio += f" {mayuscula_inicial(consecuencia).rstrip('.')}."
        oferta = elegir(OFERTAS_CON_WEB, lead.id, "oferta_wa")

    cierre = elegir(CIERRES_CON_BOCETO, lead.id, "cierre_wa")
    if inaccesible:
        cierre = "¿Te sirve?"

    bloques = [cabecera, cuerpo_medio]
    if prueba:
        bloques.append(prueba)
    bloques.append(f"{oferta} {cierre}")

    # Sin firma, sin enlace, sin asunto: el nombre y el número ya están en el
    # encabezado del chat, y el asunto no se manda por este canal (el .txt lo
    # imprimía como "gancho de referencia", o sea: trabajo tirado).
    cuerpo = limpiar("\n\n".join(b for b in bloques if b), dialecto)
    return EmailDraft(asunto="", cuerpo=cuerpo, generado_por="plantilla-whatsapp")


def redactar_whatsapp(leads: list[Lead], cfg, forzar: bool = False) -> list[Lead]:
    """Redacta el segmento sin email pero con teléfono.

    Se guarda en `lead.email_draft` porque es el único campo de borrador que
    tiene el modelo, pero el texto NO es un correo: `generado_por` lo marca
    como "plantilla-whatsapp" para que `lint` y `stats` puedan separarlos.
    """
    candidatos = [
        lead for lead in leads
        if lead.estado in {"auditado", "listo_whatsapp"}
        and (forzar or lead.email_draft is None
             or lead.email_draft.generado_por != "plantilla-whatsapp")
        and not lead.contactable and lead.telefono
    ]
    rechazados = 0
    for lead in candidatos:
        borrador = componer_whatsapp(lead, cfg.compose)
        problemas = validar(borrador, canal="whatsapp", dominio_propio=dominio_de(lead))
        if problemas:
            rechazados += 1
            log.warning("WhatsApp con problemas para %s (%s)", lead.etiqueta, ", ".join(problemas))
        lead.email_draft = borrador
        lead.estado = "listo_whatsapp"
        log.info("✎ %s (WhatsApp, %s) · %d palabras",
                 lead.etiqueta, lead.telefono, len(borrador.cuerpo.split()))
    if rechazados:
        log.warning("%d/%d mensajes de WhatsApp no pasan la validación del canal",
                    rechazados, len(candidatos))
    return leads
