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


def rubro_de(nicho: str | None) -> Rubro:
    """El vocabulario del rubro, o el genérico si no se reconoce.

    Degradación elegante a propósito: un nicho nuevo no rompe la redacción,
    solo la deja tan genérica como estaba antes de existir este módulo.
    """
    texto = _plano(nicho or "")
    for claves, rubro in _RUBROS:
        if any(clave in texto for clave in claves):
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
