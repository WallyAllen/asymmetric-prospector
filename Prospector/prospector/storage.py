"""Persistencia idempotente en JSON: escritura atómica y fusión por lead.id."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable

from .config import BASE_DIR, SUPPRESSION_FILE
from .logging_setup import get_logger
from .models import Lead

log = get_logger("storage")


def to_relative(path: str | Path | None) -> str | None:
    """Guarda rutas relativas al proyecto: mover la carpeta no rompe los datos."""
    if not path:
        return None
    p = Path(path)
    try:
        return p.resolve().relative_to(BASE_DIR).as_posix()
    except (ValueError, OSError):
        return p.as_posix()


_DRIVE_ABS = re.compile(r"^[A-Za-z]:[\\/]")


def _nombre_de_ruta_ajena(ruta_cruda: str) -> str:
    """Último componente de una ruta absoluta, sea cual sea su SO de origen.

    `Path(...).name` solo entiende el separador del SO donde corre Python
    ahora mismo; una ruta de Windows guardada por otra máquina y releída en
    Linux (o al revés) no se parte bien. Se corta a mano por ambas barras.
    """
    return ruta_cruda.replace("\\", "/").rsplit("/", 1)[-1]


def to_absolute(path: str | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    es_absoluta = p.is_absolute() or bool(_DRIVE_ABS.match(path))
    if es_absoluta:
        if p.exists():
            return p
        # Ruta absoluta heredada de otra máquina o de un proyecto movido/renombrado:
        # se reubica por nombre de archivo dentro de las capturas actuales.
        nombre = _nombre_de_ruta_ajena(path)
        candidato = BASE_DIR / "data" / "screenshots" / nombre
        if candidato.exists():
            return candidato
        for encontrado in (BASE_DIR / "data" / "screenshots").glob(f"*/{nombre}"):
            return encontrado
        return None
    candidate = BASE_DIR / p
    return candidate if candidate.exists() else None


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        backup = path.with_suffix(path.suffix + ".corrupto")
        path.rename(backup)
        log.error("%s ilegible (%s). Respaldado en %s", path.name, exc, backup.name)
        return default if default is not None else []


def load_leads(path: Path) -> list[Lead]:
    return [Lead.from_dict(item) for item in read_json(path, [])]


def save_leads(path: Path, leads: Iterable[Lead]) -> None:
    write_json(path, [lead.to_dict() for lead in leads])


# Cuánto ha avanzado un lead en el embudo: sirve para decidir, al fusionar,
# de qué lado viene el trabajo más "hecho" (nunca se pisa lo más avanzado con
# lo menos avanzado, venga del lado que venga).
#
# ⚠ Los estados de WhatsApp FALTABAN acá, y `.get(estado, 0)` los valoraba en 0
# —menos avanzado que "crudo"—. Como `pipeline.redactar_correos()` hace
# `merge_leads(composed, audited)`, en CADA `compose` el lead retrocedía de
# `listo_whatsapp` a `auditado`; después `redactar_whatsapp()` no lo recuperaba
# (ya tenía borrador) y `exportar_whatsapp()` lo excluía y le borraba el .txt.
# 86 leads con mensaje escrito y score medio 96/100 quedaron fuera de la cola
# sin una sola línea de log. Cualquier estado nuevo va acá el mismo día.
_PROGRESO = {
    "crudo": 0,
    "descartado": 1,
    "auditado": 2,
    "listo": 3,
    "listo_whatsapp": 3,
    "enviado": 4,
    "enviado_whatsapp": 4,
    "sin_whatsapp": 4,
    "revisar_web": 4,
    "rebotado": 4,
    # Terminales: por encima de todo, para que ninguna fusión los pise. Un
    # `compose` que devolviera a "auditado" a alguien que contestó lo pondría
    # de vuelta en la cola, y esa es la única falla del sistema que no tiene
    # arreglo después de pasar.
    "respondido": 9,
    "baja": 9,
}


def merge_leads(existing: Iterable[Lead], nuevos: Iterable[Lead]) -> list[Lead]:
    """Fusiona por id conservando siempre el trabajo más avanzado de cada lado.

    No asume que `existing` es la fuente de verdad: si `nuevos` trae una
    auditoría o un borrador que `existing` no tiene (por ejemplo, porque
    `existing` se guardó desde una etapa anterior que aún no había corrido
    la auditoría), se adopta. Nunca se pierde trabajo ya hecho por el orden
    en que se fusionan los archivos.
    """
    index: dict[str, Lead] = {lead.id: lead for lead in existing}
    for nuevo in nuevos:
        actual = index.get(nuevo.id)
        if actual is None:
            index[nuevo.id] = nuevo
            continue

        for campo in ("nombre", "url", "telefono", "whatsapp_verificado", "whatsapp_fuente", "direccion", "categoria", "rating",
                      "resenas", "nicho", "email", "canal"):
            valor = getattr(nuevo, campo)
            if valor and not getattr(actual, campo):
                setattr(actual, campo, valor)
        for correo in nuevo.emails:
            if correo not in actual.emails:
                actual.emails.append(correo)
        if not actual.email and actual.emails:
            actual.email = actual.emails[0]

        if actual.audit is None and nuevo.audit is not None:
            actual.audit = nuevo.audit
        elif actual.audit and nuevo.audit and nuevo.audit.auditado_el > actual.audit.auditado_el:
            # Un re-audit --forzar mide de nuevo un sitio EN VIVO: si vino
            # con fecha más nueva, reemplaza al viejo en vez de conservarlo
            # solo porque "ya había uno". Antes esto dejaba leads_listos.json
            # con un score/hallazgos viejos para siempre, aunque el sitio ya
            # se hubiera re-auditado con datos frescos.
            actual.audit = nuevo.audit
        if actual.email_draft is None and nuevo.email_draft is not None:
            actual.email_draft = nuevo.email_draft
        if not actual.enviado_el and nuevo.enviado_el:
            actual.enviado_el = nuevo.enviado_el
        if not actual.respondido_el and nuevo.respondido_el:
            actual.respondido_el = nuevo.respondido_el

        if _PROGRESO.get(nuevo.estado, 0) > _PROGRESO.get(actual.estado, 0):
            actual.estado = nuevo.estado
            if nuevo.motivo_descarte and not actual.motivo_descarte:
                actual.motivo_descarte = nuevo.motivo_descarte
    return list(index.values())


def upsert(path: Path, nuevos: Iterable[Lead]) -> list[Lead]:
    leads = merge_leads(load_leads(path), nuevos)
    save_leads(path, leads)
    return leads


def load_suppression() -> set[str]:
    """Dominios/emails que nunca deben contactarse (bajas, rebotes, clientes)."""
    if not SUPPRESSION_FILE.exists():
        return set()
    entries = set()
    for line in SUPPRESSION_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            entries.add(line)
    return entries


def add_to_suppression(entry: str, motivo: str = "") -> None:
    SUPPRESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SUPPRESSION_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{entry.strip().lower()}{('  # ' + motivo) if motivo else ''}\n")
