"""Modelo de datos del pipeline. Serializable a JSON, sin dependencias externas."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any

from .utils import lead_id as make_lead_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _clean(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


class _Serializable:
    def to_dict(self) -> dict[str, Any]:
        return _clean(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


@dataclass(slots=True)
class Finding(_Serializable):
    """Un defecto concreto detectado, con su munición de venta.

    La munición viene partida en tres piezas en vez de en un párrafo único.
    El párrafo único obligaba a `writer.py` a agregar su propia consecuencia
    genérica detrás (porque no sabía si el argumento ya la traía), y eso
    producía la misma idea dicha dos veces en el 70% de los mensajes, más un
    puente hacia la oferta que hablaba siempre de CTA aunque el hallazgo fuera
    la velocidad de carga. Partido, cada canal arma lo que le entra:

      · observacion   → lo que SE VE, sin consecuencia. Es la primera línea.
      · consecuencia  → lo que le cuesta, en plata o en clientes. Una sola vez.
      · puente        → la transición hacia la oferta, propia de ESTE defecto.

    `argumento` se conserva como campo para no romper los JSON ya guardados
    (y para quien solo quiera el párrafo entero): si no se pasa, se deriva.
    """

    rule_id: str
    titulo: str
    severidad: int          # 1-10, cuánto duele
    peso: int               # puntos que aporta al score de oportunidad
    evidencia: str          # dato duro medido ("LCP 6.2 s", "0 CTA en el fold")
    argumento: str = ""     # observacion + consecuencia, derivado si no se pasa
    observacion: str = ""   # lo que se ve, sin consecuencia
    consecuencia: str = ""  # lo que cuesta, dicho una vez
    puente: str = ""        # transición hacia la oferta, específica del defecto
    viewport: str = "desktop"   # desktop | mobile | ambos
    zona: dict[str, float] | None = None  # rect x,y,width,height para anotar la captura
    categoria: str = "moderado"  # killer | moderado | cosmetico — ver rules.py

    def __post_init__(self) -> None:
        # Nuevo → viejo: el párrafo se arma solo.
        if not self.argumento:
            piezas = []
            for texto in (self.observacion, self.consecuencia):
                texto = (texto or "").strip()
                if not texto:
                    continue
                texto = texto[:1].upper() + texto[1:]
                if not texto.endswith((".", "!", "?")):
                    texto += "."
                piezas.append(texto)
            self.argumento = " ".join(piezas)
        # Viejo → nuevo: un Finding releído de un JSON anterior solo trae
        # `argumento`. Se usa entero como observación para que los redactores
        # nuevos sigan produciendo texto en vez de un hueco.
        if not self.observacion:
            self.observacion = self.argumento

    @property
    def legado(self) -> bool:
        """True si viene de una auditoría anterior a la partición en tres.

        Importa porque su `observacion` es en realidad el párrafo entero, con
        la consecuencia adentro: si el redactor le agrega encima su
        consecuencia de reserva, vuelve a decir lo mismo dos veces, que es
        justo lo que se estaba arreglando. Un `audit --forzar` lo resuelve de
        raíz; mientras tanto, el redactor no duplica.
        """
        return not self.consecuencia.strip()


@dataclass(slots=True)
class Metrics(_Serializable):
    """Datos duros medidos en el navegador."""

    http_status: int | None = None
    https: bool | None = None
    redirected_to: str | None = None
    load_ms: float | None = None
    dom_ready_ms: float | None = None
    lcp_ms: float | None = None
    cls: float | None = None
    ttfb_ms: float | None = None
    peso_kb: float | None = None
    peticiones: int | None = None
    imagenes_pesadas_kb: float | None = None
    tiene_viewport_meta: bool | None = None
    overflow_horizontal_mobile: bool | None = None
    ancho_scroll_mobile: int | None = None
    texto_pequeno_mobile: int | None = None
    tap_targets_pequenos: int | None = None
    ctas_en_fold: int | None = None
    tiene_formulario: bool | None = None
    tiene_tel: bool | None = None
    tiene_whatsapp: bool | None = None
    # Números sacados de la propia web. El de WhatsApp es el único verificado
    # que existe: lo publicó el negocio y por definición está en WhatsApp. El
    # de Maps es una línea fija el 69% de las veces, y un fijo no se puede
    # convertir en celular: no existe ese algoritmo.
    whatsapp_web: str | None = None      # número detrás del enlace wa.me
    tel_web: str | None = None           # número detrás del primer enlace tel:
    h1: int | None = None
    title: str | None = None
    meta_description: str | None = None
    og_image: bool | None = None
    favicon: bool | None = None
    imagenes_sin_alt: int | None = None
    palabras_en_fold: int | None = None
    generador: str | None = None
    ano_copyright: int | None = None
    popup_intrusivo: bool | None = None
    items_menu: int | None = None
    # Detección de páginas directorio/agregador
    tels_unicos: int | None = None          # número de tel: distintos en la página
    emails_unicos: int | None = None        # número de mailto: distintos
    titulo_parece_directorio: bool | None = None  # título con patrón "mejores X en Y"
    error: str | None = None


@dataclass(slots=True)
class Audit(_Serializable):
    score: int = 0                       # 0-100: cuánta oportunidad hay (más = peor web)
    veredicto: str = "sin_auditar"       # sin_web | critico | mejorable | sano | inaccesible
    findings: list[Finding] = field(default_factory=list)
    metrics: Metrics = field(default_factory=Metrics)
    capturas: dict[str, str] = field(default_factory=dict)   # rutas RELATIVAS al proyecto
    vision: dict[str, Any] = field(default_factory=dict)     # dictamen del jurado IA
    # True solo si la captura "anotada" tiene de verdad un recuadro rojo
    # dibujado (hubo una zona detectable). Sin esto, "anotada" solo
    # significaba "se le puso un pie de foto", y el correo podía prometer
    # "la zona marcada" sobre una imagen sin ninguna marca.
    captura_marcada: bool = False
    auditado_el: str = field(default_factory=_now)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Audit":
        data = dict(data or {})
        return cls(
            score=int(data.get("score", 0)),
            veredicto=data.get("veredicto", "sin_auditar"),
            findings=[Finding.from_dict(f) for f in data.get("findings", [])],
            metrics=Metrics.from_dict(data.get("metrics", {})),
            capturas=dict(data.get("capturas", {})),
            vision=dict(data.get("vision", {})),
            captura_marcada=bool(data.get("captura_marcada", False)),
            auditado_el=data.get("auditado_el", _now()),
        )

    @property
    def top_findings(self) -> list[Finding]:
        return sorted(self.findings, key=lambda f: (-f.severidad, -f.peso))

    @property
    def argumentables(self) -> list[Finding]:
        """Hallazgos con peso real de venta: nunca lidera el correo un detalle
        cosmético (falta de favicon, SEO) solo porque no había nada más grave."""
        return [f for f in self.top_findings if f.categoria != "cosmetico"]


@dataclass(slots=True)
class EmailDraft(_Serializable):
    asunto: str = ""
    cuerpo: str = ""
    adjunto: str | None = None      # ruta relativa a la captura anotada
    generado_por: str = "plantilla"  # ia | plantilla
    redactado_el: str = field(default_factory=_now)


@dataclass(slots=True)
class Lead(_Serializable):
    id: str = ""
    nombre: str = ""
    url: str | None = None
    email: str | None = None
    emails: list[str] = field(default_factory=list)
    telefono: str | None = None
    direccion: str | None = None
    categoria: str | None = None
    rating: float | None = None
    resenas: int | None = None
    nicho: str = ""
    fuente: str = "google_maps"
    tiene_web: bool = True
    # crudo | auditado | descartado | listo | listo_whatsapp | enviado |
    # enviado_whatsapp | rebotado | respondido | baja  (ver storage._PROGRESO)
    estado: str = "crudo"
    motivo_descarte: str | None = None
    audit: Audit | None = None
    email_draft: EmailDraft | None = None
    enviado_el: str | None = None
    # Por qué vía se contactó. Sin esto, correo y WhatsApp comparten el estado
    # "enviado" y no hay forma de separar dos canales con ritmos, costos y
    # tasas de respuesta distintas.
    canal: str | None = None        # email | whatsapp
    # Quien contestó sale de todas las colas para siempre. Es la garantía más
    # importante del sistema: escribirle "por si no lo viste" a alguien que ya
    # te respondió es la delación de robot más cara que existe.
    respondido_el: str | None = None
    nota_respuesta: str | None = None
    creado_el: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = make_lead_id(self.url, self.nombre, self.email)
        if self.email and self.email not in self.emails:
            self.emails.insert(0, self.email)
        if not self.email and self.emails:
            self.email = self.emails[0]
        self.tiene_web = bool(self.url)

    @property
    def contactable(self) -> bool:
        return bool(self.email)

    @property
    def etiqueta(self) -> str:
        return self.nombre or self.url or self.id

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Lead":
        data = dict(data or {})
        audit = data.pop("audit", None)
        draft = data.pop("email_draft", None)
        known = {f.name for f in fields(cls)}
        lead = cls(**{k: v for k, v in data.items() if k in known})
        if audit:
            lead.audit = Audit.from_dict(audit)
        if draft:
            lead.email_draft = EmailDraft.from_dict(draft)
        return lead
