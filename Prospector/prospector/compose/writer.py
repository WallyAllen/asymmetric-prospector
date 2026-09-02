"""Redacción del primer mensaje.

Dos motores: Gemini (con la plantilla como referencia de estilo) y un motor de
plantillas puro que funciona sin conexión ni clave. Ambos pasan por el mismo
filtro anti-slop, porque un correo que huele a IA se borra sin leer.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from ..ai import AIUnavailable, GeminiClient
from ..config import TEMPLATES_DIR, ComposeSettings
from ..logging_setup import get_logger
from ..models import EmailDraft, Finding, Lead
from ..storage import to_absolute
from ..utils import dialecto_por_url, registrable_domain

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

# Solo se aplica cuando el lead es rioplatense (ver utils.dialecto_por_url):
# a un lead español (.es) escribirle en voseo desentona tanto como escribirle
# en "vosotros" a uno argentino, así que esta conversión es condicional.
SLOP_VOSEO = {
    # Castellanismos que delatan origen no rioplatense
    "vosotros": "ustedes",
    "os ": "les ",
    "habéis": "tienen",
    "tenéis": "tienen",
    "hacéis": "hacen",
    "podéis": "pueden",
    "queréis": "quieren",
    "estéis": "estén",
    "seáis": "sean",
    "sois": "son",
    "vais": "van",
    "vuestra": "su",
    "vuestro": "su",
    "vuestros": "sus",
    "vuestras": "sus",
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
    # Léxico: Argentina usa "celular", no "móvil" para el teléfono
    "en el móvil": "en el celular",
    "el móvil": "el celular",
    "tu móvil": "tu celular",
}

ASUNTOS_SIN_WEB = (
    "{nombre} en Google Maps",
    "una pregunta sobre {nombre}",
    "{nombre} sin web",
)
ASUNTOS_CON_WEB = (
    "algo que vi en {dominio}",
    "{dominio} en el {dispositivo}",
    "un detalle de {dominio}",
    "{nombre}: la primera pantalla",
)


def cargar_plantilla() -> str:
    ruta = TEMPLATES_DIR / "primer_mensaje.md"
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


# ─────────────────────────────── Filtro anti-slop ───────────────────────────────

def limpiar(texto: str, dialecto: str = "voseo") -> str:
    """Quita las marcas típicas de texto generado y aprieta el tono.

    `dialecto` viene de utils.dialecto_por_url(lead.url): "voseo" aplica las
    conversiones rioplatenses, "tuteo" las deja intactas para no imponerle
    "vos" a un lead español.
    """
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


def _validar(borrador: EmailDraft) -> list[str]:
    problemas = []
    palabras = len(borrador.cuerpo.split())
    if palabras > 175:  # deja margen para la línea de prueba social opcional
        problemas.append(f"demasiado largo ({palabras} palabras)")
    if palabras < 35:
        problemas.append("demasiado corto")
    if len(borrador.asunto) > 60:
        problemas.append("asunto largo")
    if borrador.asunto.strip().endswith("!") or borrador.asunto.isupper():
        problemas.append("asunto con tono publicitario")
    if "[" in borrador.cuerpo or "{" in borrador.cuerpo:
        problemas.append("quedaron marcadores sin rellenar")
    return problemas


# ─────────────────────────────── Motor de plantillas ───────────────────────────────

_PARECE_DOMINIO = re.compile(r"^[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+$", re.I)


def _saludo(lead: Lead) -> str:
    nombre = (lead.nombre or "").strip()
    if not nombre:
        return "Hola,"
    corto = re.split(r"[|·,\-–]", nombre)[0].strip()
    # Cuando el minado no logró un nombre real, `nombre` a veces es el propio
    # dominio (p. ej. por un fallback en el parser de Maps). Saludar a una
    # URL ("Hola, equipo de contadoreslaplata.com.ar,") es la delación de
    # automatización más rápida que existe: mejor un saludo genérico.
    if not corto or _PARECE_DOMINIO.match(corto) or len(corto) > 40:
        return "Hola,"
    return f"Hola, equipo de {corto},"


def _primera_minuscula(texto: str) -> str:
    """Baja solo la inicial, no la cadena entera (bajar todo rompe "Google",
    los saltos de oración y cualquier nombre propio que venga después)."""
    return texto[:1].lower() + texto[1:] if texto else texto


def _prueba_social(lead: Lead) -> str:
    """"Con reseñas" es vago y no prueba que se miró el negocio en particular;
    el rating y el número de reseñas ya están minados y no se usaban."""
    if lead.rating and lead.resenas:
        rating = f"{lead.rating:.1f}".replace(".", ",")
        return f"{rating} con {lead.resenas} reseñas"
    if lead.resenas:
        return f"{lead.resenas} reseñas"
    if lead.rating:
        return f"{lead.rating:.1f}".replace(".", ",")
    return ""


def _frase_prueba(cfg: ComposeSettings) -> str:
    """Una línea de credibilidad real, si el remitente la configuró.

    Nunca se inventa: cfg.sender_proof viene vacío por defecto y solo se usa
    si alguien la completó a mano en el .env con algo verificable.
    """
    texto = cfg.sender_proof.strip()
    if not texto:
        return ""
    texto = texto[:1].upper() + texto[1:]
    if not texto.endswith((".", "!", "?")):
        texto += "."
    return f" {texto}"


def componer_por_plantilla(
    lead: Lead, cfg: ComposeSettings, tiene_adjunto: bool = True, es_marcada: bool = True,
) -> EmailDraft:
    """Redacción determinista: sin IA, sin coste, siempre disponible."""
    auditoria = lead.audit
    hallazgos: list[Finding] = auditoria.argumentables[: cfg.max_findings_in_email] if auditoria else []
    dominio = registrable_domain(lead.url) or (lead.url or "").replace("https://", "").replace("http://", "").rstrip("/")
    nombre = lead.nombre or dominio or "tu negocio"
    dialecto = dialecto_por_url(lead.url)
    dispositivo = "celular" if dialecto == "voseo" else "móvil"
    inaccesible = bool(auditoria and auditoria.veredicto == "inaccesible")

    if not tiene_adjunto:
        frase_adjunto = ""
    elif es_marcada:
        frase_adjunto = "Te adjunto la captura con la zona marcada para que veas exactamente a qué me refiero.\n\n"
    else:
        frase_adjunto = "Te adjunto una captura de la portada tal como la vi.\n\n"

    prueba_social = _prueba_social(lead)
    frase_prueba = _frase_prueba(cfg)

    if not lead.url:
        asunto = random.choice(ASUNTOS_SIN_WEB).format(nombre=nombre, dominio=dominio)
        apertura = (
            f"Los busqué y tienen {prueba_social} en Maps, pero no hay web detrás."
            if prueba_social else
            "Los busqué en Google y aparecen en Maps, pero sin web."
        )
        cuerpo = (
            f"{_saludo(lead)}\n\n"
            f"{apertura} Quien los encuentra ahí no ve servicios ni precios ni forma de reservar, "
            f"así que termina abriendo la ficha del siguiente de la lista.\n\n"
            f"Me dedico a armar páginas de una sola pantalla para negocios como el suyo: "
            f"qué hacen, por qué elegirlos y un botón para escribir o llamar. Nada más.{frase_prueba}\n\n"
            f"Me lleva un par de horas armar un boceto de cómo se vería la de {nombre}. "
            f"¿Les sirve si se lo paso por acá? No cuesta nada verlo, y si no encaja, no pasa nada.\n\n"
            f"{cfg.sender_name}\n{cfg.sender_role}"
        )
    elif inaccesible:
        # No se puede decir que se miró la primera pantalla de una web que no
        # cargó: el correo se contradice solo y se nota en la primera línea.
        asunto = random.choice(ASUNTOS_CON_WEB).format(nombre=nombre, dominio=dominio, dispositivo=dispositivo)
        cuerpo = (
            f"{_saludo(lead)}\n\n"
            f"Intenté entrar a {dominio} buscando {lead.nicho or 'servicios de la zona'} y la página no cargó. "
            f"Probé de nuevo por si era algo puntual, pero el resultado fue el mismo.\n\n"
            f"Quien te busca y se encuentra eso no vuelve a intentarlo: entra al siguiente resultado. "
            f"Si el dominio o el hosting vencieron, o hay un error de configuración, es de las cosas más rápidas "
            f"de resolver y de las que más está costando en silencio.{frase_prueba}\n\n"
            f"¿Te interesa que te cuente exactamente qué encontré? Te lo mando sin compromiso.\n\n"
            f"{cfg.sender_name}\n{cfg.sender_role}"
        )
        tiene_adjunto = False  # no hay captura posible de una página que no cargó
    else:
        principal = hallazgos[0] if hallazgos else None
        secundario = hallazgos[1] if len(hallazgos) > 1 else None
        cuerpo_problema = principal.argumento if principal else (
            "La primera pantalla no está trabajando para convertir visitas en contactos."
        )
        extra = (
            f"\n\nY no es lo único: {_primera_minuscula(secundario.argumento)}"
            if secundario else ""
        )
        apertura_social = f" (con {prueba_social} se nota que hay demanda real)" if prueba_social else ""
        asunto = random.choice(ASUNTOS_CON_WEB).format(nombre=nombre, dominio=dominio, dispositivo=dispositivo)
        cuerpo = (
            f"{_saludo(lead)}\n\n"
            f"Entré en {dominio} buscando {lead.nicho or 'servicios de la zona'} y me quedé mirando la "
            f"primera pantalla{apertura_social}. {cuerpo_problema}{extra}\n\n"
            f"{frase_adjunto}"
            f"Me dedico a rehacer justo esa parte: misma marca, misma información, ordenada para que "
            f"el visitante sepa en tres segundos qué hacen y cómo contactarlos.{frase_prueba}\n\n"
            f"Me lleva un par de horas armar la portada: ¿te sirve si te la muestro con el enlace? "
            f"Si no te convence, no perdiste nada.\n\n"
            f"{cfg.sender_name}\n{cfg.sender_role}"
        )

    if cfg.sender_site:
        cuerpo += f"\n{cfg.sender_site}"
    return EmailDraft(asunto=asunto, cuerpo=limpiar(cuerpo, dialecto), generado_por="plantilla")


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
1. Máximo 130 palabras. Cuatro párrafos cortos como mucho.
2. La primera frase menciona algo CONCRETO y verificable de SU web (o, si no tiene, de su ficha de Maps).
   Nada de aperturas genéricas.
3. Traduce el problema técnico a consecuencia de negocio (clientes que se pierden), sin jerga. Si hay
   reputación en Maps, úsala como prueba de que la demanda ya existe (es un dato SUYO, no una estadística
   genérica: pesa mucho más). Prohibido inventar o citar estadísticas de la industria tipo "una de cada
   cuatro personas abandona" o "más de la mitad de las visitas son de móvil": si no es un dato medido de
   ESTE prospecto, no se afirma como hecho.
4. Prohibido: "espero que estés bien", "en el mundo actual", "llevar tu negocio al siguiente nivel",
   signos de exclamación, mayúsculas de énfasis, emojis, guiones largos.
5. {regla_adjunto}
6. Cierra ofreciendo un prototipo de la portada con una pregunta directa de bajo compromiso y un plazo
   concreto ("me lleva un par de horas", "lo tenés mañana"). Nunca digas que el prototipo de ESE negocio
   puntual ya existe o ya está hecho: no es cierto hasta que responda. Prohibido el patrón "¿te opondrías
   a...?" o cualquier doble negación tipo "¿no te molestaría que...?": preguntá directo, "¿te sirve si...?".
7. Firma como {firmante} ({rol}). Sin posdatas ni enlaces de baja.
8. {regla_dialecto}
{regla_prueba}
{regla_estado}

Devuelve solo:
{{"asunto": "en minúsculas, máximo 6 palabras, sin puntuación final", "cuerpo": "texto plano con saltos de línea"}}"""

