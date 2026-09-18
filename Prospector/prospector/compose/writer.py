"""Redacción del primer mensaje de correo.

Dos motores: Gemini (con la plantilla como referencia de estilo) y un motor de
plantillas puro que funciona sin conexión ni clave. Ambos pasan por el mismo
filtro anti-slop y por el mismo validador, porque un mensaje que huele a
programa se borra sin leer.

El motor de plantillas dejó de ser *una* plantilla con huecos y pasó a ser un
ensamblador de fragmentos:

  · los fragmentos del hallazgo los pone `audit/rules.py` (observación,
    consecuencia y puente, ya en rioplatense);
  · el vocabulario del rubro y la ciudad los pone `compose/lexicon.py`;
  · los marcos (saludo, apertura, oferta, cierre) están acá, con variantes;
  · la variante se elige por hash estable del lead, no al azar.

Antes, 3 oraciones cubrían el 72% de los correos con web y el 59% abría con
la misma frase. El motor de WhatsApp (`compose/whatsapp.py`) reusa los mismos
fragmentos con otro formato, en vez de mandar el cuerpo del correo tal cual.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..ai import AIUnavailable, GeminiClient
from ..config import TEMPLATES_DIR, ComposeSettings
from ..logging_setup import get_logger
from ..models import EmailDraft, Finding, Lead
from ..storage import to_absolute
from ..utils import dialecto_por_url, registrable_domain
from .lexicon import busqueda_de, elegir, rubro_de

log = get_logger("redactor")

# Muletillas que delatan a un bot. Se eliminan siempre, venga de donde venga el texto.
FRASES_PROHIBIDAS = (
    "espero que este correo te encuentre bien",
    "espero que estés bien",
    "en el mundo actual",
    "en la era digital",
    "en el vertiginoso mundo",
    "no dudes en",
    "de antemano",
    "quedo atento a tu pronta respuesta",
    "es un placer saludarte",
    "me pongo en contacto contigo para",
    "aprovecho la ocasión",
    "sin más que agregar",
    "revoluciona",
    "potenciar tu presencia digital",
    "llevar tu negocio al siguiente nivel",
    "soluciones a medida",
    "en un mercado cada vez más competitivo",
    # Condicional pedigüeño: pide permiso para existir y baja el estatus del
    # remitente antes de que el lector llegue al argumento.
    "quería consultarte",
    "queria consultarte",
    "no sé si te interesará",
    "no se si te interesara",
    "disculpá la molestia",
    "disculpa la molestia",
    "espero no molestar",
    "perdón por la molestia",
    "perdon por la molestia",
    # Jerga vacía ("sinergia" no va acá: SLOP_GENERAL ya la reemplaza por
    # "encaje" en vez de borrar la oración entera)
    "solución integral",
    "transformación digital",
    "propuesta de valor",
    "líder del mercado",
)

SLOP_GENERAL = {
    "delve": "profundizar",
    "sinergia": "encaje",
    "holístico": "completo",
    "robusto": "sólido",
    "aprovechar": "usar",
    "maximizar": "subir",
    "optimizar al máximo": "mejorar",
}

# Red de seguridad para el texto que viene de la IA, no traductor de producción.
# `rules.py` ya se escribe en rioplatense: cuando esto era lo único que
# convertía el dialecto, cubría las conjugaciones pero no el léxico (dejaba
# pasar "pulsar", "de sitio", "a pleno rendimiento") y en un caso metía un
# error de concordancia ("estéis" → "estén" dentro de un texto en singular).
# Se aplica solo si el lead es rioplatense (ver utils.dialecto_por_url): a un
# lead español escribirle en voseo desentona igual que al revés.
SLOP_VOSEO = {
    # Castellanismos que delatan origen no rioplatense
    "vosotros": "ustedes",
    "os ": "les ",
    "habéis": "tienen",
    "tenéis": "tienen",
    "hacéis": "hacen",
    "podéis": "pueden",
    "queréis": "quieren",
    "estéis": "estés",
    "seáis": "seas",
    "sois": "sos",
    "vais": "van",
    "vuestra": "tu",
    "vuestro": "tu",
    "vuestros": "tus",
    "vuestras": "tus",
    # Tuteo → voseo rioplatense
    "tú": "vos",
    "tienes": "tenés",
    "puedes": "podés",
    "quieres": "querés",
    "eres": "sos",
    "haces": "hacés",
    "dices": "decís",
    "sabes": "sabés",
    "piensas": "pensás",
    # Léxico peninsular que el filtro anterior no miraba
    "en el móvil": "en el celular",
    "el móvil": "el celular",
    "tu móvil": "tu celular",
    "pulsable": "tocable",
    "pulsar": "tocar",
    "pulsarlo": "tocarlo",
    "pulsarlos": "tocarlos",
    "ordenador": "computadora",
    "de sitio": "de lugar",
    "coger": "agarrar",
    "a pleno rendimiento": "a full",
    "nada más entrar": "apenas entrás",
}

# ─────────────────────────────── Marcos con variantes ───────────────────────────────
# Cada ranura tiene varias redacciones y se elige una por hash del lead. Con
# 3 saludos × 4 aperturas × 3 ofertas × 3 cierres hay 108 esqueletos distintos
# donde antes había uno solo, sin escribir una plantilla por rubro.

SALUDOS = ("Hola", "Buenas", "Hola, ¿qué tal?")

APERTURAS_CON_WEB = (
    "Estaba buscando {busqueda} y entré a {dominio}.",
    "Llegué a {dominio} buscando {busqueda}.",
    "Estuve mirando webs de {busqueda} y caí en {dominio}.",
    "Entré a {dominio} el otro día, buscando {busqueda}.",
    "Andaba viendo {busqueda} y terminé en {dominio}.",
    "Di con {dominio} mientras buscaba {busqueda}.",
)

# Ojo con el «con»: `prueba` ya viene como "4,8 con 86 reseñas", así que
# ninguna variante puede empezar con esa preposición. Anteponerla producía
# "(con 4,1 con 20 reseñas se nota que hay demanda real)" en 164 de 202
# correos, en la primera línea, que es la que decide si se sigue leyendo.
REPUTACION = (
    "Vi que tienen {prueba} en Maps, así que clientes no les faltan.",
    "En Maps tienen {prueba}: la demanda claramente está.",
    "Tienen {prueba} en Maps, o sea que el boca a boca funciona.",
    "El puntaje en Maps es bueno ({prueba}), así que gente buscándolos hay.",
)

TRANSICIONES = (
    "Mirando la primera pantalla noté una cosa:",
    "Me quedé mirando la portada y noté algo:",
    "Una cosa que salta a la vista:",
    "Me llamó la atención esto:",
    "Hay algo que se nota apenas entrás:",
    "Lo primero que vi fue esto:",
)

SEGUNDO_HALLAZGO = (
    "Y otra cosa: {extra}.",
    "Aparte de eso, {extra}.",
    "Hay un detalle más: {extra}.",
    "Se suma que {extra}.",
)

# La rama sin web era el 57% del corpus con el 93% de las palabras iguales.
SOLUCION_SIN_WEB = (
    "Una página de una sola pantalla lo resuelve: qué hacés, por qué elegirte "
    "y un botón para escribir o llamar. Nada más.",
    "Con una sola pantalla alcanza: qué ofrecés, por qué vos y un botón para "
    "escribirte. No hace falta más que eso.",
    "No hace falta un sitio grande. Una pantalla que diga qué hacés, por qué "
    "elegirte y cómo escribirte ya corta la fuga.",
)

OFERTAS = (
    "Me toma un par de horas armar un boceto de cómo quedaría esa portada.",
    "Puedo armarte un boceto de cómo se vería esa pantalla arreglada; me lleva un par de horas.",
    "Suelo armar un boceto de la portada nueva para que se vea la diferencia: un par de horas de trabajo.",
    "Armo un boceto de la portada con esto resuelto; es un rato de trabajo, no un proyecto.",
    "Si querés lo veo en concreto: te hago un boceto de esa pantalla y lo comparás con la actual.",
)

CIERRES = (
    "¿Te sirve si te lo paso para que lo veas? Sin compromiso.",
    "¿Querés que te lo mande y lo mirás? No te compromete a nada.",
    "Si te interesa verlo, te lo paso y lo charlamos. Y si no, no pasa nada.",
    "¿Te lo mando y lo ves con calma? No hace falta que contestes nada más.",
    "Decime si te lo paso. Si no es momento, lo dejamos acá y listo.",
)

# ─────────────────────────────── Asuntos ───────────────────────────────
# Regla en la que coinciden las dos skills de referencia: 2-4 palabras, en
# minúscula, que parezca un correo interno. Los de antes metían `{nombre}`
# crudo —que muchas veces es la razón social entera de Maps, con pipes— y
# producían cosas como "Estudio jurídico EOT | Abogados Previsionales en
# CABA: la primera pantalla". Ahora el asunto se elige por el hallazgo
# principal, para que tenga coherencia con la primera línea.

ASUNTO_POR_REGLA = {
    "sin_cta_fold": "el botón de contacto",
    "sin_contacto": "el botón de contacto",
    "sin_tel_movil": "el botón de contacto",
    "sin_viewport": "la web en el celular",
    "overflow_mobile": "la web en el celular",
    "texto_pequeno_movil": "la web en el celular",
    "tap_targets": "la web en el celular",
    "carga_lenta": "lo que tarda la web",
    "cls_alto": "lo que tarda la web",
    "peso_excesivo": "lo que tarda la web",
    "sin_https": "el aviso de no segura",
    "popup_intrusivo": "el aviso que tapa",
    "copyright_viejo": "el pie de la web",
    "fold_vacio": "la primera pantalla",
    "seo_basico": "algo de la web",
    "sitio_inaccesible": "la web no carga",
}

ASUNTOS_CON_WEB = (
    "algo de la web",
    "la primera pantalla",
    "una duda de la web",
    "la web en el celular",
)
ASUNTOS_SIN_WEB = (
    "los encontré en maps",
    "su ficha de maps",
    "una duda",
)


def cargar_plantilla() -> str:
    ruta = TEMPLATES_DIR / "primer_mensaje.md"
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


# ─────────────────────────────── Filtro anti-slop ───────────────────────────────

def limpiar(texto: str, dialecto: str = "voseo") -> str:
    """Quita las marcas típicas de texto generado y aprieta el tono."""
    if not texto:
        return ""
    limpio = texto.replace("\r\n", "\n")
    limpio = limpio.replace("—", ", ").replace("–", "-")
    limpio = re.sub(r"\*\*(.+?)\*\*", r"\1", limpio)   # negritas markdown
    limpio = re.sub(r"^#+\s*", "", limpio, flags=re.M)

    for frase in FRASES_PROHIBIDAS:
        limpio = re.sub(rf"[^.\n]*{re.escape(frase)}[^.\n]*[.。]?\s*", "", limpio, flags=re.I)
    palabras = dict(SLOP_GENERAL)
    if dialecto == "voseo":
        palabras.update(SLOP_VOSEO)
    for palabra, reemplazo in palabras.items():
        limpio = re.sub(rf"\b{re.escape(palabra)}\b", reemplazo, limpio, flags=re.I)

    # Decimal inglés dentro de un texto en español. `rules.py` ya formatea con
    # coma, pero un Finding releído de un JSON viejo trae "7.5 segundos" en su
    # `argumento`, y la IA los escribe con punto la mitad de las veces. Se
    # acota a número + unidad para no tocar dominios ni versiones.
    limpio = re.sub(r"(?<=\d)\.(?=\d)(?=\d*\s*(?:segundos?|seg\b|s\b|MB|KB|%))", ",", limpio)

    limpio = re.sub(r"[ \t]{2,}", " ", limpio)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio)
    return limpio.strip()


def _quitar_mencion_adjunto(cuerpo: str) -> str:
    """Si no hay una captura real que adjuntar, no se puede prometer una:
    es la mentira más rápida de detectar y la que más credibilidad quema."""
    limpio = re.sub(r"[^.\n]*\badjunt[oa]s?\b[^.\n]*[.]?\s*", "", cuerpo, flags=re.I)
    limpio = re.sub(r"[ \t]{2,}", " ", limpio)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio)
    return limpio.strip()


# ─────────────────────────────── Validación ───────────────────────────────
# Antes esto corría SOLO sobre el borrador de la IA, que escribe el 2,5% de
# los mensajes. El motor de plantillas —el 97,5%— no pasaba por ningún
# control: por eso el 31% de los cuerpos superaba el tope de 175 palabras que
# esta misma función usa para rechazar un borrador de IA, y por eso salieron
# los asuntos con razón social cruda.

LIMITES = {
    "email": {"max_palabras": 150, "min_palabras": 40},
    # WhatsApp se lee en el celular, de un desconocido, sin asunto que lo
    # anuncie. 704 caracteres de mediana (lo que se estaba mandando) son doce
    # líneas sin respiro.
    "whatsapp": {"max_palabras": 95, "min_palabras": 20},
}

_URL = re.compile(
    r"(https?://\S+|www\.\S+"
    r"|\b[a-z0-9][\w\-]*(?:\.[a-z0-9][\w\-]*)*"
    r"\.(?:com|net|org|ar|es|io|co|online|shop|edu|gov|info|app)(?:\.[a-z]{2})?\b)",
    re.I,
)
_DOMINIO_EN_ASUNTO = re.compile(r"\.(com|ar|es|net|org|online)\b", re.I)


def validar(borrador: EmailDraft, canal: str = "email", dominio_propio: str = "") -> list[str]:
    """Problemas que impiden mandar este texto. Lista vacía = se puede mandar."""
    limites = LIMITES.get(canal, LIMITES["email"])
    problemas: list[str] = []
    cuerpo = borrador.cuerpo or ""
    palabras = len(cuerpo.split())

    if palabras > limites["max_palabras"]:
        problemas.append(f"demasiado largo ({palabras} palabras, tope {limites['max_palabras']})")
    if palabras < limites["min_palabras"]:
        problemas.append(f"demasiado corto ({palabras} palabras)")
    if "[" in cuerpo or "{" in cuerpo:
        problemas.append("quedaron marcadores sin rellenar")
    # El empalme que salía en el 81% de los correos con web: `apertura_social`
    # anteponía "con" a una prueba social que ya empezaba con "con".
    if re.search(r"\bcon\s+[\d,]+\s+con\b", cuerpo, re.I):
        problemas.append("prueba social con «con» duplicado")
    if re.search(r"\d+\.\d+\s*(segundos|s\b|MB)", cuerpo):
        problemas.append("decimal con punto en vez de coma")
    minuscula = cuerpo.lower()
    for frase in FRASES_PROHIBIDAS:
        if frase in minuscula:
            problemas.append(f"frase prohibida: «{frase}»")

    if canal == "whatsapp":
        # Un enlace en el primer mensaje de un número desconocido es la señal
        # de spam más fuerte que hay, para la plataforma y para la persona.
        # Se admite una sola excepción: el dominio DEL PROSPECTO, que es la
        # prueba de que se miró su web.
        propio = (dominio_propio or "").lower().strip("/ ")
        ajenos = [
            u for u in _URL.findall(cuerpo)
            # El dominio del prospecto puede aparecer entero o como sufijo
            # ("edu.ar" dentro de "cfp1tucuman.edu.ar"): la comparación iba al
            # revés y marcaba como enlace ajeno el dominio del propio lead.
            if not (propio and (u.lower().strip("/ ") in propio or propio in u.lower()))
        ]
        if ajenos:
            problemas.append(f"enlace ajeno en WhatsApp: {ajenos[0]}")
        if borrador.asunto:
            problemas.append("un mensaje de WhatsApp no lleva asunto")
    else:
        asunto = (borrador.asunto or "").strip()
        if not asunto:
            problemas.append("sin asunto")
        if len(asunto.split()) > 5:
            problemas.append("asunto largo (más de 5 palabras)")
        if "|" in asunto:
            problemas.append("asunto con razón social cruda")
        if asunto != asunto.lower():
            problemas.append("asunto con mayúsculas")
        if _DOMINIO_EN_ASUNTO.search(asunto):
            problemas.append("asunto con dominio")
        if asunto.endswith("!") or asunto.isupper():
            problemas.append("asunto con tono publicitario")
    return problemas


# Compatibilidad con el nombre anterior (lo usaba solo la vía IA).
_validar = validar


# ─────────────────────────────── Piezas compartidas ───────────────────────────────

_PARECE_DOMINIO = re.compile(r"^[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+$", re.I)


def nombre_corto(lead: Lead) -> str:
    """El nombre utilizable del negocio, o "" si lo que hay no sirve.

    El minado a veces devuelve la razón social entera con pipes y guiones, o
    directamente el dominio. Saludar a una URL es la delación de automatismo
    más rápida que existe.
    """
    nombre = (lead.nombre or "").strip()
    if not nombre or _PARECE_DOMINIO.match(nombre):
        return ""
    corto = re.split(r"[|·,\-–]", nombre)[0].strip()
    if not corto or _PARECE_DOMINIO.match(corto) or len(corto) > 32:
        return ""
    return corto


def saludo(lead: Lead) -> str:
    """Saludo en segunda persona del singular.

    Se cambió "Hola, equipo de {nombre}," (el 88% de los mensajes) porque
    abría en plural un texto que seguía en singular ("tu web", "hacés", "te
    sirve"), y porque en WhatsApp se le escribe al celular de una persona, no
    a un equipo.
    """
    base = elegir(SALUDOS, lead.id, "saludo")
    corto = nombre_corto(lead)
    if base.endswith("?"):
        return base
    return f"{base}, {corto}," if corto else f"{base},"


def reputacion(lead: Lead) -> str:
    """El rating y las reseñas ya minados, como dato y no como adjetivo."""
    if lead.rating and lead.resenas:
        return f"{lead.rating:.1f}".replace(".", ",") + f" con {lead.resenas} reseñas"
    if lead.resenas:
        return f"{lead.resenas} reseñas"
    if lead.rating:
        return f"{lead.rating:.1f}".replace(".", ",")
    return ""


def frase_reputacion(lead: Lead) -> str:
    """Oración completa y bien armada, o "" si no hay dato.

    Esto reemplaza al `f" (con {prueba_social} se nota que hay demanda real)"`
    que producía "(con 4,1 con 20 reseñas se nota que hay demanda real)" en
    164 de los 202 correos con web.
    """
    prueba = reputacion(lead)
    if not prueba:
        return ""
    return elegir(REPUTACION, lead.id, "reputacion").format(prueba=prueba)


def minuscula_inicial(texto: str) -> str:
    """Baja solo la inicial (bajar todo rompe «Google» y los nombres propios)."""
    return texto[:1].lower() + texto[1:] if texto else texto


def mayuscula_inicial(texto: str) -> str:
    return texto[:1].upper() + texto[1:] if texto else texto


def frase_prueba(cfg: ComposeSettings) -> str:
    """Una línea de credibilidad real, si el remitente la configuró.

    Nunca se inventa: `cfg.sender_proof` viene vacío por defecto.
    """
    texto = cfg.sender_proof.strip()
    if not texto:
        return ""
    texto = mayuscula_inicial(texto)
    if not texto.endswith((".", "!", "?")):
        texto += "."
    return texto


def firma(cfg: ComposeSettings) -> str:
    """Firma del correo. No se usa en WhatsApp: ahí el nombre y el número ya
    están en el encabezado del chat, y un enlace en el primer mensaje es la
    señal de spam más cara del canal."""
    lineas = [cfg.sender_name]
    if cfg.sender_role:
        lineas.append(cfg.sender_role)
    if cfg.sender_site:
        lineas.append(cfg.sender_site)
    if cfg.sender_phone:
        lineas.append(cfg.sender_phone)
    return "\n".join(l for l in lineas if l)


def hallazgos_de(lead: Lead, maximo: int) -> list[Finding]:
    return lead.audit.argumentables[:maximo] if lead.audit else []


def dominio_de(lead: Lead) -> str:
    return registrable_domain(lead.url) or (lead.url or "").replace(
        "https://", "").replace("http://", "").rstrip("/")


def asunto_para(lead: Lead, hallazgo: Finding | None) -> str:
    if not lead.url:
        return elegir(ASUNTOS_SIN_WEB, lead.id, "asunto")
    if hallazgo and hallazgo.rule_id in ASUNTO_POR_REGLA:
        return ASUNTO_POR_REGLA[hallazgo.rule_id]
    return elegir(ASUNTOS_CON_WEB, lead.id, "asunto")


# ─────────────────────────────── Motor de plantillas ───────────────────────────────

def componer_por_plantilla(
    lead: Lead, cfg: ComposeSettings, tiene_adjunto: bool = True, es_marcada: bool = True,
) -> EmailDraft:
    """Redacción determinista: sin IA, sin coste, siempre disponible."""
    auditoria = lead.audit
    hallazgos = hallazgos_de(lead, cfg.max_findings_in_email)
    principal = hallazgos[0] if hallazgos else None
    secundario = hallazgos[1] if len(hallazgos) > 1 else None
    dominio = dominio_de(lead)
    dialecto = dialecto_por_url(lead.url)
    rubro = rubro_de(lead.nicho)
    busqueda = busqueda_de(lead.nicho)
    inaccesible = bool(auditoria and auditoria.veredicto == "inaccesible")

    if inaccesible:
        tiene_adjunto = False  # no hay captura posible de una página que no cargó

    if not tiene_adjunto:
        linea_adjunto = ""
    elif es_marcada:
        linea_adjunto = "Te adjunto la captura con la zona marcada.\n\n"
    else:
        linea_adjunto = "Te adjunto una captura de la portada, tal como la vi.\n\n"

    prueba = frase_prueba(cfg)
    cierre_prueba = f" {prueba}" if prueba else ""

    def armar(con_reputacion: bool, con_extra: bool) -> list[str]:
        return [
            saludo(lead),
            _sin_web(lead, rubro, busqueda, con_reputacion),
            elegir(SOLUCION_SIN_WEB, lead.id, "solucion") + cierre_prueba,
            elegir(OFERTAS, lead.id, "oferta").replace("esa portada", "esa página")
            .replace("esa pantalla", "esa página"),
            elegir(CIERRES, lead.id, "cierre"),
        ] if not lead.url else [
            saludo(lead),
            _con_web(lead, principal, secundario, dominio, busqueda, con_reputacion, con_extra),
            linea_adjunto.strip(),
            _cierre_con_web(lead, principal, rubro, cierre_prueba),
            elegir(CIERRES, lead.id, "cierre"),
        ]

    if not lead.url:
        parrafos = _ajustar(armar, cfg, firma(cfg))
    elif inaccesible:
        # No se puede decir que se miró la primera pantalla de una web que no
        # cargó: el mensaje se contradice solo en la primera línea.
        parrafos = [
            saludo(lead),
            (
                f"Quise entrar a {dominio} buscando {busqueda} y la web no cargó, "
                f"ni la primera vez ni la segunda."
            ),
            (
                f"El que te busca y se encuentra con eso no vuelve a probar: entra al siguiente "
                f"resultado. Si venció el dominio o el hosting, o hay un error de configuración, "
                f"suele ser rápido de resolver.{cierre_prueba}"
            ),
            "¿Te sirve si te paso exactamente qué error me apareció? Sin compromiso.",
        ]
    else:
        parrafos = _ajustar(armar, cfg, firma(cfg))

    cuerpo = "\n\n".join(p for p in parrafos if p) + "\n\n" + firma(cfg)
    return EmailDraft(
        asunto=asunto_para(lead, principal),
        cuerpo=limpiar(cuerpo, dialecto),
        generado_por="plantilla",
    )


def _ajustar(armar, cfg: ComposeSettings, firma_texto: str) -> list[str]:
    """Presupuesto de palabras: si el mensaje se pasa, se caen los opcionales.

    El 31% de los cuerpos superaba las 175 palabras porque nadie los medía —el
    validador corría solo sobre el borrador de la IA—. Recortar a mano las
    frases hasta que "entren siempre" habría dejado el mensaje pobre en el caso
    normal; se prefiere escribir completo y sacar, en este orden, el segundo
    hallazgo y después la línea de reputación, que son las dos piezas que el
    argumento no necesita para sostenerse.
    """
    tope = LIMITES["email"]["max_palabras"]
    intentos = ((True, True), (True, False), (False, False))
    parrafos: list[str] = []
    for con_reputacion, con_extra in intentos:
        parrafos = armar(con_reputacion, con_extra)
        cuerpo = "\n\n".join(p for p in parrafos if p) + "\n\n" + firma_texto
        if len(cuerpo.split()) <= tope:
            break
    return parrafos


def _sin_web(lead: Lead, rubro, busqueda: str, con_reputacion: bool = True) -> str:
    """El segmento de mayor valor del sistema, y el que menos variación tenía:
    312 mensajes con el 93% de las palabras idénticas y dos huecos."""
    apertura = elegir(
        (
            f"Te encontré en Maps buscando {busqueda} y vi que no tenés web enlazada.",
            f"Estaba buscando {busqueda}, llegué a tu ficha de Maps y no había web detrás.",
            f"Buscando {busqueda} di con tu ficha de Maps, pero sin web enlazada.",
        ),
        lead.id, "apertura_sin_web",
    )
    rep = frase_reputacion(lead) if con_reputacion else ""
    consecuencia = (
        f"{mayuscula_inicial(rubro.cliente)} ve la ficha, no encuentra {rubro.no_ve}, "
        f"y termina abriendo la del de al lado."
    )
    return " ".join(p for p in (apertura, rep, consecuencia) if p)


def _con_web(lead: Lead, principal: Finding | None, secundario: Finding | None,
             dominio: str, busqueda: str, con_reputacion: bool = True,
             con_extra: bool = True) -> str:
    apertura = elegir(APERTURAS_CON_WEB, lead.id, "apertura").format(
        busqueda=busqueda, dominio=dominio)
    rep = frase_reputacion(lead) if con_reputacion else ""
    transicion = elegir(TRANSICIONES, lead.id, "transicion")
    observacion = minuscula_inicial(
        principal.observacion if principal else
        "la primera pantalla no está trabajando para convertir visitas en contactos"
    ).rstrip(".")
    extra = ""
    if con_extra and secundario and secundario.observacion:
        extra = " " + elegir(SEGUNDO_HALLAZGO, lead.id, "extra").format(
            extra=minuscula_inicial(secundario.observacion).rstrip("."))
    return f"{apertura} {rep} {transicion} {observacion}.{extra}".replace("  ", " ").strip()


def _cierre_con_web(lead: Lead, principal: Finding | None, rubro, cierre_prueba: str) -> str:
    """La consecuencia se dice UNA vez, y el puente sale del hallazgo.

    El párrafo fijo de antes ("Si el visitante no ve rápido cómo contactar,
    termina cerrando la pestaña") era una consecuencia de CTA que se mandaba
    igual cuando el hallazgo era la velocidad de carga o el copyright de 2002:
    en 65 de los 202 correos con web no venía a cuento.
    """
    legado = bool(principal and principal.legado)
    consecuencia = "" if legado else (
        (principal.consecuencia if principal else "")
        or f"{rubro.cliente} se va sin {rubro.accion}"
    )
    puente = (principal.puente if principal else "") or (
        "ordenar esa pantalla es lo primero que suelo mover"
    )
    oferta = elegir(OFERTAS, lead.id, "oferta")
    piezas = [mayuscula_inicial(t).rstrip(".") + "." for t in (consecuencia, puente) if t]
    return " ".join(piezas + [f"{oferta}{cierre_prueba}"])


# ─────────────────────────────── Motor IA ───────────────────────────────

PROMPT = """\
Escribes correos en frío que la gente contesta. No eres un generador de plantillas.

Estilo de referencia de la agencia (imítalo en tono, no copies frases):
<referencia>
{plantilla}
</referencia>

Prospecto:
- Negocio: {nombre}
- Sector/búsqueda: {nicho}
- Web: {url}
- Reputación en Maps: {reputacion}
- Señales objetivas medidas por nosotros (datos reales, no inventes otros):
{hallazgos}
{vision}

Reglas innegociables:
1. Máximo 130 palabras. Cuatro párrafos cortos como mucho, y ninguno de más de dos líneas leído en la
   pantalla de un celular.
2. La primera frase menciona algo CONCRETO y verificable de SU web (o, si no tiene, de su ficha de Maps).
   Nada de aperturas genéricas: si la frase sirve igual para otro prospecto de la lista, es spam.
3. Traduce el problema técnico a consecuencia de negocio (clientes que se pierden), sin jerga, y dila UNA
   sola vez. Si hay reputación en Maps, úsala como prueba de que la demanda ya existe (es un dato SUYO, no
   una estadística genérica: pesa mucho más). Prohibido inventar o citar estadísticas de la industria tipo
   "una de cada cuatro personas abandona": si no es un dato medido de ESTE prospecto, no se afirma.
4. Prohibido: "espero que estés bien", "en el mundo actual", "llevar tu negocio al siguiente nivel",
   signos de exclamación, mayúsculas de énfasis, emojis, guiones largos. Prohibido también el condicional
   pedigüeño ("quería consultarte", "no sé si te interesará", "disculpá la molestia", "espero no
   molestar"): pide permiso para existir y baja el estatus antes de que el lector llegue al argumento.
   Prohibida cualquier credencial académica (carrera, universidad, "estoy estudiando"): la autoridad la
   dan el hallazgo medido y la evidencia, no un título.
5. {regla_adjunto}
6. Cierra ofreciendo un prototipo de la portada con una pregunta directa de bajo compromiso y un plazo
   concreto ("me lleva un par de horas", "lo tenés mañana"). Nunca digas que el prototipo de ESE negocio
   puntual ya existe o ya está hecho: no es cierto hasta que responda. Prohibido el patrón "¿te opondrías
   a...?" o cualquier doble negación tipo "¿no te molestaría que...?": preguntá directo, "¿te sirve si...?".
7. Firma como {firmante} ({rol}). Sin posdatas ni enlaces de baja.
8. Ratio: al menos el DOBLE de referencias al negocio del prospecto (su web, su ficha, sus clientes, lo
   que pierde) que a vos mismo (lo que hacés, lo que ofrecés). Contalas antes de responder. Un correo que
   habla más del remitente que del lector no se contesta.
9. {regla_dialecto}
10. Segunda persona del SINGULAR de punta a punta. Nada de abrir en plural ("hola, equipo de X") y seguir
   en singular ("tu web", "te sirve"): mezclar las dos personas en el mismo texto se lee como plantilla
   mal rellenada.
{regla_prueba}
{regla_estado}

Devuelve solo:
{{"asunto": "en minúsculas, máximo 4 palabras, sin puntuación final, sin el nombre del negocio ni el dominio", "cuerpo": "texto plano con saltos de línea"}}"""

REGLA_DIALECTO_VOSEO = (
    'Español rioplatense obligatorio. Segunda persona singular siempre con "vos" y conjugaciones '
    'voseantes: tenés, podés, querés, sabés, sos, hacés, decís, pensás. Nunca "tú", "tienes", "puedes", '
    '"eres". Plural siempre con "ustedes". Nunca "vosotros". Léxico argentino: "celular" (no "móvil"), '
    '"tocar" (no "pulsar"), "computadora" (no "ordenador"), tono de persona real con prisa, no de agencia.'
)
REGLA_DIALECTO_TUTEO = (
    'Español peninsular neutro: el negocio es de España. Trato de "tú" en singular y "vosotros" en '
    'plural. No uses voseo rioplatense ("vos", "tenés", "sos", "celular" en vez de "móvil"): a un lead '
    'español le desentona tanto como "vosotros" le desentonaría a uno argentino.'
)


def componer_con_ia(
    cliente: GeminiClient, lead: Lead, cfg: ComposeSettings, plantilla: str,
    tiene_adjunto: bool = True, es_marcada: bool = True,
) -> EmailDraft:
    auditoria = lead.audit
    hallazgos = auditoria.argumentables[:3] if auditoria else []
    lista = "\n".join(f"  - {h.titulo}: {h.evidencia}. {h.argumento}" for h in hallazgos) or "  - (sin datos)"
    vision = ""
    if auditoria and auditoria.vision.get("problema_visual"):
        vision = (
            f"- Observación visual del revisor: {auditoria.vision['problema_visual']}"
            f" ({auditoria.vision.get('detalle_observado', '')})"
        )

    dialecto = dialecto_por_url(lead.url)
    inaccesible = bool(auditoria and auditoria.veredicto == "inaccesible")
    if inaccesible:
        tiene_adjunto = False

    if not tiene_adjunto:
        regla_adjunto = "No prometas ningún adjunto ni captura de pantalla: no hay ninguna disponible para este correo."
    elif es_marcada:
        regla_adjunto = "Menciona en una frase que adjuntas una captura con la zona marcada."
    else:
        regla_adjunto = (
            "Menciona en una frase que adjuntas una captura de la portada tal como la viste, SIN decir "
            "que está marcada, señalada o resaltada (no lo está, es la captura sin anotar)."
        )
    regla_estado = (
        "12. El sitio no cargó cuando lo visitamos (hallazgo sitio_inaccesible): NO digas que viste su "
        "primera pantalla ni que navegaste la web. Contá que intentaste entrar y no cargó."
        if inaccesible else ""
    )
    regla_prueba = (
        f'11. Si encaja de forma natural (no forzado), sumá esta prueba de que ya hiciste este trabajo: '
        f'"{cfg.sender_proof.strip()}".'
        if cfg.sender_proof.strip() else ""
    )

    prompt = PROMPT.format(
        plantilla=plantilla[:2500],
        nombre=lead.nombre or lead.url,
        nicho=lead.nicho or "no especificado",
        url=lead.url or "no tiene web (aparece solo en Google Maps)",
        reputacion=reputacion(lead) or "sin datos de rating/reseñas",
        hallazgos=lista,
        vision=vision,
        firmante=cfg.sender_name,
        rol=cfg.sender_role,
        regla_adjunto=regla_adjunto,
        regla_dialecto=REGLA_DIALECTO_VOSEO if dialecto == "voseo" else REGLA_DIALECTO_TUTEO,
        regla_prueba=regla_prueba,
        regla_estado=regla_estado,
    )
    datos = cliente.generar_json(prompt, temperatura=0.8)
    cuerpo = limpiar(str(datos.get("cuerpo", "")), dialecto)
    if not tiene_adjunto:
        cuerpo = _quitar_mencion_adjunto(cuerpo)
    if cfg.sender_site and cfg.sender_site not in cuerpo:
        cuerpo += f"\n{cfg.sender_site}"
    if cfg.sender_phone and cfg.sender_phone not in cuerpo:
        cuerpo += f"\n{cfg.sender_phone}"
    return EmailDraft(
        asunto=limpiar(str(datos.get("asunto", "")), dialecto).strip().strip(".").lower(),
        cuerpo=cuerpo,
        generado_por="ia",
    )


# ─────────────────────────────── Orquestación ───────────────────────────────

def _ruta_adjunto(lead: Lead) -> tuple[str | None, bool]:
    """Candidato a adjunto y si tiene de verdad un recuadro rojo dibujado.

    La anotada es la estrella; si no existe, se cae a la captura cruda del
    fold. `captura_marcada` (ver audit/runner.py) es la fuente de verdad de
    si HUBO un recuadro dibujado: prometer "la zona marcada" sobre una imagen
    sin marca es la misma mentira detectable que prometer un adjunto que no
    existe.
    """
    if not lead.audit:
        return None, False
    capturas = lead.audit.capturas
    marcada = capturas.get("principal") or capturas.get("anotada")
    if marcada:
        return marcada, bool(lead.audit.captura_marcada)
    return capturas.get("desktop_fold") or None, False


def adjunto_real(lead: Lead) -> tuple[str | None, bool, bool]:
    """(ruta relativa, es_marcada, existe_en_disco)."""
    adjunto, es_marcada = _ruta_adjunto(lead)
    ruta_absoluta = to_absolute(adjunto) if adjunto else None
    existe = bool(ruta_absoluta and ruta_absoluta.exists())
    return (adjunto if existe else None), es_marcada, existe


def redactar(lead: Lead, cfg: ComposeSettings, cliente: GeminiClient | None, plantilla: str) -> EmailDraft:
    # Se decide ANTES de redactar: el cuerpo no puede prometer una captura que
    # el archivo en disco no respalda.
    adjunto, es_marcada, tiene_adjunto = adjunto_real(lead)
    dominio = dominio_de(lead)

    borrador: EmailDraft | None = None
    if cliente is not None and cfg.use_ai and cliente.disponible:
        try:
            borrador = componer_con_ia(
                cliente, lead, cfg, plantilla, tiene_adjunto=tiene_adjunto, es_marcada=es_marcada,
            )
            problemas = validar(borrador, canal="email", dominio_propio=dominio)
            if problemas:
                log.warning("Borrador IA rechazado para %s (%s)", lead.etiqueta, ", ".join(problemas))
                borrador = None
        except (AIUnavailable, ValueError, KeyError) as exc:
            log.warning("IA no disponible para %s: %s", lead.etiqueta, exc)

    if borrador is None:
        borrador = componer_por_plantilla(lead, cfg, tiene_adjunto=tiene_adjunto, es_marcada=es_marcada)
        # El motor de plantillas ya NO es "seguro por ser determinista": fue el
        # que produjo los peores asuntos y el 31% de los cuerpos fuera de tope.
        problemas = validar(borrador, canal="email", dominio_propio=dominio)
        if problemas:
            log.warning("Plantilla con problemas para %s (%s)", lead.etiqueta, ", ".join(problemas))

    borrador.adjunto = adjunto
    return borrador


def redactar_todos(leads: list[Lead], cfg, forzar: bool = False) -> list[Lead]:
    from ..ai import get_client

    plantilla = cargar_plantilla()
    cliente = get_client(cfg.ai) if cfg.compose.use_ai and cfg.ai.enabled else None
    if cfg.compose.use_ai and cliente is None:
        log.info("Sin GEMINI_API_KEY: se redactará con el motor de plantillas")

    candidatos = [
        lead for lead in leads
        if lead.estado in {"auditado", "listo"} and (forzar or lead.email_draft is None)
        and lead.contactable
    ]
    sin_correo_ni_tel = [
        lead for lead in leads
        if lead.estado == "auditado" and not lead.contactable and not lead.telefono
    ]
    if sin_correo_ni_tel:
        log.info("%d leads calificados no tienen ni email ni teléfono: sin forma de contacto",
                 len(sin_correo_ni_tel))

    for lead in candidatos:
        borrador = redactar(lead, cfg.compose, cliente, plantilla)
        lead.email_draft = borrador
        lead.estado = "listo"
        log.info("✎ %s · «%s» (%s)", lead.etiqueta, borrador.asunto, borrador.generado_por)
    return leads
