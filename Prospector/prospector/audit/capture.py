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

from ..config import DESKTOP_VIEWPORT, MOBILE_DEVICE_SCALE, MOBILE_VIEWPORT
from ..logging_setup import get_logger
from ..models import Finding
from .rules import es_demostrable

log = get_logger("captura")

ROJO = (229, 57, 53)
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


def _envolver(draw, texto: str, fuente, ancho_max: int, max_lineas: int | None = None) -> list[str]:
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
    if max_lineas is not None and len(lineas) > max_lineas:
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

    # P1: "incluir siempre la franja superior con el logo"
    # Forzamos top=0 por defecto para ganar el contexto del hero/logo.
    left = x0 - pad_x
    top = 0.0
    right = x1 + pad_x
    bottom = y1 + pad_y

    # Contexto mínimo: sin este piso, una zona chica (un botón, un ítem de
    # nav) produce un recorte del tamaño del propio botón — ni con el logo
    # arriba alcanza para que se reconozca la marca. El ancho se expande
    # simétrico alrededor de la zona; el alto solo hacia abajo, porque
    # arriba ya está fijo en 0.
    ancho_min, alto_min = img_w * _MIN_RECORTE_ANCHO, img_h * _MIN_RECORTE_ALTO
    if (right - left) < ancho_min:
        extra = (ancho_min - (right - left)) / 2
        left, right = left - extra, right + extra
    bottom = max(bottom, alto_min)

    # Se desliza la caja en horizontal (no se recorta a lo bruto) para no
    # perder ancho cuando la zona está pegada a un borde lateral.
    if left < 0:
        right -= left
        left = 0
    if right > img_w:
        left -= (right - img_w)
        right = img_w
    left, right = max(0, left), min(img_w, right)
    bottom = min(img_h, bottom)

    w = max(1.0, right - left)
    h = max(1.0, bottom - top)

    # Relación de aspecto acotada (nunca más de 2:1 ni menos de 3:4)
    # 2:1 (banda horizontal): w/h = 2 => h = w/2. Si h es menor, expandimos h hacia abajo.
    if (w / h) > 2.0:
        target_h = w / 2.0
        bottom = min(img_h, top + target_h)
        h = max(1.0, bottom - top)

    # 3:4 (columna vertical): w/h = 0.75 => h = w/0.75. Si h es mayor, ensanchamos o recortamos.
    if (w / h) < 0.75:
        # Ensanchar primero, pero acotado a 2*h: ensanchar a ciegas hasta
        # img_w puede pasarse del máximo de 2:1 que se acaba de exigir arriba.
        ancho_deseado = min(img_w, 2.0 * h)
        if ancho_deseado > w:
            centro_x = (x0 + x1) / 2
            left = max(0.0, centro_x - ancho_deseado / 2)
            right = min(img_w, left + ancho_deseado)
            left = max(0.0, right - ancho_deseado)
            w = max(1.0, right - left)
        if (w / h) < 0.75:
            # Sigue siendo muy alto incluso al ancho máximo permitido:
            # recortar altura centrando la zona.
            target_h = w / 0.75
            centro_y = (y0 + y1) / 2
            top = max(0, centro_y - (target_h / 2))
            bottom = min(img_h, top + target_h)
            top = max(0, bottom - target_h)

            # Garantizar que el hallazgo no quede cortado por cumplir la proporción
            if top > y0:
                top = max(0, y0 - _PAD_MIN_Y)
            if bottom < y1:
                bottom = min(img_h, y1 + _PAD_MIN_Y)

    if right - left < 40 or bottom - top < 40:
        return None
    return int(left), int(top), int(right), int(bottom)


