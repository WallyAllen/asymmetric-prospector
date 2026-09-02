"""Informe HTML autocontenido: el panel donde decides a quién escribir.

Se genera desde los datos ya auditados, sin dependencias externas, y se abre
con doble clic. Las capturas van embebidas, así que el archivo se puede enviar.
"""
from __future__ import annotations

import base64
import html
import io
from datetime import datetime
from pathlib import Path

from .config import AUDITED_FILE, COMPOSED_FILE, DATA_DIR
from .logging_setup import get_logger
from .models import Lead
from .storage import load_leads, merge_leads, to_absolute

log = get_logger("informe")

ANCHO_MINIATURA = 560

CSS = """
:root{--tinta:#14161a;--suave:#6b7280;--linea:#e6e8eb;--fondo:#fbfbfc;--rojo:#e53935;
      --ambar:#f59e0b;--verde:#16a34a;--azul:#2563eb}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
     font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{padding:34px 28px 22px;border-bottom:1px solid var(--linea);background:#fff}
h1{margin:0 0 6px;font-size:23px;letter-spacing:-.02em}
.sub{color:var(--suave);font-size:14px}
.kpis{display:flex;gap:28px;margin-top:18px;flex-wrap:wrap}
.kpi b{display:block;font-size:26px;letter-spacing:-.02em}
.kpi span{color:var(--suave);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
main{padding:24px 28px 60px;max-width:1080px;margin:0 auto}
.lead{background:#fff;border:1px solid var(--linea);border-radius:12px;padding:20px 22px;margin-bottom:18px}
.cab{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap}
.nombre{font-size:17px;font-weight:650;margin:0}
.meta{color:var(--suave);font-size:13px;margin-top:3px}
.meta a{color:var(--azul);text-decoration:none}
.score{text-align:right;min-width:96px}
.score b{font-size:30px;letter-spacing:-.03em;display:block;line-height:1}
.badge{display:inline-block;font-size:11px;font-weight:650;text-transform:uppercase;
       letter-spacing:.06em;padding:3px 9px;border-radius:99px;color:#fff}
.b-sin_web{background:#7c3aed}.b-critico{background:var(--rojo)}
.b-inaccesible{background:#b91c1c}.b-mejorable{background:var(--ambar)}.b-sano{background:var(--verde)}
.barra{height:6px;background:var(--linea);border-radius:99px;overflow:hidden;margin:14px 0 16px}
.barra i{display:block;height:100%;background:linear-gradient(90deg,#f59e0b,#e53935)}
ul.hallazgos{list-style:none;padding:0;margin:0}
ul.hallazgos li{padding:10px 0;border-top:1px dashed var(--linea)}
.tit{font-weight:600}
.ev{color:var(--suave);font-size:13px;font-variant-numeric:tabular-nums}
.arg{font-size:14px;margin-top:4px}
.sev{float:right;font-size:12px;color:var(--suave)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.grid img{width:100%;border:1px solid var(--linea);border-radius:8px;display:block}
.correo{margin-top:16px;background:#f7f8fa;border:1px solid var(--linea);border-radius:9px;padding:14px 16px}
.correo .asunto{font-weight:650;margin-bottom:8px}
.correo pre{white-space:pre-wrap;font:14px/1.55 inherit;margin:0}
.vacio{color:var(--suave);padding:40px 0;text-align:center}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
"""


def _miniatura(ruta: Path | None) -> str | None:
    if not ruta or not ruta.exists():
        return None
    try:
        from PIL import Image

        imagen = Image.open(ruta).convert("RGB")
        if imagen.width > ANCHO_MINIATURA:
            alto = int(imagen.height * ANCHO_MINIATURA / imagen.width)
            imagen = imagen.resize((ANCHO_MINIATURA, alto))
        buffer = io.BytesIO()
        imagen.save(buffer, "JPEG", quality=78, optimize=True)
        datos = buffer.getvalue()
        mime = "image/jpeg"
    except Exception:  # noqa: BLE001 - sin Pillow embebemos el PNG tal cual
        datos, mime = ruta.read_bytes(), "image/png"
        if len(datos) > 900_000:
            return None
    return f"data:{mime};base64,{base64.b64encode(datos).decode()}"


