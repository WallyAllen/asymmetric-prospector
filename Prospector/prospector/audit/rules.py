"""Reglas de calificación: convierten señales medidas en argumentos de venta.

Filosofía (revisada tras auditar sitios reales que resultaban "críticos" sin
serlo): el score **no** es un índice general de calidad ni de buenas prácticas.
Mide una sola cosa: ¿esto le está costando clientes al negocio, hoy, de forma
demostrable? Una web puede tener detalles cosméticos de sobra (sin favicon,
meta description floja, menú con muchos ítems) y seguir siendo una landing
page perfectamente funcional que convierte. Eso no es un prospecto de valor.

Por eso cada regla se etiqueta con una `categoria`:
  · killer    → corta el embudo de conversión de raíz (nadie puede contactar,
                 nadie ve un CTA, el móvil no funciona, la web no carga).
                 Son las únicas que, solas o de a dos, cruzan el umbral de
                 "crítico". Pesos altos (18-38).
  · moderado  → fricción real pero no fatal; empeora la conversión sin matarla.
                 Pesos medios (4-10). Apilados sin ningún killer, como mucho
                 llegan a "mejorable".
  · cosmetico → detalles de pulido (SEO, favicon, alt text, menú largo). Pesan
                 poco o nada: no mueven el score, solo aportan color si ya hay
                 algo más grave que contar.

Cada `Finding` produce tres cosas:
  · evidencia  → el dato duro, irrefutable ("LCP 6.4 s en móvil")
  · argumento  → la traducción a dinero, que es lo que va al correo
  · zona       → el rectángulo que se marcará en rojo sobre la captura
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Iterable

from ..models import Finding
from .signals import ProbeResult

Regla = Callable[[ProbeResult], Finding | None]
_REGLAS: list[Regla] = []


def regla(func: Regla) -> Regla:
    _REGLAS.append(func)
    return func


def _rect(res: ProbeResult, nombre: str, movil: bool = False) -> dict | None:
    origen = (res.mobile if movil else res.desktop) or {}
    return (origen.get("rects") or {}).get(nombre)


# ═══════════════════════════ FILTRO PREVIO ═══════════════════════════
# Se evalúa antes que cualquier otra regla. Si la página no es la web
# de un negocio individual sino un directorio, no hay historia que contar.

@regla
def es_directorio(res: ProbeResult) -> Finding | None:
    """Detecta páginas que listan múltiples negocios (directorios/agregadores).

    Un directorio tiene: muchos teléfonos distintos, muchos emails distintos,
    y/o un título del estilo 'Mejores X en Y'. Con dos señales positivas basta.
    Un solo negocio raramente tiene más de 1-2 tel: y 1-2 mailto: en su web.
    """
    if not res.ok:
        return None
    met = res.metrics
    señales = 0
    evidencias: list[str] = []

    tels = met.tels_unicos or 0
    emails = met.emails_unicos or 0

    if tels > 3:
        señales += 1
        evidencias.append(f"{tels} números de teléfono distintos en la página")
    if emails > 2:
        señales += 1
        evidencias.append(f"{emails} direcciones de email distintas")
    if met.titulo_parece_directorio:
        señales += 1
        evidencias.append("título con patrón de directorio ('Mejores X en Y', 'Guía de...')")

    if señales < 2:
        return None

    return Finding(
        rule_id="es_directorio",
        titulo="La página es un directorio de negocios, no una web propia",
        severidad=0,
        peso=0,
        categoria="killer",
        evidencia=" · ".join(evidencias),
        argumento=(
            "Esta URL pertenece a un portal que lista múltiples negocios. "
            "No es un prospecto: no hay un dueño que necesite mejorar su landing."
        ),
    )


# ═══════════════════════════ KILLERS ═══════════════════════════
# Cortan el embudo. Uno solo ya empuja a "mejorable"; dos, a "crítico".

@regla
def sitio_inaccesible(res: ProbeResult) -> Finding | None:
    if res.ok and (res.metrics.http_status or 200) < 400:
        return None
    detalle = res.error or f"HTTP {res.metrics.http_status}"
    return Finding(
        rule_id="sitio_inaccesible",
        titulo="La web no responde correctamente",
        severidad=10,
        peso=100,
        categoria="killer",
        evidencia=detalle,
        argumento=(
            "Tu web no cargó al intentar entrar desde una conexión normal. "
            "El 100% de las visitas que se encuentran esto se van a la competencia y no vuelven."
        ),
    )


@regla
def sin_viewport(res: ProbeResult) -> Finding | None:
    if res.metrics.tiene_viewport_meta is not False:
        return None
    return Finding(
        rule_id="sin_viewport",
        titulo="La web no está adaptada a móvil",
        severidad=10,
        peso=38,
        categoria="killer",
        viewport="mobile",
        evidencia="Falta la etiqueta meta viewport: el móvil renderiza la versión de escritorio encogida",
        argumento=(
            "Quien entra desde el celular ve la web de escritorio miniaturizada, con el texto ilegible y "
            "obligado a hacer zoom para leer cualquier cosa. Eso es fricción antes de la primera frase."
        ),
        zona=_rect(res, "fold", movil=True),
    )


@regla
def sin_cta_en_fold(res: ProbeResult) -> Finding | None:
    if not res.ok:
        return None
    ctas = res.metrics.ctas_en_fold
    if ctas is None or ctas > 0:
        return None
    return Finding(
        rule_id="sin_cta_fold",
        titulo="Ningún llamado a la acción visible al entrar",
        severidad=10,
        peso=35,
        categoria="killer",
        evidencia="0 botones de acción en la primera pantalla",
        argumento=(
            "Al entrar no hay ni un botón que diga qué hacer: ni pedir cita, ni llamar, ni escribir. "
            "El visitante tiene que buscar cómo contactarte, y casi nadie se molesta en buscar."
        ),
        zona=_rect(res, "hero") or _rect(res, "fold"),
    )


@regla
def sin_vias_de_contacto(res: ProbeResult) -> Finding | None:
    if not res.ok:
        return None
    met = res.metrics
    if met.tiene_formulario or met.tiene_tel or met.tiene_whatsapp:
        return None
    return Finding(
        rule_id="sin_contacto",
        titulo="No hay forma rápida de contactar",
        severidad=9,
        categoria="killer",
        peso=35,
        evidencia="Sin formulario, sin teléfono pulsable ni WhatsApp en la página",
        argumento=(
            "No hay formulario, ni teléfono pulsable, ni WhatsApp. Quien quiere contratarte tiene que "
            "copiar un número a mano: la fricción justa para que lo deje para luego y no vuelva."
        ),
    )


@regla
def carga_lenta(res: ProbeResult) -> Finding | None:
    lcp = res.metrics.lcp_ms or res.metrics.load_ms
    if not lcp or lcp < 2500:
        return None
    segundos = lcp / 1000
    if segundos >= 4:
        severidad, peso, categoria = 9, 28, "killer"
        remate = "Google considera 'malo' todo lo que pase de 4 segundos, y lo castiga en el buscador."
    else:
        # Entre 2,5 y 4 s es fricción real, pero todavía dentro de lo tolerable:
        # no alcanza para llamarlo "el motivo" de que se pierdan clientes.
        severidad, peso, categoria = 5, 7, "moderado"
        remate = "El umbral que Google considera bueno son 2,5 segundos."
    return Finding(
        rule_id="carga_lenta",
        titulo=f"Tarda {segundos:.1f} s en mostrar el contenido principal",
        severidad=severidad,
        peso=peso,
        categoria=categoria,
        evidencia=f"LCP {segundos:.1f} s medido en una conexión normal",
        argumento=(
            f"Tu web tarda {segundos:.1f} segundos en mostrar lo importante, y eso lo medí yo mismo "
            f"entrando igual que entraría cualquiera. {remate}"
        ),
        zona=_rect(res, "imagenPrincipal"),
    )


@regla
def overflow_mobile(res: ProbeResult) -> Finding | None:
    if not res.metrics.overflow_horizontal_mobile:
        return None
    # Si ya no hay meta viewport, el desborde es consecuencia de eso y se penaliza
    # allí: no cobramos dos veces por el mismo defecto.
    if res.metrics.tiene_viewport_meta is False:
        return None
    ancho = res.metrics.ancho_scroll_mobile or 0
    return Finding(
        rule_id="overflow_mobile",
        titulo="El diseño se desborda en móvil",
        severidad=8,
        peso=22,
        categoria="killer",
        viewport="mobile",
        evidencia=f"El contenido mide {ancho}px de ancho en una pantalla de 390px",
        argumento=(
            "En el móvil hay que desplazarse en horizontal para leer: el contenido se sale de la pantalla. "
            "Es la señal más rápida de que una web está descuidada."
        ),
        zona=_rect(res, "fold", movil=True),
    )


@regla
def tecnologia_obsoleta(res: ProbeResult) -> Finding | None:
    d = res.desktop or {}
    motivos = []
    if d.get("flash"):
        motivos.append("componentes Flash (descontinuado desde 2020)")
    if (d.get("tablasLayout") or 0) > 0:
        motivos.append("maquetación con tablas HTML")
    if not motivos:
        return None
    return Finding(
        rule_id="tecnologia_obsoleta",
        titulo="Construida con técnicas obsoletas",
        severidad=8,
        peso=20,
        categoria="killer",
        evidencia="; ".join(motivos),
        argumento=(
            "La web está construida con técnicas que los navegadores actuales ya no soportan bien. "
            "No es cuestión de estética: partes del sitio directamente no funcionan."
        ),
    )


# ═══════════════════════════ MODERADOS ═══════════════════════════
# Fricción real. Apilados sin ningún killer, como mucho llegan a "mejorable".

@regla
def brochure_sin_propuesta(res: ProbeResult) -> Finding | None:
    if not res.ok:
        return None
    palabras = res.metrics.palabras_en_fold or 0
    ctas = res.metrics.ctas_en_fold or 0
    if palabras >= 12 or ctas > 0:
        return None
    return Finding(
        rule_id="fold_vacio",
        titulo="La primera pantalla no explica qué ofreces",
        severidad=7,
        peso=10,
        categoria="moderado",
        evidencia=f"Solo {palabras} palabras visibles al entrar, sin llamada a la acción",
        argumento=(
            "Lo primero que se ve es una imagen grande y poco más: en los 3 segundos que decide el visitante "
            "no hay ni una frase que diga qué haces ni por qué elegirte."
        ),
        zona=_rect(res, "hero") or _rect(res, "imagenPrincipal"),
    )


@regla
def sin_https(res: ProbeResult) -> Finding | None:
    if res.metrics.https is not False:
        return None
    return Finding(
        rule_id="sin_https",
        titulo="Sin certificado de seguridad (HTTPS)",
        severidad=7,
        peso=10,
        categoria="moderado",
        evidencia="La web se sirve por HTTP sin cifrar",
        argumento=(
            "El navegador marca tu web como «No segura» antes de que el visitante lea una sola palabra. "
            "Google además penaliza eso en el posicionamiento."
        ),
        zona=_rect(res, "nav"),
    )


@regla
def popup_intrusivo(res: ProbeResult) -> Finding | None:
    if not res.metrics.popup_intrusivo:
        return None
    return Finding(
        rule_id="popup_intrusivo",
        titulo="Un aviso tapa el contenido al entrar",
        severidad=6,
        peso=8,
        categoria="moderado",
        evidencia="Capa fija ocupando parte importante de la primera pantalla",
        argumento=(
            "Lo primero que ve el visitante no es tu oferta, es un aviso que tapa la pantalla y hay que cerrar. "
            "Se puede cumplir con la normativa sin sacrificar la primera impresión."
        ),
        zona=_rect(res, "popup"),
    )


@regla
def texto_ilegible_movil(res: ProbeResult) -> Finding | None:
    cantidad = res.metrics.texto_pequeno_mobile or 0
    if cantidad < 12:
        return None
    return Finding(
        rule_id="texto_pequeno_movil",
        titulo="Texto demasiado pequeño en móvil",
        severidad=5,
        peso=6,
        categoria="moderado",
        viewport="mobile",
        evidencia=f"{cantidad} bloques de texto por debajo de 13px",
        argumento=(
            "En el teléfono hay que ampliar con los dedos para leer buena parte de la página. "
            "Cada gesto extra es gente que abandona."
        ),
        zona=_rect(res, "fold", movil=True),
    )


@regla
def botones_pequenos(res: ProbeResult) -> Finding | None:
    cantidad = res.metrics.tap_targets_pequenos or 0
    if cantidad < 8:
        return None
    return Finding(
        rule_id="tap_targets",
        titulo="Botones difíciles de pulsar en móvil",
        severidad=5,
        peso=5,
        categoria="moderado",
        viewport="mobile",
        evidencia=f"{cantidad} enlaces o botones por debajo del tamaño mínimo táctil (40px)",
        argumento=(
            "Varios botones son tan pequeños que se fallan al pulsarlos con el dedo. "
            "Cuando el botón que falla es el de contacto, la venta se pierde ahí."
        ),
    )


@regla
def sin_telefono_pulsable(res: ProbeResult) -> Finding | None:
    met = res.metrics
    # El WhatsApp YA resuelve "contacto rápido desde el móvil": pedir un
    # tel: además de eso es nitpicking, no un defecto real (y decirle a
    # alguien "tu botón no se puede pulsar" cuando el de WhatsApp funciona
    # perfecto es un argumento falso que se detecta a la primera mirada).
    # Esto solo importa cuando la única vía de contacto es un formulario.
    if not res.ok or met.tiene_tel or met.tiene_whatsapp or not met.tiene_formulario:
        return None
    return Finding(
        rule_id="sin_tel_movil",
        titulo="El teléfono no se puede pulsar desde el móvil",
        severidad=5,
        peso=4,
        categoria="moderado",
        viewport="mobile",
        evidencia="Ningún enlace tel: ni de WhatsApp en la página, solo formulario",
        argumento=(
            "Desde el móvil, la única forma de contactar es completar un formulario: no hay teléfono "
            "ni WhatsApp para escribir directo. Un botón de llamada o de WhatsApp suele ser "
            "la mejora más rentable de toda la web."
        ),
    )


@regla
def layout_inestable(res: ProbeResult) -> Finding | None:
    cls = res.metrics.cls or 0
    if cls < 0.25:
        return None
    return Finding(
        rule_id="cls_alto",
        titulo="El contenido salta mientras carga",
        severidad=5,
        peso=5,
        categoria="moderado",
        evidencia=f"CLS de {cls:.2f} (Google considera aceptable por debajo de 0,1)",
        argumento=(
            "Mientras carga, los bloques se mueven de sitio: se acaba pulsando donde no era. "
            "Es de los errores que más irritan y Google lo mide explícitamente."
        ),
    )


@regla
def web_desactualizada(res: ProbeResult) -> Finding | None:
    ano = res.metrics.ano_copyright
    actual = date.today().year
    if not ano or ano >= actual - 1 or ano < 1995:
        return None
    return Finding(
        rule_id="copyright_viejo",
        titulo=f"El pie de página sigue anclado en {ano}",
        severidad=5,
        peso=5,
        categoria="moderado",
        evidencia=f"Copyright {ano} frente al año actual {actual}",
        argumento=(
            f"El pie de página dice {ano}. Para quien entra hoy es la señal de que el negocio "
            "puede estar cerrado o abandonado, aunque estéis funcionando a pleno rendimiento."
        ),
    )


# ═══════════════════════════ COSMÉTICOS ═══════════════════════════
# Pulido, no conversión. Pesan poco o nada: nunca definen el veredicto por
# sí solos, solo aportan color cuando ya hay algo más grave que contar.

@regla
def peso_excesivo(res: ProbeResult) -> Finding | None:
    kb = res.metrics.peso_kb or 0
    if kb < 3000:
        return None
    return Finding(
        rule_id="peso_excesivo",
        titulo="Página demasiado pesada",
        severidad=4,
        peso=4,
        categoria="cosmetico",
        evidencia=f"{kb / 1024:.1f} MB descargados en una sola visita ({res.metrics.peticiones or 0} peticiones)",
        argumento=(
            f"Cada visita descarga {kb / 1024:.1f} MB. Con datos móviles eso son varios segundos de espera "
            "y una factura de datos que el visitante nota."
        ),
    )


@regla
def imagenes_sin_optimizar(res: ProbeResult) -> Finding | None:
    sobredim = (res.desktop or {}).get("imagenesSobredimensionadas") or 0
    if sobredim < 3:
        return None
    return Finding(
        rule_id="imagenes_pesadas",
        titulo="Imágenes servidas mucho más grandes de lo necesario",
        severidad=3,
        peso=3,
        categoria="cosmetico",
        evidencia=f"{sobredim} imágenes con más del doble de resolución de la que se muestra",
        argumento=(
            "Se están sirviendo fotos de tamaño original y reduciéndolas por CSS. "
            "Es peso muerto que solo paga el visitante con su espera."
        ),
        zona=_rect(res, "imagenPrincipal"),
    )


@regla
def menu_sobrecargado(res: ProbeResult) -> Finding | None:
    items = res.metrics.items_menu or 0
    if items <= 9:
        return None
    return Finding(
        rule_id="menu_sobrecargado",
        titulo="Menú con demasiadas salidas",
        severidad=3,
        peso=3,
        categoria="cosmetico",
        evidencia=f"{items} enlaces en la navegación principal",
        argumento=(
            f"El menú ofrece {items} caminos distintos nada más entrar. Cada opción extra reparte la atención "
            "y aleja al visitante de la única acción que te interesa: que te contacte."
        ),
        zona=_rect(res, "nav"),
    )


@regla
def sin_identidad_seo(res: ProbeResult) -> Finding | None:
    if not res.ok:
        return None
    met = res.metrics
    fallos = []
    if not met.title or len(met.title) < 15:
        fallos.append("título de página vacío o genérico")
    if not met.meta_description:
        fallos.append("sin descripción para Google")
    if not met.og_image:
        fallos.append("sin imagen de previsualización al compartir")
    if (met.h1 or 0) == 0:
        fallos.append("sin titular H1")
    if len(fallos) < 2:
        return None
    return Finding(
        rule_id="seo_basico",
        titulo="Le faltan los básicos para posicionar y compartirse",
        severidad=4,
        peso=3,
        categoria="cosmetico",
        evidencia="; ".join(fallos),
        argumento=(
            "Faltan los elementos básicos que Google usa para entender la página, y al compartir el enlace "
            "por WhatsApp aparece sin imagen ni descripción: parece un enlace sospechoso."
        ),
    )


@regla
def accesibilidad_imagenes(res: ProbeResult) -> Finding | None:
    d = res.desktop or {}
    total, sin_alt = d.get("imagenes") or 0, d.get("imagenesSinAlt") or 0
    if total < 5 or sin_alt / max(total, 1) < 0.6:
        return None
    return Finding(
        rule_id="imagenes_sin_alt",
        titulo="Imágenes sin texto alternativo",
        severidad=3,
        peso=2,
        categoria="cosmetico",
        evidencia=f"{sin_alt} de {total} imágenes sin atributo alt",
        argumento=(
            "Las imágenes no tienen descripción: Google no sabe qué muestran y quien usa lector de pantalla "
            "no puede navegar la web. Además incumple los requisitos de accesibilidad."
        ),
    )


@regla
def sin_favicon(res: ProbeResult) -> Finding | None:
    if res.metrics.favicon is not False:
        return None
    return Finding(
        rule_id="sin_favicon",
        titulo="Sin icono en la pestaña del navegador",
        severidad=2,
        peso=0,
        categoria="cosmetico",
        evidencia="No hay favicon declarado",
        argumento=(
            "En la pestaña del navegador tu web aparece con el icono en blanco por defecto: "
            "un detalle pequeño que resta profesionalidad frente a la competencia."
        ),
    )


# ═══════════════════════════ Veredicto ═══════════════════════════
# Calibrado para que:
#   · el pulido cosmético apilado entero (sin ningún killer/moderado) no
#     pase de "sano" — no se contacta a nadie por no tener favicon.
#   · una pila de fricciones moderadas sin ningún killer llegue como mucho
#     a "mejorable" — hay margen, pero no es una urgencia.
#   · haga falta un killer real (o dos moderados fuertes) para cruzar a
#     "crítico": ahí es donde el negocio pierde clientes de forma medible.
VEREDICTOS = (
    (65, "critico"),
    (28, "mejorable"),
    (0, "sano"),
)


def evaluar(res: ProbeResult) -> tuple[int, str, list[Finding]]:
    """Aplica todas las reglas y devuelve (score, veredicto, hallazgos)."""
    hallazgos: list[Finding] = []
    for regla_fn in _REGLAS:
        try:
            hallazgo = regla_fn(res)
        except Exception:  # noqa: BLE001 - una regla rota no invalida la auditoría
            continue
        if hallazgo:
            hallazgos.append(hallazgo)

    inaccesible = next((h for h in hallazgos if h.rule_id == "sitio_inaccesible"), None)
    if inaccesible:
        return 95, "inaccesible", hallazgos

    score = min(100, sum(h.peso for h in hallazgos))
    veredicto = next(nombre for umbral, nombre in VEREDICTOS if score >= umbral)
    return score, veredicto, hallazgos


def finding_sin_web(nombre: str) -> Finding:
    """El prospecto ideal: ficha en Maps y ninguna web detrás."""
    return Finding(
        rule_id="sin_web",
        titulo="El negocio no tiene web",
        severidad=10,
        peso=100,
        categoria="killer",
        evidencia="Ficha en Google Maps sin sitio web asociado",
        argumento=(
            f"{nombre} aparece en Google Maps sin ninguna web enlazada. Quien os busca por el nombre "
            "encuentra la ficha, no encuentra precios, servicios ni forma de reservar, y termina "
            "entrando en la web del competidor que sí la tiene."
        ),
    )


def resumen(hallazgos: Iterable[Finding], maximo: int = 3) -> str:
    ordenados = sorted(hallazgos, key=lambda f: (-f.severidad, -f.peso))[:maximo]
    return " · ".join(h.titulo for h in ordenados)
