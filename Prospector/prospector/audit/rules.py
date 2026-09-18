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

Cada `Finding` produce:
  · evidencia     → el dato duro, irrefutable ("LCP 6,4 s en el celular")
  · observacion   → lo que SE VE, sin consecuencia. Es la primera línea del mensaje.
  · consecuencia  → la traducción a clientes perdidos. Se dice UNA vez.
  · puente        → la transición hacia la oferta, propia de ESTE defecto.
  · zona          → el rectángulo que se marcará en rojo sobre la captura

Las tres piezas de texto van partidas a propósito: cuando eran un párrafo
único (`argumento`), `writer.py` tenía que agregar detrás su propia
consecuencia genérica —siempre la misma, siempre sobre el botón de contacto—
y salían dos consecuencias por mensaje, la segunda muchas veces sin relación
con el hallazgo. `Finding` deriva `argumento` solo, para compatibilidad.

Dialecto: todo esto se escribe **en rioplatense y en segunda persona del
singular (vos)**, que es el registro del remitente. Antes estaba en español
peninsular ("pulsar", "estéis", "os busca", "se mueven de sitio") y lo
traducía `writer.SLOP_VOSEO` a la salida: una traducción de última milla que
cubría las conjugaciones pero no el léxico, y que en un caso ("estéis" →
"estén") metía un plural dentro de un texto en singular. El filtro sigue ahí
como red de seguridad para lo que venga de la IA, no como traductor.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Iterable

from ..models import Finding
from .signals import ProbeResult

Regla = Callable[[ProbeResult], Finding | None]
_REGLAS: list[Regla] = []

# Hallazgos cuya "zona" se puede demostrar con una captura: son defectos que
# SE VEN — un botón que falta, un texto chico, un popup tapando la pantalla.
# El resto (carga_lenta, cls_alto, seo_basico, sin_contacto, peso_excesivo...)
# son medidas de tiempo, código o ausencia de algo: no hay ningún rectángulo
# de píxeles que los demuestre, aunque la regla tenga un `zona` calculado
# (p. ej. "la imagen más grande del fold" para carga_lenta). Dibujar un
# recuadro ahí no prueba nada — es una caja decorativa alrededor de lo que
# sea que haya quedado más grande, y el prospecto lo detecta a la primera
# mirada. Ver `capture.anotar`: cuando el hallazgo principal no está en este
# conjunto, no se marca ningún recuadro.
DEMOSTRABLES = frozenset({
    "sin_cta_fold",
    "popup_intrusivo",
    "texto_pequeno_movil",
    "sin_viewport",
    "overflow_mobile",
    # El jurado visual (vision.py) recibe la captura y señala DENTRO de ella
    # dónde está el problema: su zona no es una aproximación, es literalmente
    # el punto que un humano miró y marcó. Distinto de una regla que calcula
    # "la imagen más grande del fold" sin haber visto si eso prueba algo.
    "jurado_visual",
})


def es_demostrable(finding: Finding) -> bool:
    return finding.rule_id in DEMOSTRABLES


def regla(func: Regla) -> Regla:
    _REGLAS.append(func)
    return func


def _coma(valor: float, decimales: int = 1) -> str:
    """Decimal con coma: es un texto en español y se lee en un celular.

    `f"{7.5:.1f}"` daba "7.5 segundos" dentro de un mensaje que a cuatro
    líneas de distancia escribía el rating como "4,8". Dos separadores
    decimales distintos en el mismo párrafo es de las cosas que más rápido
    delatan que el texto lo armó un programa.
    """
    return f"{valor:.{decimales}f}".replace(".", ",")


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
        observacion="Esta URL pertenece a un portal que lista múltiples negocios.",
        consecuencia="No es un prospecto: no hay un dueño que necesite mejorar su landing.",
    )


# ═══════════════════════════ KILLERS ═══════════════════════════
# Cortan el embudo. Uno solo ya empuja a "mejorable"; dos, a "crítico".