REGLA_DIALECTO_VOSEO = (
    'Español rioplatense obligatorio. Segunda persona singular siempre con "vos" y conjugaciones '
    'voseantes: tenés, podés, querés, sabés, sos, hacés, decís, pensás. Nunca "tú", "tienes", "puedes", '
    '"eres". Plural siempre con "ustedes". Nunca "vosotros". Léxico argentino: "celular" (no "móvil"), '
    '"laburo" si corresponde, tono de persona real con prisa, no de agencia vendiendo.'
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
        "9. El sitio no cargó cuando lo visitamos (hallazgo sitio_inaccesible): NO digas que viste su "
        "primera pantalla ni que navegaste la web. Contá que intentaste entrar y no cargó."
        if inaccesible else ""
    )
    regla_prueba = (
        f'9. Si encaja de forma natural (no forzado), sumá esta prueba de que ya hiciste este trabajo: '
        f'"{cfg.sender_proof.strip()}".'
        if cfg.sender_proof.strip() else ""
    )

    prompt = PROMPT.format(
        plantilla=plantilla[:2500],
        nombre=lead.nombre or lead.url,
        nicho=lead.nicho or "no especificado",
        url=lead.url or "no tiene web (aparece solo en Google Maps)",
        reputacion=_prueba_social(lead) or "sin datos de rating/reseñas",
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
    return EmailDraft(
        asunto=limpiar(str(datos.get("asunto", "")), dialecto).strip().strip(".").lower(),
        cuerpo=cuerpo,
        generado_por="ia",
    )


# ─────────────────────────────── Orquestación ───────────────────────────────

def _ruta_adjunto(lead: Lead) -> tuple[str | None, bool]:
    """Candidato a adjunto y si es la versión con la zona marcada en rojo.

    La anotada es la estrella; si no existe, se cae a la captura cruda del
    fold. Distinguir cuál es cuál importa para el texto: prometer "la zona
    marcada" cuando lo único que hay es la captura sin anotar es la misma
    clase de mentira detectable que prometer un adjunto que no existe.
    """
    if not lead.audit:
        return None, False
    capturas = lead.audit.capturas
    marcada = capturas.get("principal") or capturas.get("anotada")
    if marcada:
        return marcada, True
    return capturas.get("desktop_fold") or None, False


def redactar(lead: Lead, cfg: ComposeSettings, cliente: GeminiClient | None, plantilla: str) -> EmailDraft:
    # Se decide ANTES de redactar: el cuerpo no puede prometer una captura que
    # el archivo en disco no respalda. Antes el mailer omitía el adjunto en
    # silencio si faltaba y el texto seguía diciendo "te adjunto la captura".
    adjunto, es_marcada = _ruta_adjunto(lead)
    ruta_absoluta = to_absolute(adjunto) if adjunto else None
    tiene_adjunto = bool(ruta_absoluta and ruta_absoluta.exists())

    borrador: EmailDraft | None = None
    if cliente is not None and cfg.use_ai and cliente.disponible:
        try:
            borrador = componer_con_ia(
                cliente, lead, cfg, plantilla, tiene_adjunto=tiene_adjunto, es_marcada=es_marcada,
            )
            problemas = _validar(borrador)
            if problemas:
                log.warning("Borrador IA rechazado para %s (%s)", lead.etiqueta, ", ".join(problemas))
                borrador = None
        except (AIUnavailable, ValueError, KeyError) as exc:
            log.warning("IA no disponible para %s: %s", lead.etiqueta, exc)

    if borrador is None:
        borrador = componer_por_plantilla(lead, cfg, tiene_adjunto=tiene_adjunto, es_marcada=es_marcada)

    borrador.adjunto = adjunto if tiene_adjunto else None
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
    # Sin web (o sin email hallado) pero con teléfono: no entran a la cola de
    # correo, pero sí se redactan para el canal manual (ver redactar_whatsapp).
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


def redactar_whatsapp(leads: list[Lead], cfg, forzar: bool = False) -> list[Lead]:
    """Redacta para el segmento sin email: mismo motor, mismo texto, pero
    termina en un archivo de texto para contactar a mano por WhatsApp, no en
    la cola de envío por correo (ver deliver/whatsapp.py para el volcado)."""
    from ..ai import get_client

    plantilla = cargar_plantilla()
    cliente = get_client(cfg.ai) if cfg.compose.use_ai and cfg.ai.enabled else None

    candidatos = [
        lead for lead in leads
        if lead.estado in {"auditado", "listo_whatsapp"} and (forzar or lead.email_draft is None)
        and not lead.contactable and lead.telefono
    ]
    for lead in candidatos:
        borrador = redactar(lead, cfg.compose, cliente, plantilla)
        lead.email_draft = borrador
        lead.estado = "listo_whatsapp"
        log.info("✎ %s (WhatsApp, %s) · «%s»", lead.etiqueta, lead.telefono, borrador.asunto)
    return leads
