"""Envío semi-manual por WhatsApp Web, con las mismas salvaguardas que el correo.

Abre el chat con el texto ya cargado y, si hay captura, la deja en el
portapapeles para pegarla. Lo que cambió respecto de la versión anterior:

  · **cuota diaria y ventana horaria** (`WA_DAILY_CAP`, por defecto 50). En
    correo pasarse cuesta entregabilidad; acá cuesta el número, con los chats
    adentro y sin apelación.
  · **registro real de lo enviado** en `data/04_sent/registro_whatsapp.json`,
    con fecha. Antes solo se marcaba `estado = "enviado"` —el mismo valor que
    usa el correo— así que 56 mensajes quedaron sin fecha, sin canal y fuera
    de todo registro: el sistema creía haber hecho 49 contactos cuando había
    hecho 105.
  · **lista de supresión**: quien pidió que no le escriban lo pidió para todos
    los canales, no solo para el correo.
  · **el número correcto** (ver `prospector/telefono.py`). La conversión
    anterior le ponía un `9` a todos los teléfonos, y el 69% de los que
    devuelve Maps son líneas fijas: un `9` delante no da el celular de ese
    negocio, da el de otra persona. Ahora se convierte fielmente, se elige el
    mejor número disponible (el `wa.me` de su propia web primero) y, si no se
    puede normalizar con confianza, se saltea el lead en vez de adivinar.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.config import COMPOSED_FILE, settings  # noqa: E402
from prospector.deliver import cola_whatsapp, cuota_whatsapp, registrar_whatsapp  # noqa: E402
from prospector.telefono import para_whatsapp  # noqa: E402
from prospector.storage import load_leads, save_leads, to_absolute  # noqa: E402

def copiar_imagen(ruta: Path) -> bool:
    """Deja la captura en el portapapeles (solo Windows)."""
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        f"[System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{ruta}'))"
    )
    try:
        res = subprocess.run(["powershell", "-sta", "-c", ps], capture_output=True, text=True)
        return res.returncode == 0
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Envío semi-manual por WhatsApp Web.")
    parser.add_argument("--sin-fijos", action="store_true",
                        help="saltear las líneas fijas: solo celulares y WhatsApp publicados")
    parser.add_argument("--limite", type=int, help="tope para esta tanda, además del diario")
    args = parser.parse_args()

    cfg = settings
    print("=" * 62)
    print("  WHATSAPP · envío semi-manual")
    print("=" * 62)

    leads = load_leads(COMPOSED_FILE)
    cola = cola_whatsapp(leads, cfg)
    if args.sin_fijos:
        # Un fijo puede tener WhatsApp Business, pero la mayoría no, y cada uno
        # gasta un lugar del cupo diario para abrir un chat que no existe.
        # Conviene sobre todo mientras la auditoría no haya capturado todavía
        # los números que cada negocio publica en su propia web.
        antes = len(cola)
        cola = [l for l in cola if para_whatsapp(l, cfg.whatsapp.country_code).confianza >= 2]
        print(f"  --sin-fijos: {antes - len(cola)} líneas fijas fuera de esta tanda")
    if not cola:
        print("No hay mensajes de WhatsApp pendientes.")
        return 0

    cuota = cuota_whatsapp(cfg)
    en_ventana, motivo = cuota.en_ventana()
    if not en_ventana:
        print(f"⚠  {motivo}.")
        if input("¿Seguir igual? (s/N): ").strip().lower() != "s":
            return 0
    if cuota.restantes <= 0:
        print(f"Cuota diaria agotada ({cuota.enviados_hoy}/{cfg.whatsapp.daily_cap}). Seguimos mañana.")
        return 0

    tope = min(cuota.restantes, args.limite) if args.limite else cuota.restantes
    tanda = cola[:tope]
    print(f"{len(cola)} en cola · {cuota.restantes} disponibles hoy "
          f"({cuota.enviados_hoy}/{cfg.whatsapp.daily_cap} usados)")
    print("-" * 62)

    for i, lead in enumerate(tanda, 1):
        numero = para_whatsapp(lead, cfg.whatsapp.country_code)
        if not numero:
            print(f"[{i}/{len(tanda)}] {lead.etiqueta}: sin número usable "
                  f"({lead.telefono!r}), lo salteo.")
            continue

        borrador = lead.email_draft
        print(f"[{i}/{len(tanda)}] {lead.etiqueta}")
        print(f"          score {lead.audit.score if lead.audit else '?'}/100 · "
              f"{len(borrador.cuerpo.split())} palabras")
        print(f"          +{numero.e164} · {numero.etiqueta}")
        if numero.tipo == "fijo":
            print("          ⚠ si no tiene WhatsApp Business, el chat no va a existir: no fuerces el envío")

        imagen_lista = False
        if borrador.adjunto:
            ruta = to_absolute(borrador.adjunto)
            if ruta and ruta.exists():
                imagen_lista = copiar_imagen(ruta)

        accion = input("          ENTER para abrir · 's' saltear · 'q' salir: ").strip().lower()
        if accion == "q":
            break
        if accion == "s":
            continue

        webbrowser.open(f"https://wa.me/{numero.e164}?text={urllib.parse.quote(borrador.cuerpo)}")
        if imagen_lista:
            print("          ✓ captura en el portapapeles: Ctrl+V para pegarla")

        if input("          ¿Enviado? (ENTER sí / 'n' no): ").strip().lower() != "n":
            registrar_whatsapp(lead)
            cuota.anotar()
            save_leads(COMPOSED_FILE, leads)
            print(f"          ✓ registrado ({cuota.enviados_hoy}/{cfg.whatsapp.daily_cap} hoy)")
            if cuota.restantes <= 0:
                print("\nCuota diaria alcanzada. Mejor cortar acá.")
                break
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