@regla
def sitio_inaccesible(res: ProbeResult) -> Finding | None:
    if res.ok and (res.metrics.http_status or 200) < 400:
        return None
    # El dominio resuelve pero el navegador no pudo entrar: puede ser un
    # tropiezo de red, un TLS raro, un timeout o un bloqueo antibot. No es
    # "tu web está caída", y decírselo al dueño es una afirmación que
    # desmiente abriendo su propia web. Se maneja como medición fallida
    # (ver `evaluar`), no como hallazgo.
    if res.dns_ok:
        return None
    detalle = res.error or f"HTTP {res.metrics.http_status}"
    return Finding(
        rule_id="sitio_inaccesible",
        titulo="La web no responde correctamente",
        severidad=10,
        peso=100,
        categoria="killer",
        evidencia=detalle,
        observacion="tu web no cargó cuando intenté entrar, con una conexión normal",
        consecuencia="el que llega ahí no vuelve a probar: se va al siguiente resultado y no vuelve",
        puente="si venció el dominio o el hosting, o hay un error de configuración, suele ser rápido de resolver",
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
        evidencia="Falta la etiqueta meta viewport: el celular muestra la versión de escritorio encogida",
        observacion="desde el celular se ve la web de escritorio miniaturizada, con el texto ilegible",
        consecuencia="hay que hacer zoom con los dedos para leer cualquier cosa, y eso espanta antes de la primera frase",
        puente="adaptarla al celular es lo que más mueve la aguja acá, y no implica rehacer el diseño",
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
        observacion="al entrar no hay ningún botón que diga qué hacer: ni turno, ni llamar, ni escribir",
        consecuencia="el que entra tiene que ponerse a buscar cómo contactarte, y casi nadie busca",
        puente="poner un botón visible arriba de todo es lo primero que suelo mover, y se nota enseguida",
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
        evidencia="Sin formulario, sin teléfono para tocar ni WhatsApp en la página",
        observacion="no hay formulario, ni teléfono para tocar, ni WhatsApp",
        consecuencia="el que te quiere contratar tiene que copiar el número a mano, y ahí lo deja para después",
        puente="un botón de WhatsApp arriba suele ser el arreglo más rentable de toda la web",
    )


@regla
def carga_lenta(res: ProbeResult) -> Finding | None:
    lcp = res.metrics.lcp_ms or res.metrics.load_ms
    if not lcp or lcp < 2500:
        return None
    segundos = lcp / 1000
    if segundos >= 4:
        severidad, peso, categoria = 9, 28, "killer"
        remate = "Google considera «malo» todo lo que pase de 4 segundos y lo baja en el buscador"
    else:
        # Entre 2,5 y 4 s es fricción real, pero todavía dentro de lo tolerable:
        # no alcanza para llamarlo "el motivo" de que se pierdan clientes.
        severidad, peso, categoria = 5, 7, "moderado"
        remate = "el umbral que Google considera bueno son 2,5 segundos"
    return Finding(
        rule_id="carga_lenta",
        titulo=f"Tarda {_coma(segundos)} s en mostrar el contenido principal",
        severidad=severidad,
        peso=peso,
        categoria=categoria,
        evidencia=f"LCP {_coma(segundos)} s medido en una conexión normal",
        observacion=(
            f"tu web tarda {_coma(segundos)} segundos en mostrar lo importante, "
            f"y lo medí entrando igual que entraría cualquiera"
        ),
        consecuencia=remate,
        puente="casi siempre es peso de imágenes, y se corrige sin tocar el diseño",
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
        observacion="en el celular hay que arrastrar para los costados para leer: el contenido se sale de la pantalla",
        consecuencia="es la señal más rápida de que una web está descuidada, y se ve en los primeros dos segundos",
        puente="ordenar el ancho en el celular es un arreglo acotado, no un rediseño",
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
        observacion="la web está armada con técnicas que los navegadores de hoy ya no soportan bien",
        consecuencia="no es una cuestión de estética: hay partes del sitio que directamente no funcionan",
        puente="rehacer la portada con lo de hoy es más barato que parchar lo viejo",
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
        titulo="La primera pantalla no explica qué ofrecés",
        severidad=7,
        peso=10,
        categoria="moderado",
        evidencia=f"Solo {palabras} palabras visibles al entrar, sin llamada a la acción",
        observacion="lo primero que se ve es una imagen grande y poco más",
        consecuencia="en los tres segundos en que se decide el que entra no hay ni una frase que diga qué hacés ni por qué elegirte",
        puente="con un titular claro y un botón, esa misma pantalla empieza a trabajar",
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
        observacion="el navegador marca tu web como «No segura» antes de que se lea una sola palabra",
        consecuencia="mucha gente se vuelve ahí mismo, y además Google lo penaliza en el posicionamiento",
        puente="el certificado suele ser gratis y se activa en el panel del hosting",
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
        observacion="lo primero que aparece no es tu oferta, es un aviso que tapa la pantalla y hay que cerrar",
        consecuencia="se pierde la primera impresión justo en el segundo en que se decide si quedarse",
        puente="se puede cumplir con la normativa sin comerse la portada",
        zona=_rect(res, "popup"),
    )


