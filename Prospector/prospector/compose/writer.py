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
from ..utils import registrable_domain

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

PALABRAS_SLOP = {
    "delve": "profundizar",
    "sinergia": "encaje",
    "holístico": "completo",
    "robusto": "sólido",
    "aprovechar": "usar",
    "maximizar": "subir",
    "optimizar al máximo": "mejorar",
    # Castellanismos que delatan origen no rioplatense
    "vosotros": "ustedes",
    "os ": "les ",
    "habéis": "tienen",
    "tenéis": "tienen",
    "hacéis": "hacen",
    "podéis": "pueden",
    "queréis": "quieren",
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
    "ves": "ves",       # igual en voseo, pero previene falsos positivos futuros
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
    "{dominio} en el celular",
    "un detalle de {dominio}",
    "{nombre}: la primera pantalla",
)


def cargar_plantilla() -> str:
    ruta = TEMPLATES_DIR / "primer_mensaje.md"
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


# ─────────────────────────────── Filtro anti-slop ───────────────────────────────

def limpiar(texto: str) -> str:
    """Quita las marcas típicas de texto generado y aprieta el tono."""
    if not texto:
        return ""
    limpio = texto.replace("\r\n", "\n")
    limpio = limpio.replace("—", ", ").replace("–", "-")
    limpio = re.sub(r"\*\*(.+?)\*\*", r"\1", limpio)   # negritas markdown
    limpio = re.sub(r"^#+\s*", "", limpio, flags=re.M)

    for frase in FRASES_PROHIBIDAS:
        limpio = re.sub(rf"[^.\n]*{re.escape(frase)}[^.\n]*[.。]?\s*", "", limpio, flags=re.I)
    for palabra, reemplazo in PALABRAS_SLOP.items():
        limpio = re.sub(rf"\b{re.escape(palabra)}\b", reemplazo, limpio, flags=re.I)

    limpio = re.sub(r"[ \t]{2,}", " ", limpio)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio)
    return limpio.strip()


def _validar(borrador: EmailDraft) -> list[str]:
    problemas = []
    palabras = len(borrador.cuerpo.split())
    if palabras > 160:
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

def _saludo(lead: Lead) -> str:
    nombre = (lead.nombre or "").strip()
    if not nombre:
        return "Hola,"
    corto = re.split(r"[|·,\-–]", nombre)[0].strip()
    return f"Hola, equipo de {corto}," if len(corto) <= 40 else "Hola,"


def componer_por_plantilla(lead: Lead, cfg: ComposeSettings) -> EmailDraft:
    """Redacción determinista: sin IA, sin coste, siempre disponible."""
    auditoria = lead.audit
    hallazgos: list[Finding] = auditoria.argumentables[: cfg.max_findings_in_email] if auditoria else []
    dominio = registrable_domain(lead.url) or (lead.url or "").replace("https://", "").replace("http://", "").rstrip("/")
    nombre = lead.nombre or dominio or "tu negocio"

    if not lead.url:
        asunto = random.choice(ASUNTOS_SIN_WEB).format(nombre=nombre, dominio=dominio)
        cuerpo = (
            f"{_saludo(lead)}\n\n"
            f"Los busqué en Google y aparecen en Maps, con reseñas, pero sin web. "
            f"Quien los encuentra ahí no ve servicios ni precios ni forma de reservar, "
            f"así que termina abriendo la ficha del siguiente de la lista.\n\n"
            f"Me dedico a armar páginas de una sola pantalla para negocios como el suyo: "
            f"qué hacen, por qué elegirlos y un botón para escribir o llamar. Nada más.\n\n"
            f"¿Les molesta si preparo un boceto de cómo se vería la de {nombre} y les paso el enlace? "
            f"Sin compromiso, y si no encaja lo tiramos.\n\n"
            f"{cfg.sender_name}\n{cfg.sender_role}"
        )
    else:
        principal = hallazgos[0] if hallazgos else None
        secundario = hallazgos[1] if len(hallazgos) > 1 else None
        cuerpo_problema = principal.argumento if principal else (
            "La primera pantalla no está trabajando para convertir visitas en contactos."
        )
        extra = f"\n\nTambién me llamó la atención otra cosa: {secundario.argumento.lower()}" if secundario else ""
        asunto = random.choice(ASUNTOS_CON_WEB).format(nombre=nombre, dominio=dominio)
        cuerpo = (
            f"{_saludo(lead)}\n\n"
            f"Entré en {dominio} buscando {lead.nicho or 'servicios de la zona'} y me quedé mirando la "
            f"primera pantalla. {cuerpo_problema}{extra}\n\n"
            f"Te adjunto la captura con la zona marcada para que veas exactamente a qué me refiero.\n\n"
            f"Me dedico a rehacer justo esa parte: misma marca, misma información, ordenada para que "
            f"el visitante sepa en tres segundos qué hacen y cómo contactarlos.\n\n"
            f"¿Te opondrías a que arme un prototipo de la portada y te pase el enlace? "
            f"Sin compromiso; si no te convence, no hay más que hablar.\n\n"
            f"{cfg.sender_name}\n{cfg.sender_role}"
        )

    if cfg.sender_site:
        cuerpo += f"\n{cfg.sender_site}"
    return EmailDraft(asunto=asunto, cuerpo=limpiar(cuerpo), generado_por="plantilla")


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
- Señales objetivas medidas por nosotros (datos reales, no inventes otros):
{hallazgos}
{vision}

