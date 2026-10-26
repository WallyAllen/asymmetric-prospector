"""Vocabulario del prospecto y elección determinista de variantes.

Dos problemas del motor anterior se resuelven acá:

1. **Todos los rubros hablaban igual.** A una veterinaria, a un estudio
   contable y a una inmobiliaria se les decía la misma frase: "forma de
   reservar", "cómo contactar". El `nicho` —que es la consulta tal como se
   tipeó en el buscador— ya trae el rubro y la ciudad adentro y nadie los
   usaba. Es la única personalización disponible para el 73% del segmento de
   WhatsApp, que no tiene web y por lo tanto no tiene hallazgos que contar.

2. **La variación venía de `random.choice`.** Eso hace que el mismo lead
   recompuesto (`compose --forzar`) cambie de texto, que no se pueda
   reproducir un mensaje ya mandado, y que el reparto entre variantes sea
   parejo solo en promedio. Acá se elige por hash estable del id del lead:
   mismo lead, mismo texto, siempre; y reparto plano por construcción.

`hash()` de Python NO sirve para esto: está aleatorizado por proceso
(PYTHONHASHSEED), así que daría un texto distinto en cada corrida. Se usa
sha1, que es estable entre procesos y entre máquinas.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence
from ..utils import es_indumentaria


# ─────────────────────────────── Elección determinista ───────────────────────────────

def _semilla(*partes: str) -> int:
    crudo = "|".join(p or "" for p in partes).encode("utf-8")
    return int.from_bytes(hashlib.sha1(crudo).digest()[:4], "big")


def elegir(opciones: Sequence[str], *partes: str) -> str:
    """Una opción estable para esta combinación de semillas.

    `partes` suele ser (lead.id, "apertura"): el id fija el lead y la etiqueta
    hace que dos ranuras distintas del mismo mensaje no elijan siempre el
    mismo índice (que produciría "variante 2 en todo" para un lead y
    "variante 0 en todo" para otro, o sea tres mensajes distintos en vez de
    3×3×3).
    """
    if not opciones:
        return ""
    return opciones[_semilla(*partes) % len(opciones)]


# ─────────────────────────────── Normalización ───────────────────────────────

def _plano(texto: str) -> str:
    """Minúsculas sin tildes, para comparar 'Odontologia' con 'odontología'."""
    limpio = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return limpio.lower().strip()


# ─────────────────────────────── Rubros ───────────────────────────────

@dataclass(frozen=True, slots=True)
class Rubro:
    """Cómo habla el dueño de este negocio de lo que le pasa.

    · `plural`  → cómo nombrar el rubro en una búsqueda ("veterinarias")
    · `accion`  → lo que el cliente quiere hacer y no puede ("sacar un turno")
    · `no_ve`   → lo que no encuentra en la ficha de Maps ("los servicios ni los horarios")
    · `cliente` → cómo llamar a quien busca ("el que necesita un veterinario")
    """

    plural: str
    accion: str
    no_ve: str
    cliente: str


GENERICO = Rubro(
    plural="servicios de la zona",
    accion="ponerse en contacto",
    no_ve="qué hacen ni cómo contactarlos",
    cliente="el que los busca",
)

INDUMENTARIA = Rubro(
    plural="tiendas de ropa",
    accion="elegir una prenda y hacer un pedido",
    no_ve="las prendas, los talles disponibles ni cómo hacer un pedido",
    cliente="el que está buscando ropa",
)

# Se recorre en orden: la primera clave contenida en el nicho gana. Por eso las
# claves más específicas van antes que las genéricas ("clinica veterinaria"
# tiene que resolver a veterinaria, no a clínica médica).
_RUBROS: tuple[tuple[tuple[str, ...], Rubro], ...] = (
    (("veterinaria", "veterinario", "mascota", "pet shop"), Rubro(
        plural="veterinarias",
        accion="sacar un turno",
        no_ve="los horarios, si hay urgencias ni cómo sacar turno",
        cliente="el que tiene la mascota enferma")),
    (("odontolog", "dentista", "dental"), Rubro(
        plural="consultorios de odontología",
        accion="pedir un turno",
        no_ve="los tratamientos, las obras sociales ni cómo pedir turno",
        cliente="el que anda con dolor de muelas")),
    (("fisioterapia", "kinesiolog", "kinesio", "rehabilitacion"), Rubro(
        plural="centros de fisioterapia",
        accion="pedir un turno",
        no_ve="los tratamientos, las obras sociales ni cómo sacar turno",
        cliente="el que sale del traumatólogo con una orden")),
    (("academia", "ingles", "idiomas", "instituto", "curso"), Rubro(
        plural="academias de inglés",
        accion="preguntar por horarios y precios",
        no_ve="los cursos, los horarios ni cuánto sale",
        cliente="el que está buscando dónde anotarse")),
    (("inmobiliaria", "propiedades", "bienes raices"), Rubro(
        plural="inmobiliarias",
        accion="consultar por una propiedad",
        no_ve="las propiedades ni cómo consultar por una",
        cliente="el que está buscando dónde mudarse")),
    (("abogado", "juridico", "legal", "estudio juridico"), Rubro(
        plural="estudios jurídicos",
        accion="pedir una consulta",
        no_ve="en qué se especializan ni cómo pedir una consulta",
        cliente="el que tiene un problema y no sabe a quién llamar")),
    (("contador", "contable", "impuesto"), Rubro(
        plural="estudios contables",
        accion="pedir una consulta",
        no_ve="qué servicios dan ni cómo pedir una consulta",
        cliente="el monotributista que necesita ordenarse")),
    (("taller", "mecanic", "automotor", "gomeria", "repuesto"), Rubro(
        plural="talleres",
        accion="pedir un presupuesto",
        no_ve="qué arreglan, si atienden su marca ni cómo pedir presupuesto",
        cliente="el que tiene el auto parado")),
    (("agencia", "marketing", "publicidad", "diseño web", "diseno web"), Rubro(
        plural="agencias",
        accion="pedir un presupuesto",
        no_ve="qué hacen, para quién trabajaron ni cómo pedirles presupuesto",
        cliente="el que está buscando con quién trabajar")),
    (("reforma", "construc", "albañil", "albanil", "pintura", "plomer"), Rubro(
        plural="reformas",
        accion="pedir un presupuesto",
        no_ve="qué trabajos hacen ni cómo pedir un presupuesto",
        cliente="el que quiere arreglar la casa")),
    (("estetica", "belleza", "peluquer", "spa", "wellness"), Rubro(
        plural="centros de estética",
        accion="sacar un turno",
        no_ve="los tratamientos, los precios ni cómo sacar turno",
        cliente="el que está eligiendo dónde ir")),
    (("clinica", "medic", "salud", "consultorio", "laboratorio"), Rubro(
        plural="centros de salud",
        accion="sacar un turno",
        no_ve="las especialidades, las obras sociales ni cómo sacar turno",
        cliente="el que necesita atenderse")),
)


def rubro_de(nicho: str | None, nombre: str = "") -> Rubro:
    """El vocabulario del rubro, o el genérico si no se reconoce.

    Degradación elegante a propósito: un nicho nuevo no rompe la redacción,
    solo la deja tan genérica como estaba antes de existir este módulo.
    """
    texto = _plano(nicho or "")
    if es_indumentaria(nicho or ""):
        return INDUMENTARIA
    for claves, rubro in _RUBROS:
        if any(clave in texto for clave in claves):
            if "contable" in claves and re.search(r"\b(asociados|srl|s\.r\.l|sa|s\.a)\b", _plano(nombre)):
                return Rubro(rubro.plural, rubro.accion, rubro.no_ve,
                             "la empresa que necesita llevar la contabilidad al día")
            return rubro
    return GENERICO


# ─────────────────────────────── Ciudades ───────────────────────────────

# El nicho se tipea como "veterinarias La Plata": la ciudad va al final y no
# hay separador. Se buscan por lista porque partir por palabras es frágil
# (una ciudad de tres palabras como "San Miguel de Tucumán" se rompe sola).
# Las compuestas van primero para que "Mar del Plata" gane sobre "La Plata".
_CIUDADES: tuple[str, ...] = (
    "San Miguel de Tucumán", "Mar del Plata", "Bahía Blanca", "Buenos Aires",
    "La Plata", "Villa Carlos Paz", "San Isidro", "Santa Fe", "La Rioja",
    "Córdoba", "Mendoza", "Rosario", "Salta", "Quilmes", "Tucumán", "Neuquén",
    "Corrientes", "Posadas", "Resistencia", "San Juan", "San Luis", "Paraná",
    "Barcelona", "Madrid", "Valencia", "Sevilla", "Zaragoza", "Bilbao",
)


def ciudad_de(nicho: str | None) -> str:
    """La ciudad del nicho, bien escrita, o "" si no se reconoce.

    Devuelve la forma canónica de la lista, no la que tipeó el usuario: el
    nicho real del corpus incluye "dentistas en mar del plata" y
    "Odontologia estética La Plata". Citarlo crudo entre comillas —como hacía
    `_termino_busqueda()`— metía en el mensaje los errores de tipeo propios.
    """
    texto = _plano(nicho or "")
    for ciudad in _CIUDADES:
        if _plano(ciudad) in texto:
            return ciudad
    return ""


def busqueda_de(nicho: str | None) -> str:
    """Cómo referirse a la búsqueda que llevó hasta el prospecto.

    "veterinarias en La Plata", no '"veterinarias La Plata"'. Sin comillas,
    con preposición y con la ciudad bien escrita.
    """
    rubro = rubro_de(nicho)
    ciudad = ciudad_de(nicho)
    return f"{rubro.plural} en {ciudad}" if ciudad else rubro.plural


# ─────────────────────────────── Toque 1 por WhatsApp: inmobiliarias ───────────────────────────────
# Spec 009. La v4 (125 mensajes en cola) abría describiendo la portada, cerraba
# preguntando qué sistema usaban y tres rechazos contestaron "ya tenemos CRM":
# la pregunta les servía de salida. Acá lidera una falla que se comprueba
# abriendo la web, y la consecuencia está escrita para una inmobiliaria.
# `{v}`/`{vc}` salen de VERBO/VERBO_CELU, `{d}` es el dominio, `{s}` los segundos.

VERBO = ("Entré a {d}", "Abrí {d}", "Miré {d}")
VERBO_CELU = ("Entré a {d} desde el celu", "Abrí {d} en el celu", "Miré {d} desde el celular")

SALUDOS_V5 = ("Hola, ¿qué tal?", "Hola, buenas.", "Hola, ¿cómo va?", "Buenas, ¿qué tal?")
PRESENTACIONES_V5 = (
    "Soy {nombre}, hago webs para {plural}.",
    "Soy {nombre} y armo webs para {plural}.",
    "Te escribo por algo puntual. Soy {nombre}, hago webs para {plural}.",
    "Me llamo {nombre} y trabajo haciendo webs de {plural}.",
    "Soy {nombre}, diseño webs para {plural}.",
)

OBSERVACION = {
    "carga_lenta": (
        "{v} y tardó {s} segundos en mostrar algo.",
        "{v} y la portada tardó {s} segundos en aparecer, con una conexión normal.",
        "{v}: {s} segundos hasta que se ve la portada.",
    ),
    "sin_contacto": (
        "{v} y no encontré cómo consultar: no hay formulario, ni teléfono para tocar, ni WhatsApp.",
        "{v} y no hay forma de consultar desde la web: ni WhatsApp, ni teléfono para tocar, ni formulario.",
    ),
    "sin_tel_movil": (
        "{vc} y la única forma de consultar es un formulario: no hay WhatsApp ni teléfono para tocar.",
        "{vc} y para consultar hay que llenar un formulario; no hay botón de WhatsApp ni de llamar.",
    ),
    "overflow_mobile": (
        "{vc} y la página se sale de la pantalla: hay que arrastrar para los costados para leer.",
        "{vc} y queda más ancha que la pantalla, así que se lee cortada.",
    ),
    "sin_viewport": (
        "{vc} y se ve la web de la compu en miniatura: hay que hacer zoom para leer.",
        "{vc} y aparece la versión de escritorio achicada; sin zoom no se lee.",
    ),
    "popup_intrusivo": (
        "{v} y lo primero que aparece es un aviso que tapa la pantalla y hay que cerrar.",
    ),
    "sitio_inaccesible": (
        "Quise entrar a {d} y no cargó, probé dos veces.",
    ),
}

# El que más pesa para una inmobiliaria es el propietario que quiere vender: llega
# recomendado y mira la web antes de llamar. El comprador consulta en el portal.
CONSECUENCIA_INMOBILIARIA = {
    "carga_lenta": (
        "El propietario que te recomendaron entra a mirarte antes de llamar, y lo primero que ve es la espera.",
        "El que busca casa tiene diez pestañas abiertas y cierra la que tarda.",
        "En ese tiempo, el que estaba mirando una propiedad ya volvió atrás.",
        "El que está eligiendo a quién darle su casa para vender compara dos o tres webs, y la que tarda queda última.",
    ),
    "sin_contacto": (
        "El que ve una casa que le gusta tiene que salir a buscar tu número, y casi siempre lo deja para después.",
        "El propietario que te recomendaron entra a mirarte y no tiene cómo escribirte desde ahí.",
    ),
    "sin_tel_movil": (
        "El que mira casas desde el celu quiere escribir por WhatsApp y listo; un formulario lo deja para después.",
        "El que encontró la casa que buscaba quiere preguntar ya, y un formulario lo enfría.",
    ),
    "overflow_mobile": (
        "Casi todo el que busca casa lo hace desde el celu, y lo ve roto en los primeros segundos.",
        "El propietario que te recomendaron entra a mirarte desde el celu y se lleva esa imagen.",
    ),
    "sin_viewport": (
        "Casi todo el que busca casa lo hace desde el celu, y nadie hace zoom para leer una ficha.",
        "El propietario que te recomendaron entra a mirarte desde el celu y se lleva esa imagen.",
    ),
    "popup_intrusivo": (
        "El que entra a ver propiedades tiene que sacarse eso de encima antes de ver una sola casa.",
        "La primera impresión de la inmobiliaria termina siendo un cartel que estorba.",
    ),
    "sitio_inaccesible": (
        "El que te busca y se encuentra con eso no vuelve a probar: entra al siguiente resultado.",
        "El propietario que te recomendaron te busca para chequearte y termina llamando a la otra que le nombraron.",
    ),
}

# La oferta nombra lo que se arregla; "esa pantalla" no dice nada.
OFERTA = {
    "carga_lenta": (
        "Te armo un boceto de esa misma portada cargando rápido.",
        "Te hago un boceto de cómo quedaría esa portada, liviana.",
        "Te muestro en un boceto cómo sería esa portada sin la espera.",
    ),
    "sin_contacto": (
        "Te armo un boceto de la portada con la consulta a un toque.",
        "Te hago un boceto de cómo quedaría con un botón de WhatsApp a la vista.",
    ),
    "sin_tel_movil": (
        "Te armo un boceto de cómo se vería en el celu con un botón de WhatsApp.",
        "Te hago un boceto de esa misma web con la consulta por WhatsApp a un toque.",
    ),
    "overflow_mobile": (
        "Te armo un boceto de cómo se vería bien en el celu.",
        "Te hago un boceto de esa portada adaptada al celular.",
    ),
    "sin_viewport": (
        "Te armo un boceto de cómo se vería bien en el celu.",
        "Te hago un boceto de esa portada adaptada al celular.",
    ),
    "popup_intrusivo": (
        "Te armo un boceto de la portada sin ese aviso, mostrando las propiedades de entrada.",
    ),
}

# Siete y no cinco: con cinco, el cierre era la oración más repetida del corpus (26 %).
CIERRE = ("¿Te lo paso?", "¿Te lo mando?", "¿Querés verlo?", "Es sin cargo, ¿te lo paso?",
          "¿Te sirve que te lo pase?", "¿Lo querés ver?", "Si te sirve, ¿te lo mando?")
CIERRE_INACCESIBLE = ("Si querés te paso qué error me apareció, ¿te sirve?",)