@regla
def texto_ilegible_movil(res: ProbeResult) -> Finding | None:
    cantidad = res.metrics.texto_pequeno_mobile or 0
    if cantidad < 12:
        return None
    return Finding(
        rule_id="texto_pequeno_movil",
        titulo="Texto demasiado chico en el celular",
        severidad=5,
        peso=6,
        categoria="moderado",
        viewport="mobile",
        evidencia=f"{cantidad} bloques de texto por debajo de 13px",
        observacion="en el celular hay que agrandar con los dedos para leer buena parte de la página",
        consecuencia="cada gesto de más es gente que abandona antes de llegar al contacto",
        puente="subir el cuerpo de texto es un cambio de minutos",
        zona=_rect(res, "fold", movil=True),
    )


@regla
def botones_pequenos(res: ProbeResult) -> Finding | None:
    cantidad = res.metrics.tap_targets_pequenos or 0
    if cantidad < 8:
        return None
    return Finding(
        rule_id="tap_targets",
        titulo="Botones difíciles de tocar en el celular",
        severidad=5,
        peso=5,
        categoria="moderado",
        viewport="mobile",
        evidencia=f"{cantidad} enlaces o botones por debajo del tamaño mínimo táctil (40px)",
        observacion="varios botones son tan chicos que se fallan al tocarlos con el dedo",
        consecuencia="cuando el que falla es el de contacto, la consulta se pierde ahí mismo",
        puente="agrandar el área táctil de los botones es un arreglo de un rato",
    )


