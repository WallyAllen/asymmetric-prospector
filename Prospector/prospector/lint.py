"""Auditoría del corpus redactado: mide la calidad de la redacción sin enviar nada.

Existe porque los defectos que importan **no se ven en un mensaje suelto**.
Cada correo leído por separado parecía correcto; los 563 juntos decían otra
cosa: el 59% de los que tenían web abría con la misma oración, el 93% de la
rama sin web compartía las palabras, el 81% traía un «con» duplicado en la
primera línea y el 31% pasaba el tope de palabras que el validador aplicaba
solo al motor de IA.

`python -m prospector lint` convierte todo eso en números que suben o bajan
con cada cambio, sin gastar un envío ni esperar tres semanas de respuestas.
"""
from __future__ import annotations

import difflib
import random
import re
from collections import Counter

from .compose.writer import dominio_de, validar
from .config import COMPOSED_FILE, settings
from .models import Lead
from .storage import load_leads

# Objetivos. No son caprichos: la duplicación es lo que detecta el filtro de
# spam de WhatsApp, y la apertura repetida es lo que detecta el prospecto que
# habla con el de al lado.
OBJETIVOS = {
    "duplicacion": 45,       # % de palabras compartidas entre mensajes del canal
    "apertura_top": 12,      # % que abre con la misma oración
}

_CREDENCIAL = re.compile(r"\b(unlp|uba|utn|universidad|facultad|estudiante|carrera de)\b", re.I)


# Un mensaje ya enviado conserva el texto con el que salió, y así tiene que
# ser: reescribir el borrador de algo que ya se mandó borraría el único
# registro de qué leyó el prospecto. Pero tampoco se puede arreglar, así que
# no entra en las métricas: si entrara, el lint seguiría marcando en rojo
# defectos que ya no se pueden tocar y taparía el estado real de la cola.
ENVIADOS = {"enviado", "enviado_whatsapp", "rebotado"}


def _canal(lead: Lead) -> str:
    if lead.email_draft and lead.email_draft.generado_por == "plantilla-whatsapp":
        return "whatsapp"
    return "whatsapp" if (not lead.contactable and lead.telefono) else "email"


def _duplicacion(cuerpos: list[str], pares: int = 120) -> float:
    """% de palabras que dos mensajes cualesquiera comparten, literales y en orden.

    Se promedian pares tomados con un `random` sembrado, no todos contra el
    primero: comparar siempre contra el mismo mensaje hace que el número
    dependa de cuál quedó primero en el archivo. La semilla fija hace que dos
    corridas sobre el mismo corpus den exactamente el mismo número, que es lo
    que permite comparar antes y después de un cambio.
    """
    if len(cuerpos) < 2:
        return 0.0
    rnd = random.Random(20260915)
    compartidas = total = 0
    for _ in range(pares):
        a, b = rnd.sample(cuerpos, 2)
        pa, pb = a.split(), b.split()
        matcher = difflib.SequenceMatcher(None, pa, pb, autojunk=False)
        compartidas += sum(bloque.size for bloque in matcher.get_matching_blocks())
        total += max(len(pa), len(pb))
    return 100 * compartidas / total if total else 0.0


def _primera_oracion(cuerpo: str) -> str:
    """La oración con la que arranca el argumento, salteando el saludo."""
    cuerpo = re.sub(r"^[^\n]*\n\n", "", cuerpo.strip(), count=1)
    partes = re.split(r"(?<=[.:?])\s+", cuerpo.strip())
    return partes[0][:64] if partes else ""


def _marca(valor: float, objetivo: float) -> str:
    return "  ⚠" if valor > objetivo else "  ✓"