def _tarjeta(lead: Lead) -> str:
    e = html.escape
    auditoria = lead.audit
    score = auditoria.score if auditoria else 0
    veredicto = auditoria.veredicto if auditoria else "sin_auditar"

    contacto = []
    if lead.email:
        contacto.append(e(lead.email))
    if lead.telefono:
        contacto.append(e(lead.telefono))
    enlace = f'<a href="{e(lead.url)}" target="_blank">{e(lead.url)}</a>' if lead.url else "sin web"

    hallazgos = ""
    if auditoria:
        filas = []
        for hallazgo in auditoria.top_findings[:6]:
            filas.append(
                f'<li><span class="sev">severidad {hallazgo.severidad}/10</span>'
                f'<div class="tit">{e(hallazgo.titulo)}</div>'
                f'<div class="ev">{e(hallazgo.evidencia)}</div>'
                f'<div class="arg">{e(hallazgo.argumento)}</div></li>'
            )
        hallazgos = f'<ul class="hallazgos">{"".join(filas)}</ul>'

    imagenes = ""
    if auditoria:
        piezas = []
        # Prioridad por claves: la anotada es la ideal, pero un lead migrado
        # del formato anterior solo tiene la captura sin marcar, y aun así
        # vale la pena mostrarla en el informe.
        opciones_desktop = ("anotada", "desktop_fold", "principal", "desktop_full")
        opciones_movil = ("anotada_movil", "mobile_fold")
        clave_desktop = next((c for c in opciones_desktop if auditoria.capturas.get(c)), None)
        clave_movil = next((c for c in opciones_movil if auditoria.capturas.get(c)), None)
        for clave, titulo in ((clave_desktop, "Escritorio"), (clave_movil, "Móvil")):
            if not clave:
                continue
            src = _miniatura(to_absolute(auditoria.capturas.get(clave)))
            if src:
                piezas.append(f'<figure style="margin:0"><img src="{src}" alt="{titulo}"></figure>')
        if piezas:
            imagenes = f'<div class="grid">{"".join(piezas)}</div>'

    correo = ""
    if lead.email_draft:
        correo = (
            f'<div class="correo"><div class="asunto">Asunto: {e(lead.email_draft.asunto)}</div>'
            f"<pre>{e(lead.email_draft.cuerpo)}</pre></div>"
        )

    return f"""<article class="lead">
  <div class="cab">
    <div>
      <p class="nombre">{e(lead.etiqueta)}</p>
      <div class="meta">{enlace}{(' · ' + ' · '.join(contacto)) if contacto else ''}</div>
    </div>
    <div class="score"><b>{score}</b><span class="badge b-{e(veredicto)}">{e(veredicto.replace('_', ' '))}</span></div>
  </div>
  <div class="barra"><i style="width:{min(100, score)}%"></i></div>
  {hallazgos}{imagenes}{correo}
</article>"""


def generar(destino: Path | None = None, minimo: int = 0) -> Path:
    leads = merge_leads(load_leads(COMPOSED_FILE), load_leads(AUDITED_FILE))
    interesantes = [
        lead for lead in leads
        if lead.audit and lead.audit.score >= minimo and lead.estado != "descartado"
    ]
    interesantes.sort(key=lambda l: -(l.audit.score if l.audit else 0))

    con_email = sum(1 for l in interesantes if l.contactable)
    sin_web = sum(1 for l in interesantes if not l.url)
    criticos = sum(1 for l in interesantes if l.audit and l.audit.score >= 75)

    cuerpo = "".join(_tarjeta(lead) for lead in interesantes) or (
        '<p class="vacio">Todavía no hay leads auditados. Ejecuta <code>python -m prospector audit</code>.</p>'
    )
    documento = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prospector · informe</title><style>{CSS}</style></head><body>
<header>
  <h1>Informe de prospección</h1>
  <div class="sub">Generado el {datetime.now():%d/%m/%Y a las %H:%M}</div>
  <div class="kpis">
    <div class="kpi"><b>{len(interesantes)}</b><span>oportunidades</span></div>
    <div class="kpi"><b>{criticos}</b><span>críticas (75+)</span></div>
    <div class="kpi"><b>{sin_web}</b><span>sin web</span></div>
    <div class="kpi"><b>{con_email}</b><span>contactables</span></div>
  </div>
</header>
<main>{cuerpo}</main></body></html>"""

    destino = destino or (DATA_DIR / "informe.html")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(documento, encoding="utf-8")
    log.info("Informe listo: %s (%d leads)", destino, len(interesantes))
    return destino