@regla
def sin_telefono_pulsable(res: ProbeResult) -> Finding | None:
    met = res.metrics
    # El WhatsApp YA resuelve "contacto rápido desde el celular": pedir un
    # tel: además de eso es nitpicking, no un defecto real (y decirle a
    # alguien "tu botón no se puede tocar" cuando el de WhatsApp funciona
    # perfecto es un argumento falso que se detecta a la primera mirada).
    # Esto solo importa cuando la única vía de contacto es un formulario.
    if not res.ok or met.tiene_tel or met.tiene_whatsapp or not met.tiene_formulario:
        return None
    return Finding(
        rule_id="sin_tel_movil",
        titulo="El teléfono no se puede tocar desde el celular",
        severidad=5,
        peso=4,
        categoria="moderado",
        viewport="mobile",
        evidencia="Ningún enlace tel: ni de WhatsApp en la página, solo formulario",
        observacion="desde el celular la única forma de contactarte es llenar un formulario",
        consecuencia="no hay teléfono ni WhatsApp para escribir directo, y esa vuelta la abandona mucha gente",
        puente="un botón de llamada o de WhatsApp suele ser el arreglo más rentable de toda la web",
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
        evidencia=f"CLS de {_coma(cls, 2)} (Google considera aceptable por debajo de 0,1)",
        observacion="mientras carga, los bloques se mueven de lugar y terminás tocando donde no era",
        consecuencia="es de los errores que más irritan, y Google lo mide aparte",
        puente="se arregla reservando el espacio de las imágenes, sin tocar el diseño",
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
        observacion=f"el pie de página sigue diciendo {ano}",
        consecuencia=(
            "para el que entra hoy es la señal de que el negocio puede estar cerrado, "
            "aunque estés trabajando a full"
        ),
        puente="es de las cosas que menos cuestan arreglar y más rápido se notan",
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
        evidencia=f"{_coma(kb / 1024)} MB descargados en una sola visita ({res.metrics.peticiones or 0} peticiones)",
        observacion=f"cada visita se descarga {_coma(kb / 1024)} MB",
        consecuencia="con datos móviles eso son varios segundos de espera y un consumo que se nota",
        puente="comprimir las imágenes baja eso a una fracción sin perder calidad",
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
        observacion="se están sirviendo las fotos en tamaño original y achicándolas por CSS",
        consecuencia="es peso muerto que paga el que entra, con su espera",
        puente="servirlas al tamaño real es automático y no cambia nada visual",
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
        observacion=f"el menú ofrece {items} caminos distintos apenas entrás",
        consecuencia="cada opción de más reparte la atención y aleja de la única acción que te interesa: que te escriban",
        puente="recortar el menú a lo que de verdad usan es gratis y ordena la portada",
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
        observacion="faltan los datos básicos que Google usa para entender la página",
        consecuencia="al compartir el enlace por WhatsApp aparece sin imagen ni descripción, y se lee como un link sospechoso",
        puente="son cuatro etiquetas en el HTML, se resuelve de una vez",
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
        observacion="las imágenes no tienen descripción",
        consecuencia="Google no sabe qué muestran y quien usa lector de pantalla no puede navegar la web",
        puente="completar los textos alternativos es mecánico y suma en el buscador",
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
        observacion="en la pestaña del navegador tu web aparece con el ícono en blanco",
        consecuencia="es un detalle chico que resta al lado de la competencia",
        puente="es subir un archivo de 32 píxeles",
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

    # Ni cargó ni se pudo descartar que sea culpa nuestra: no hay nada medido
    # que contar, así que no hay prospecto. Score 0 para que el umbral lo
    # descarte solo, y un veredicto propio para poder reintentarlo después.
    if not res.ok:
        return 0, "no_medido", hallazgos

    score = min(100, sum(h.peso for h in hallazgos))
    veredicto = next(nombre for umbral, nombre in VEREDICTOS if score >= umbral)
    return score, veredicto, hallazgos


def finding_sin_web(nombre: str) -> Finding:
    """El prospecto ideal: ficha en Maps y ninguna web detrás.

    Este texto es descriptivo y va al informe HTML y al prompt de la IA, en
    tercera persona. El mensaje que se le manda al prospecto NO se arma acá:
    lo arma `compose/` con el vocabulario del rubro ("no encuentra cómo sacar
    un turno" para una veterinaria, "cómo pedir un presupuesto" para un
    taller), que es dato que la auditoría no tiene. Es la única redacción
    duplicada del sistema y es deliberada; cualquier otra hay que unificarla.
    """
    return Finding(
        rule_id="sin_web",
        titulo="El negocio no tiene web",
        severidad=10,
        peso=100,
        categoria="killer",
        evidencia="Ficha en Google Maps sin sitio web asociado",
        observacion=f"{nombre} aparece en Google Maps sin ninguna web enlazada",
        consecuencia=(
            "quien lo busca ve la ficha, no encuentra ni los servicios ni cómo reservar, "
            "y termina entrando en la del competidor que sí la tiene"
        ),
        puente="una página de una sola pantalla alcanza para cortar esa fuga",
    )


def resumen(hallazgos: Iterable[Finding], maximo: int = 3) -> str:
    ordenados = sorted(hallazgos, key=lambda f: (-f.severidad, -f.peso))[:maximo]
    return " · ".join(h.titulo for h in ordenados)