def anotar(
    origen: Path,
    destino: Path,
    hallazgos: list[Finding],
    movil: bool = False,
    pie: str | None = None,
) -> tuple[Path, int] | None:
    """Recorta la zona del problema principal, amplía y marca en rojo.

    Solo el hallazgo más prioritario decide el recorte; si otros hallazgos
    con zona caen dentro de ese recorte, también se numeran. Sin ninguna
    zona utilizable, se usa la captura completa tal cual (mejor eso que
    inventar un recorte sin nada que señalar) — pero eso significa que a
    veces no se dibuja ningún recuadro, solo el pie de foto. El segundo
    valor del tuple (cuántos recuadros se dibujaron de verdad) es lo que
    decide si el correo puede decir "con la zona marcada" o no: prometer
    una marca que no está ahí es la misma mentira detectable que prometer
    un adjunto que no existe.

    Regla dura: si el hallazgo que lidera `hallazgos` (el que el correo va a
    citar) no es de los que se pueden demostrar con un recuadro —ver
    `rules.DEMOSTRABLES`—, no se marca nada, aunque algún hallazgo secundario
    sí tenga zona. Dibujar una caja alrededor de "lo que sea que haya quedado
    grande" mientras el pie habla de segundos de carga o de SEO es peor que
    no marcar nada: es una prueba que el prospecto puede refutar mirando su
    propia pantalla.
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
    principal_demostrable = not hallazgos or es_demostrable(hallazgos[0])
    con_zona = [
        h for h in hallazgos
        if h.zona and h.zona.get("width") and h.zona.get("height") and h.viewport in (propio, "ambos")
    ] if principal_demostrable else []

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

    # P1: No agrandar nunca por encima del tamaño nativo
    factor = 1.0

    sombra_mask = Image.new("L", imagen.size, 140)
    mask_draw = ImageDraw.Draw(sombra_mask)

    capa = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    grosor = max(3, int(4 * escala * factor))
    fuente_badge = _fuente(int(20 * escala * factor))

    dibujados = 0
    for hallazgo in con_zona[:3]:
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

        # Spotlight: limpiar la sombra en esta zona
        mask_draw.rectangle([x0, y0, x1, y1], fill=0)
        # Borde rojo (ya no rellenamos de rojo suave porque el spotlight lo resalta)
        draw.rectangle([x0, y0, x1, y1], outline=ROJO + (255,), width=grosor)

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
        
        # P2: Numeración contigua de chapas
        etiqueta = str(dibujados + 1)
        ancho = _texto_ancho(draw, etiqueta, fuente_badge)
        draw.text((cx - ancho / 2, cy - radio * 0.72), etiqueta, font=fuente_badge, fill=BLANCO)
        dibujados += 1

    imagen = imagen.convert("RGBA")
    if dibujados > 0:
        sombra = Image.new("RGBA", imagen.size, (0, 0, 0, 255))
        sombra.putalpha(sombra_mask)
        imagen = Image.alpha_composite(imagen, sombra)

    imagen = Image.alpha_composite(imagen, capa).convert("RGB")

    # Pie de foto con el diagnóstico, para que la imagen se explique sola.
    texto_pie = pie or (con_zona[0].titulo if con_zona else (hallazgos[0].titulo if hallazgos else ""))
    if texto_pie:
        imagen = _con_pie(imagen, texto_pie, escala, factor)

    destino.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(destino, "PNG", optimize=True)
    log.debug("Captura anotada: %s (%s, %d marca%s)", destino.name,
              "recortada" if recorte else "completa", dibujados, "" if dibujados == 1 else "s")
    return destino, dibujados


def _con_pie(imagen, texto_pie: str, escala: float = 1.0, factor: float = 1.0):
    """Agrega debajo de la imagen la franja blanca con el pie de foto."""
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
    return lienzo


def anotar_overflow_movil(
    origen: Path,
    destino: Path,
    hallazgo: Finding,
    pie: str | None = None,
) -> tuple[Path, int] | None:
    """Anota la captura full_page de móvil para demostrar `overflow_mobile`.

    Acá no hay una zona puntual que recortar: el defecto ES que la página
    entera mide más que la pantalla del teléfono, así que no existe ningún
    rectángulo que "señalar" sin fabricar una caja decorativa (ver la regla
    dura en `anotar`). En vez de eso se marca dónde termina la pantalla real
    (390px) y se oscurece todo lo que sobra a la derecha de esa línea: eso
    es, literalmente, lo que el visitante tiene que desplazar en horizontal
    para leer. `origen` debe ser la captura con `full_page=True` — la única
    que conserva el ancho real (`scrollWidth`) en vez de recortarlo al ancho
    del viewport.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        log.warning("Pillow no está instalado: no se pueden anotar capturas")
        return None
    if not origen.exists():
        return None

    imagen_completa = Image.open(origen).convert("RGB")
    borde_x = MOBILE_VIEWPORT["width"] * MOBILE_DEVICE_SCALE
    if borde_x >= imagen_completa.width - 10:
        # La página ya no desborda en esta corrida (pudo cambiar entre la
        # medición y la captura): no hay nada real que sombrear.
        return None

    # Alto acotado al fold (con margen): interesa el sobrante ahí arriba,
    # no la altura entera de la página, que puede medir miles de píxeles y
    # volver el adjunto inservible en un cliente de correo.
    alto_recorte = min(imagen_completa.height, int(MOBILE_VIEWPORT["height"] * MOBILE_DEVICE_SCALE * 1.4))
    imagen = imagen_completa.crop((0, 0, imagen_completa.width, alto_recorte))

    ANCHO_MAX = 1200
    factor = ANCHO_MAX / imagen.width if imagen.width > ANCHO_MAX else 1.0
    if factor != 1.0:
        imagen = imagen.resize((int(imagen.width * factor), int(imagen.height * factor)), Image.LANCZOS)
    borde_x_img = borde_x * factor

    capa = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    # Todo lo que queda a la derecha del borde real del teléfono: oscurecido,
    # porque es exactamente la parte que no se ve sin desplazar la pantalla.
    draw.rectangle([borde_x_img, 0, imagen.width, imagen.height], fill=(10, 10, 10, 140))

    grosor = max(3, int(4 * factor))
    guion, hueco, y = 16, 9, 0.0
    while y < imagen.height:
        draw.line([borde_x_img, y, borde_x_img, min(y + guion, imagen.height)], fill=ROJO + (255,), width=grosor)
        y += guion + hueco

    ancho_sombra = imagen.width - borde_x_img
    if ancho_sombra > 90:
        fuente_etq = _fuente(max(13, int(16 * factor)))
        medidor = ImageDraw.Draw(capa)
        lineas = _envolver(medidor, "se sale de la pantalla", fuente_etq, int(ancho_sombra) - 16, max_lineas=3)
        alto_linea = int(20 * factor)
        y_txt = (imagen.height - alto_linea * len(lineas)) / 2
        for linea in lineas:
            ancho_l = _texto_ancho(medidor, linea, fuente_etq)
            x_txt = borde_x_img + (ancho_sombra - ancho_l) / 2
            draw.text((x_txt, y_txt), linea, font=fuente_etq, fill=BLANCO)
            y_txt += alto_linea

    imagen = Image.alpha_composite(imagen.convert("RGBA"), capa).convert("RGB")

    texto_pie = pie or hallazgo.titulo
    if texto_pie:
        imagen = _con_pie(imagen, texto_pie)

    destino.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(destino, "PNG", optimize=True)
    log.debug("Captura de desborde anotada: %s (ancho real %dpx vs pantalla %dpx)",
              destino.name, imagen_completa.width, borde_x)
    return destino, 1


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