def _bloque(nombre: str, leads: list[Lead], lineas: list[str]) -> None:
    cuerpos = [l.email_draft.cuerpo for l in leads if l.email_draft]
    if not cuerpos:
        return
    lineas.append("")
    lineas.append(f"─── {nombre.upper()} · {len(cuerpos)} mensajes " + "─" * max(0, 34 - len(nombre)))

    dup = _duplicacion(cuerpos)
    lineas.append(f"  duplicación de texto      {dup:5.0f}%   (objetivo < {OBJETIVOS['duplicacion']}%)"
                  f"{_marca(dup, OBJETIVOS['duplicacion'])}")

    aperturas = Counter(_primera_oracion(c) for c in cuerpos)
    if aperturas:
        frase, veces = aperturas.most_common(1)[0]
        pct = 100 * veces / len(cuerpos)
        lineas.append(f"  apertura más repetida     {pct:5.0f}%   (objetivo < {OBJETIVOS['apertura_top']}%)"
                      f"{_marca(pct, OBJETIVOS['apertura_top'])}")
        lineas.append(f"      «{frase}…»")
        lineas.append(f"  aperturas distintas       {len(aperturas):5d}")

    palabras = sorted(len(c.split()) for c in cuerpos)
    mediana = palabras[len(palabras) // 2]
    caracteres = sorted(len(c) for c in cuerpos)
    lineas.append(f"  palabras (mediana/máx)    {mediana:5d} / {palabras[-1]}")
    lineas.append(f"  caracteres (mediana/máx)  {caracteres[len(caracteres) // 2]:5d} / {caracteres[-1]}")

    problemas: Counter[str] = Counter()
    for lead in leads:
        if not lead.email_draft:
            continue
        for p in validar(lead.email_draft, canal=nombre, dominio_propio=dominio_de(lead)):
            # Se agrupa por tipo, no por texto exacto, para que 170 cuerpos
            # largos no impriman 170 renglones distintos.
            problemas[re.sub(r"\s*\([^)]*\)", "", p).strip()] += 1
    if problemas:
        lineas.append(f"  no pasan la validación    {sum(1 for l in leads if l.email_draft and validar(l.email_draft, canal=nombre, dominio_propio=dominio_de(l))):5d}")
        for motivo, veces in problemas.most_common(6):
            lineas.append(f"      {veces:4d}  {motivo}")
    else:
        lineas.append("  no pasan la validación        0   ✓")


def informe(leads: list[Lead] | None = None) -> str:
    leads = leads if leads is not None else load_leads(COMPOSED_FILE)
    con_borrador = [l for l in leads if l.email_draft]

    lineas = [
        "",
        "  LINT DE REDACCIÓN — mide el corpus, no un mensaje suelto",
        "  " + "=" * 62,
    ]
    en_cola = [l for l in con_borrador if l.estado not in ENVIADOS]
    enviados = len(con_borrador) - len(en_cola)
    motores = Counter(l.email_draft.generado_por for l in en_cola)
    lineas.append(f"  {len(en_cola)} borradores en cola · " +
                  " · ".join(f"{v} {k}" for k, v in motores.most_common()))
    if enviados:
        lineas.append(f"  ({enviados} ya enviados, no se miden: su texto no se puede cambiar)")

    for canal in ("email", "whatsapp"):
        _bloque(canal, [l for l in en_cola if _canal(l) == canal], lineas)

    # Chequeos de configuración: se informan una vez, no por mensaje.
    lineas.append("")
    lineas.append("─── CONFIGURACIÓN " + "─" * 30)
    cfg = settings.compose
    credencial = _CREDENCIAL.search(f"{cfg.sender_role} {cfg.sender_pitch}")
    if credencial:
        lineas.append(f"  ⚠ SENDER_ROLE/SENDER_PITCH trae una credencial académica "
                      f"(«{credencial.group(0)}»).")
        lineas.append("     La regla 4 del PROMPT la prohíbe: la autoridad la da el hallazgo medido.")
    else:
        lineas.append("  ✓ sin credenciales académicas en la firma")
    if not cfg.sender_proof.strip():
        lineas.append("  · SENDER_PROOF vacío: no hay línea de prueba social en ningún mensaje")
    lineas.append("")
    return "\n".join(lineas)


def imprimir(leads: list[Lead] | None = None) -> None:
    print(informe(leads))
