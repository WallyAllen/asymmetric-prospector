"""Anotación de capturas: la prueba visual que hace creíble el correo.

Antes se marcaba un recuadro rojo sobre la captura entera del viewport
(1440×900 o 390×844): técnicamente correcto, pero en la práctica el defecto
quedaba perdido en una imagen enorme y había que buscarlo. Ahora se recorta
y amplía la zona señalada, con margen suficiente para reconocer la marca:
la primera imagen que ve el prospecto es un primer plano de SU problema, no
un mapa de toda su pantalla con una chincheta en algún lado.
"""
from __future__ import annotations

from pathlib import Path

from ..config import DESKTOP_VIEWPORT, MOBILE_VIEWPORT
from ..logging_setup import get_logger
from ..models import Finding

log = get_logger("captura")

ROJO = (229, 57, 53)
ROJO_SUAVE = (229, 57, 53, 26)
BLANCO = (255, 255, 255)
TINTA = (17, 17, 17)

# Cuánto se agranda alrededor de la zona señalada: lo mayor entre un margen
# fijo (para que un botón pequeño no quede pegado al borde) y una fracción
# del propio tamaño de la zona (para que un bloque grande respire).
_PAD_MIN_X, _PAD_FRAC_X = 70, 0.35
_PAD_MIN_Y, _PAD_FRAC_Y = 55, 0.35
# El recorte final nunca es más pequeño que esto: hace falta contexto
# alrededor (logo, colores, layout) para que se reconozca como "tu web".
_MIN_RECORTE_ANCHO, _MIN_RECORTE_ALTO = 0.42, 0.28
# Si la zona ya cubre casi toda la captura, recortar no aporta nada.
_MAX_AREA_RECORTABLE = 0.82


def _fuente(tamano: int):
    from PIL import ImageFont

    for nombre in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "seguisb.ttf"):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    return ImageFont.load_default()


def _texto_ancho(draw, texto: str, fuente) -> int:
    try:
        caja = draw.textbbox((0, 0), texto, font=fuente)
        return caja[2] - caja[0]
    except Exception:  # noqa: BLE001 - fuente por defecto sin textbbox
        return len(texto) * 7


def _envolver(draw, texto: str, fuente, ancho_max: int, max_lineas: int = 4) -> list[str]:
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if _texto_ancho(draw, prueba, fuente) <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = lineas[-1].rstrip(" ,;:") + "…"
    return lineas


def _rect_px(zona: dict, escala: float) -> tuple[float, float, float, float]:
    x0 = zona.get("x", 0) * escala
    y0 = zona.get("y", 0) * escala
    return x0, y0, x0 + zona.get("width", 0) * escala, y0 + zona.get("height", 0) * escala


def _calcular_recorte(zona_px: tuple[float, float, float, float], img_w: int, img_h: int):
    """Caja de recorte alrededor de la zona: con margen, con un mínimo de
    contexto y sin salirse de la imagen. Devuelve None si no vale la pena
    recortar (la zona ya es casi toda la imagen)."""
    x0, y0, x1, y1 = zona_px
    ancho_zona, alto_zona = max(1.0, x1 - x0), max(1.0, y1 - y0)

    if (ancho_zona * alto_zona) >= img_w * img_h * _MAX_AREA_RECORTABLE:
        return None

    pad_x = max(_PAD_MIN_X, ancho_zona * _PAD_FRAC_X)
    pad_y = max(_PAD_MIN_Y, alto_zona * _PAD_FRAC_Y)
    left, top = x0 - pad_x, y0 - pad_y
    right, bottom = x1 + pad_x, y1 + pad_y

    # Contexto mínimo: si el margen natural deja un recorte demasiado
    # pequeño (un botón suelto), se agranda simétricamente hasta el mínimo.
    ancho_min, alto_min = img_w * _MIN_RECORTE_ANCHO, img_h * _MIN_RECORTE_ALTO
    if (right - left) < ancho_min:
        extra = (ancho_min - (right - left)) / 2
        left, right = left - extra, right + extra
    if (bottom - top) < alto_min:
        extra = (alto_min - (bottom - top)) / 2
        top, bottom = top - extra, bottom + extra

    # Se desliza la caja (no se recorta a lo bruto) para no perder tamaño
    # cuando la zona está pegada a un borde de la captura original.
    if left < 0:
        right -= left
        left = 0
    if top < 0:
        bottom -= top
        top = 0
    if right > img_w:
        left -= (right - img_w)
        right = img_w
    if bottom > img_h:
        top -= (bottom - img_h)
        bottom = img_h

    left, top = max(0, left), max(0, top)
    right, bottom = min(img_w, right), min(img_h, bottom)
    if right - left < 40 or bottom - top < 40:
        return None
    return int(left), int(top), int(right), int(bottom)


