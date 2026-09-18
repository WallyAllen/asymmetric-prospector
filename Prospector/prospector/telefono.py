"""Normalización de teléfonos a formato WhatsApp, y de dónde sacar el mejor.

Por qué esto es un módulo propio y no dos líneas sueltas: **el 69% de los
teléfonos que Maps devuelve son líneas fijas**, y la versión anterior
(`scripts/send_whatsapp.py`) les anteponía un `9` a todos. Un `9` delante de
un número argentino no lo convierte en el celular de ese negocio: lo convierte
en *otro* número, el celular de alguien más. De los 56 mensajes de la primera
tanda, 33 salieron así.

La regla del plan de numeración argentino, que es lo único que hay que
respetar:

    fijo    0 221 421-9413      →  54 221 4219413      (sin 9)
    móvil   0 221 15-421-9413   →  54 9 221 4219413    (con 9, sin el 15)

No hay forma de deducir el segundo a partir del primero. Son dos números
distintos. Así que acá **nunca se inventa un dígito**: se convierte fielmente
y se etiqueta con qué confianza, y quien envía decide.

Orden de preferencia para elegir a qué número escribir:

    1. el `wa.me` de su propia web  → verificado: lo publicó el negocio
    2. un `tel:` de su web que sea móvil
    3. el teléfono de Maps, si es móvil
    4. cualquier fijo                → puede tener WhatsApp Business, o no:
                                       si no lo tiene, WhatsApp lo dice al
                                       abrir el chat y no se manda nada, que
                                       es exactamente el fallo que se quiere
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

# Países donde el móvil lleva un dígito extra después del código de país.
# Argentina intercala un 9; España, México (hoy) y el resto de esta lista no.
_MOVIL_NACIONAL = {"54": "9"}

# Un E.164 sin el "+" tiene entre 8 y 15 dígitos.
_LARGO_MIN, _LARGO_MAX = 8, 15


@dataclass(frozen=True, slots=True)
class Telefono:
    """Un número listo para `wa.me`, con su procedencia.

    · `e164`      dígitos, sin "+", como lo quiere wa.me. "" si no se pudo.
    · `tipo`      movil | fijo | internacional | invalido
    · `verificado` True solo si el número salió de un enlace de WhatsApp
                   publicado por el propio negocio.
    """

    e164: str
    tipo: str
    verificado: bool = False

    def __bool__(self) -> bool:
        return bool(self.e164)

    @property
    def confianza(self) -> int:
        """Para ordenar la cola: primero a quien seguro está en WhatsApp."""
        if not self.e164:
            return 0
        if self.verificado:
            return 3
        return {"movil": 2, "internacional": 2, "fijo": 1}.get(self.tipo, 1)

    @property
    def etiqueta(self) -> str:
        if self.verificado:
            return "WhatsApp publicado en su web"
        return {"movil": "celular", "fijo": "línea fija (puede no tener WhatsApp)",
                "internacional": "número internacional"}.get(self.tipo, "sin teléfono usable")


SIN_TELEFONO = Telefono("", "invalido")


def _digitos(crudo: str | None) -> tuple[str, bool]:
    """(solo dígitos, venía con prefijo internacional explícito)."""
    limpio = re.sub(r"[^\d+]", "", crudo or "")
    if limpio.startswith("+"):
        return re.sub(r"\D", "", limpio), True
    solo = re.sub(r"\D", "", limpio)
    if solo.startswith("00"):          # prefijo de salida internacional
        return solo[2:], True
    return solo, False


def normalizar(crudo: str | None, cc: str = "54") -> Telefono:
    """Un teléfono en cualquier formato → E.164 sin "+", sin inventar dígitos."""
    digitos, internacional = _digitos(crudo)
    if not digitos:
        return SIN_TELEFONO

    movil = _MOVIL_NACIONAL.get(cc, "")

    if internacional or digitos.startswith(cc) and len(digitos) >= len(cc) + 9:
        if not digitos.startswith(cc):
            # Otro país: se respeta tal cual, no se le aplica el plan local.
            return _acotar(digitos, "internacional")
        resto = digitos[len(cc):]
        if movil and resto.startswith(movil) and len(resto) >= 10:
            return _acotar(digitos, "movil")
        return _acotar(digitos, "fijo")

    nacional = digitos.lstrip("0")     # el 0 es prefijo de larga distancia
    if not nacional:
        return SIN_TELEFONO

    # Móvil escrito a la argentina: área + 15 + abonado.
    coincidencia = re.match(r"^(\d{2,4})15(\d{6,8})$", nacional) if movil else None
    if coincidencia:
        area, abonado = coincidencia.groups()
        return _acotar(f"{cc}{movil}{area}{abonado}", "movil")

    # Sin 15 y sin prefijo internacional: es una línea fija. NO se le pone el
    # 9: eso no da el celular del negocio, da el de otra persona.
    return _acotar(f"{cc}{nacional}", "fijo")


def _acotar(digitos: str, tipo: str) -> Telefono:
    return Telefono(digitos, tipo) if _LARGO_MIN <= len(digitos) <= _LARGO_MAX else SIN_TELEFONO


def de_enlace_whatsapp(href: str | None) -> Telefono:
    """El número detrás de un `wa.me/…`, `api.whatsapp.com/send?phone=…`.

    Es el único número del que se sabe con certeza que está en WhatsApp: lo
    publicó el negocio en su propia web. `probe_js.py` ya encontraba estos
    enlaces desde el principio — los contaba y tiraba el href.
    """
    if not href:
        return SIN_TELEFONO
    try:
        url = urlparse(href)
    except ValueError:
        return SIN_TELEFONO
    crudo = (parse_qs(url.query).get("phone") or [""])[0]
    if not crudo:
        crudo = url.path.strip("/").split("/")[-1]
    digitos = re.sub(r"\D", "", crudo)
    if not (_LARGO_MIN <= len(digitos) <= _LARGO_MAX):
        return SIN_TELEFONO
    tipo = "movil" if digitos.startswith("549") else "fijo"
    return Telefono(digitos, tipo, verificado=True)


def para_whatsapp(lead, cc: str = "54") -> Telefono:
    """El mejor número al que escribirle a este lead, o SIN_TELEFONO.

    Nunca devuelve algo "aproximado": si no se puede normalizar con confianza,
    devuelve vacío y quien envía saltea el lead. Abrir el chat equivocado es
    peor que no escribir.
    """
    metricas = getattr(getattr(lead, "audit", None), "metrics", None)

    if metricas is not None:
        verificado = de_enlace_whatsapp(getattr(metricas, "whatsapp_web", None))
        if verificado:
            return verificado
        del_sitio = normalizar(getattr(metricas, "tel_web", None), cc)
        if del_sitio.tipo == "movil":
            return del_sitio
    else:
        del_sitio = SIN_TELEFONO

    de_maps = normalizar(getattr(lead, "telefono", None), cc)
    if de_maps.tipo in ("movil", "internacional"):
        return de_maps
    return de_maps or del_sitio