Reglas innegociables:
1. Máximo 130 palabras. Cuatro párrafos cortos como mucho.
2. La primera frase menciona algo CONCRETO y verificable de SU web. Nada de aperturas genéricas.
3. Traduce el problema técnico a consecuencia de negocio (clientes que se pierden), sin jerga.
4. Prohibido: "espero que estés bien", "en el mundo actual", "llevar tu negocio al siguiente nivel",
   signos de exclamación, mayúsculas de énfasis, emojis, guiones largos.
5. Menciona en una frase que adjuntas una captura con la zona marcada.
6. Cierra con una pregunta de bajo compromiso ofreciendo un prototipo de la portada.
7. Firma como {firmante} ({rol}). Sin posdatas ni enlaces de baja.
8. Español rioplatense obligatorio. Segunda persona singular siempre con "vos" y conjugaciones voseantes:
   tenés, podés, querés, sabés, sos, hacés, decís, pensás. Nunca "tú", "tienes", "puedes", "eres".
   Plural siempre con "ustedes". Nunca "vosotros". Léxico argentino: "celular" (no "móvil"), "laburo" si
   corresponde, tono de persona real con prisa, no de agencia vendiendo.

Devuelve solo:
{{"asunto": "en minúsculas, máximo 6 palabras, sin puntuación final", "cuerpo": "texto plano con saltos de línea"}}"""


def componer_con_ia(cliente: GeminiClient, lead: Lead, cfg: ComposeSettings, plantilla: str) -> EmailDraft:
    auditoria = lead.audit
    hallazgos = auditoria.argumentables[:3] if auditoria else []
    lista = "\n".join(f"  - {h.titulo}: {h.evidencia}. {h.argumento}" for h in hallazgos) or "  - (sin datos)"
    vision = ""
    if auditoria and auditoria.vision.get("problema_visual"):
        vision = (
            f"- Observación visual del revisor: {auditoria.vision['problema_visual']}"
            f" ({auditoria.vision.get('detalle_observado', '')})"
        )

    prompt = PROMPT.format(
        plantilla=plantilla[:2500],
        nombre=lead.nombre or lead.url,
        nicho=lead.nicho or "no especificado",
        url=lead.url or "no tiene web (aparece solo en Google Maps)",
        hallazgos=lista,
        vision=vision,
        firmante=cfg.sender_name,
        rol=cfg.sender_role,
    )
    datos = cliente.generar_json(prompt, temperatura=0.8)
    cuerpo = limpiar(str(datos.get("cuerpo", "")))
    if cfg.sender_site and cfg.sender_site not in cuerpo:
        cuerpo += f"\n{cfg.sender_site}"
    return EmailDraft(
        asunto=limpiar(str(datos.get("asunto", ""))).strip().strip(".").lower(),
        cuerpo=cuerpo,
        generado_por="ia",
    )


# ─────────────────────────────── Orquestación ───────────────────────────────

def redactar(lead: Lead, cfg: ComposeSettings, cliente: GeminiClient | None, plantilla: str) -> EmailDraft:
    borrador: EmailDraft | None = None
    if cliente is not None and cfg.use_ai and cliente.disponible:
        try:
            borrador = componer_con_ia(cliente, lead, cfg, plantilla)
            problemas = _validar(borrador)
            if problemas:
                log.warning("Borrador IA rechazado para %s (%s)", lead.etiqueta, ", ".join(problemas))
                borrador = None
        except (AIUnavailable, ValueError, KeyError) as exc:
            log.warning("IA no disponible para %s: %s", lead.etiqueta, exc)

    if borrador is None:
        borrador = componer_por_plantilla(lead, cfg)

    # La captura anotada es el adjunto estrella; si no hay, va la del fold.
    if lead.audit:
        borrador.adjunto = (
            lead.audit.capturas.get("principal")
            or lead.audit.capturas.get("anotada")
            or lead.audit.capturas.get("desktop_fold")
            or None
        )
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
    sin_correo = [lead for lead in leads if lead.estado == "auditado" and not lead.contactable]
    if sin_correo:
        log.info("%d leads calificados no tienen email todavía (usa 'mine --enriquecer')", len(sin_correo))

    for lead in candidatos:
        borrador = redactar(lead, cfg.compose, cliente, plantilla)
        lead.email_draft = borrador
        lead.estado = "listo"
        log.info("✎ %s · «%s» (%s)", lead.etiqueta, borrador.asunto, borrador.generado_por)
    return leads
