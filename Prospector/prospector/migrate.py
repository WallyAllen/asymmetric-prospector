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
