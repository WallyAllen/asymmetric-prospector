"""Migración única desde el formato de datos anterior (pre-paquete).

Los scripts 0X_*.py originales guardaban los leads con otras claves:
`cro_audit` (un veredicto subjetivo de una sola llamada a Gemini, sin ninguna
métrica objetiva detrás) y `email_content`. `Lead.from_dict` ignora esas
claves desconocidas, así que al recargar los JSON viejos ese trabajo
desaparecía en silencio, dejando el lead como recién minado.

Importante: esta migración NO inventa un score ni un veredicto a partir del
`cro_audit` viejo. Ese número salía de una sola opinión de IA sin datos duros
detrás (nada de LCP, viewport, CTAs medidos), y mezclarlo con el score nuevo
—que sí exige evidencia objetiva— produce justo lo que hay que evitar:
puntajes que no se sostienen cuando alguien mira la web con sus propios ojos.
Lo correcto es dejar el lead como "crudo" para que pase por el auditor nuevo
y reciba un score real. Solo se conservan los datos de contacto (url, email)
y, como nota de contexto, el texto del diagnóstico viejo.

Uso:  python -m prospector.migrate
Es idempotente: si ya no quedan restos del formato viejo, no hace nada.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .config import AUDITED_FILE, COMPOSED_FILE, RAW_FILE
from .logging_setup import get_logger
from .models import Lead
from .storage import write_json
from .utils import lead_id

log = get_logger("migracion")


def _es_legado(item: dict) -> bool:
    return "cro_audit" in item or "email_content" in item


def _migrar_lead(item: dict) -> dict:
    """Limpia las claves del formato viejo sin fabricar un score a partir de ellas.

    El lead queda como recién minado (sin `audit`, sin `email_draft`) para que
    lo audite el motor nuevo con datos reales. Se preserva el diagnóstico viejo
    solo como texto de referencia en `nota_legado`, nunca como score.
    """
    item = dict(item)
    url = item.get("url")
    email = item.get("email")
    item.setdefault("id", lead_id(url, item.get("nombre", ""), email))
    item.setdefault("nombre", item.get("nombre") or "")

    item.pop("screenshot_path", None)
    cro = item.pop("cro_audit", None)
    item.pop("email_content", None)
    item.pop("enviado_el", None)

    # Ni audit ni email_draft: que el motor nuevo vuelva a medir desde cero.
    item["audit"] = None
    item["email_draft"] = None
    item["estado"] = "crudo"

    if cro and cro.get("problema_cro"):
        # Lead.from_dict solo conserva claves declaradas en el modelo, así que
        # esta nota no sobrevive al guardado: se deja constancia únicamente en
        # el log, no tiene sentido fingir que queda persistida en el JSON.
        log.debug("  %s: diagnóstico anterior (referencia, no se conserva) → %s",
                  item.get("id"), cro["problema_cro"])
    return item


def _migrar_archivo(ruta: Path) -> int:
    if not ruta.exists():
        return 0
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, list):
        return 0

    convertidos = 0
    resultado = []
    for item in datos:
        if isinstance(item, dict) and _es_legado(item):
            item = _migrar_lead(item)
            convertidos += 1
        resultado.append(item)

    if convertidos:
        # Validamos que Lead.from_dict acepta el resultado antes de guardar.
        leads = [Lead.from_dict(d) for d in resultado]
        write_json(ruta, [lead.to_dict() for lead in leads])
        log.info(
            "%s: %d leads limpiados del formato anterior (vuelven a 'crudo' para reauditarse)",
            ruta.name, convertidos,
        )
    return convertidos


def migrar_todo() -> int:
    total = 0
    for ruta in (RAW_FILE, AUDITED_FILE, COMPOSED_FILE):
        total += _migrar_archivo(ruta)
    if total:
        log.info(
            "Migración completa: %d leads limpiados. Corre 'python -m prospector audit' "
            "para que reciban un score real con el motor nuevo.", total,
        )
    else:
        log.info("Nada que migrar (los datos ya están en el formato actual)")
    return total


if __name__ == "__main__":
    migrar_todo()


# ═══════════════ Recuperación del canal WhatsApp ═══════════════

def recuperar_whatsapp(simular: bool = True, fecha: str | None = None) -> int:
    """Rescata los contactos de WhatsApp que se mandaron sin dejar rastro.

    `scripts/send_whatsapp.py` marcaba `estado = "enviado"` —el mismo valor
    que usa el correo— y nada más: ni fecha, ni canal, ni entrada en ningún
    registro. Se los reconoce por descarte: están en "enviado", no tienen
    email (así que el mailer nunca pudo haberlos tocado), tienen teléfono y no
    figuran en `registro_envios.json`.

    La fecha no está en ningún lado, así que o la aporta quien los mandó
    (`fecha="2026-09-14"`) o queda vacía. Nunca se inventa: cuando se aporta
    se guarda con `fecha_aproximada: true`, porque se conoce el día pero no la
    hora, y un `stats` que mida "horas hasta la respuesta" tiene que saberlo.
    """
    if fecha:
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"fecha inválida: {fecha!r}. Se espera AAAA-MM-DD.") from None
    enviado_el = f"{fecha}T12:00:00+00:00" if fecha else None
    from .config import COMPOSED_FILE, SENT_FILE, WHATSAPP_SENT_FILE
    from .storage import load_leads, read_json, save_leads, write_json

    leads = load_leads(COMPOSED_FILE)
    del_correo = {e.get("id") for e in (read_json(SENT_FILE, []) or [])}
    registro = read_json(WHATSAPP_SENT_FILE, []) or []
    ya = {e.get("id") for e in registro}

    huerfanos = [
        lead for lead in leads
        if lead.estado == "enviado" and not lead.email and lead.telefono
        and lead.id not in del_correo and lead.id not in ya
    ]
    if not huerfanos:
        log.info("WhatsApp: no hay envíos sin registrar")
        return 0

    log.info("WhatsApp: %d contactos enviados sin ningún registro%s%s",
             len(huerfanos),
             f", fechados el {fecha}" if fecha else ", sin fecha conocida",
             " (simulación)" if simular else "")
    if simular:
        for lead in huerfanos[:5]:
            log.info("    %s · %s", lead.etiqueta, lead.telefono)
        return len(huerfanos)

    for lead in huerfanos:
        registro.append({
            "id": lead.id,
            "nombre": lead.nombre,
            "telefono": lead.telefono,
            "url": lead.url,
            "nicho": lead.nicho,
            "score": lead.audit.score if lead.audit else None,
            "veredicto": lead.audit.veredicto if lead.audit else None,
            "toque": 1,
            "enviado_el": enviado_el,
            "recuperado": True,
            # Se conoce el día, no la hora: no sirve para medir tiempos de
            # respuesta, sí para saber cuándo vence la ventana del toque 2.
            "fecha_aproximada": bool(fecha),
        })
        lead.estado = "enviado_whatsapp"
        lead.canal = "whatsapp"
        lead.enviado_el = enviado_el
    write_json(WHATSAPP_SENT_FILE, registro)
    save_leads(COMPOSED_FILE, leads)
    log.info("WhatsApp: %d contactos incorporados al registro", len(huerfanos))
    return len(huerfanos)