def anotar(
    origen: Path,
    destino: Path,
    hallazgos: list[Finding],
    movil: bool = False,
    pie: str | None = None,
) -> Path | None:
    """Recorta la zona del problema principal, amplía y marca en rojo.

    Solo el hallazgo más prioritario decide el recorte; si otros hallazgos
    con zona caen dentro de ese recorte, también se numeran. Sin ninguna
    zona utilizable, se usa la captura completa tal cual (mejor eso que
    inventar un recorte sin nada que señalar).
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        log.warning("Pillow no está instalado: no se pueden anotar capturas")
        return None
    if not origen.exists():
        return None

    imagen_completa = Image.open(origen).convert("RGB")
    viewport = MOBILE_VIEWPORT if movil else DESKTOP_VIEWPORT
    escala = imagen_completa.width / viewport["width"] if viewport["width"] else 1.0

    # Solo se marcan hallazgos del viewport que se está anotando: señalar en la
    # captura de escritorio un defecto medido en móvil confunde al prospecto.
    propio = "mobile" if movil else "desktop"
    con_zona = [
        h for h in hallazgos
        if h.zona and h.zona.get("width") and h.zona.get("height") and h.viewport in (propio, "ambos")
    ]

    recorte = None
    if con_zona:
        zona_principal_px = _rect_px(con_zona[0].zona, escala)
        recorte = _calcular_recorte(zona_principal_px, imagen_completa.width, imagen_completa.height)

    if recorte:
        left, top, right, bottom = recorte
        imagen = imagen_completa.crop(recorte)
        offset_x, offset_y = left, top
    else:
        imagen = imagen_completa
        offset_x, offset_y = 0, 0

    # Si el recorte quedó chico, se agranda para que el detalle se lea bien
    # incluso en la miniatura del informe o en el cliente de correo.
    ANCHO_OBJETIVO = 1000
    if imagen.width < ANCHO_OBJETIVO:
        factor = ANCHO_OBJETIVO / imagen.width
        imagen = imagen.resize((int(imagen.width * factor), int(imagen.height * factor)), Image.LANCZOS)
    else:
        factor = 1.0

    capa = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    grosor = max(3, int(4 * escala * factor))
    fuente_badge = _fuente(int(20 * escala * factor))

    dibujados = 0
    for indice, hallazgo in enumerate(con_zona[:3], start=1):
        x0, y0, x1, y1 = _rect_px(hallazgo.zona, escala)
        # Coordenadas relativas al recorte (y reescaladas si se amplió).
        x0 = (x0 - offset_x) * factor
        y0 = (y0 - offset_y) * factor
        x1 = (x1 - offset_x) * factor
        y1 = (y1 - offset_y) * factor
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(imagen.width - 1, x1), min(imagen.height - 1, y1)
        if x1 - x0 < 6 or y1 - y0 < 6:
            continue  # la zona de este hallazgo secundario quedó fuera del recorte

        draw.rectangle([x0, y0, x1, y1], outline=ROJO + (255,), width=grosor)
        draw.rectangle([x0, y0, x1, y1], fill=ROJO_SUAVE)

        radio = int(17 * escala * factor)
        # La chapa va PEGADA AL BORDE del recuadro pero por fuera, nunca
        # encima del contenido: con el recorte ajustado a la zona, colocarla
        # "adentro" (como antes, cuando sobraba espacio de captura completa)
        # termina tapando el propio texto que se quiere señalar.
        cx = min(max(radio, x0 + radio), imagen.width - radio)
        if y0 - 2 * radio - grosor >= 0:
            cy = y0 - radio - grosor          # arriba del recuadro
        elif y1 + 2 * radio + grosor <= imagen.height:
            cy = y1 + radio + grosor          # o abajo, si arriba no entra
        else:
            cy = max(radio + grosor, y0 + radio + grosor)  # último recurso: adentro
        draw.ellipse([cx - radio, cy - radio, cx + radio, cy + radio], fill=ROJO + (255,))
        draw.ellipse([cx - radio, cy - radio, cx + radio, cy + radio], outline=BLANCO, width=max(1, grosor // 2))
        etiqueta = str(indice)
        ancho = _texto_ancho(draw, etiqueta, fuente_badge)
        draw.text((cx - ancho / 2, cy - radio * 0.72), etiqueta, font=fuente_badge, fill=BLANCO)
        dibujados += 1

    imagen = Image.alpha_composite(imagen.convert("RGBA"), capa).convert("RGB")

    # Pie de foto con el diagnóstico, para que la imagen se explique sola.
    texto_pie = pie or (con_zona[0].titulo if con_zona else (hallazgos[0].titulo if hallazgos else ""))
    if texto_pie:
        from PIL import Image as _Image, ImageDraw as _Draw

        fuente_pie = _fuente(int(19 * escala * factor))
        medidor = _Draw.Draw(imagen)
        margen = int(22 * escala * factor)
        lineas_pie = _envolver(medidor, texto_pie, fuente_pie, imagen.width - margen * 2)
        alto_linea = int(26 * escala * factor)
        alto_pie = alto_linea * len(lineas_pie) + margen

        lienzo = _Image.new("RGB", (imagen.width, imagen.height + alto_pie), BLANCO)
        lienzo.paste(imagen, (0, 0))
        draw2 = _Draw.Draw(lienzo)
        draw2.rectangle([0, imagen.height, imagen.width, imagen.height + 4], fill=ROJO)
        y = imagen.height + int(margen * 0.6)
        for linea in lineas_pie:
            draw2.text((margen, y), linea, font=fuente_pie, fill=TINTA)
            y += alto_linea
        imagen = lienzo

    destino.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(destino, "PNG", optimize=True)
    log.debug("Captura anotada: %s (%s, %d marca%s)", destino.name,
              "recortada" if recorte else "completa", dibujados, "" if dibujados == 1 else "s")
    return destino


def componer_comparativa(desktop: Path, mobile: Path, destino: Path) -> Path | None:
    """Une escritorio y móvil en una sola imagen: el contraste vende solo."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    if not (desktop.exists() and mobile.exists()):
        return None

    izq = Image.open(desktop).convert("RGB")
    der = Image.open(mobile).convert("RGB")
    alto = max(izq.height, der.height)
    escala_der = alto / der.height
    der = der.resize((int(der.width * escala_der), alto))

    separador = 16
    lienzo = Image.new("RGB", (izq.width + separador + der.width, alto), BLANCO)
    lienzo.paste(izq, (0, 0))
    lienzo.paste(der, (izq.width + separador, 0))
    ImageDraw.Draw(lienzo).rectangle(
        [izq.width, 0, izq.width + separador, alto], fill=(240, 240, 240)
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(destino, "PNG", optimize=True)
    return destino
