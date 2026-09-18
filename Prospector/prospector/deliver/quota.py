"""Control de cuota y ventana de envío: la parte que salva la reputación del dominio."""
from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

from ..config import MailSettings, WhatsAppSettings
from ..storage import read_json, write_json


class Quota:
    """Lleva la cuenta de envíos por día y decide si toca parar.

    Sirve para los dos canales: solo necesita `daily_cap`, `skip_weekends` y
    la ventana horaria, que `MailSettings` y `WhatsAppSettings` tienen por
    igual. WhatsApp no tenía ninguna de las tres, que es justo el canal donde
    pasarse cuesta el número en vez de cuesta entregabilidad.
    """

    def __init__(self, cfg: MailSettings | WhatsAppSettings, ruta: Path) -> None:
        self.cfg = cfg
        self.ruta = ruta
        self.registro: dict[str, int] = read_json(ruta, {}) or {}

    @property
    def hoy(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @property
    def enviados_hoy(self) -> int:
        return int(self.registro.get(self.hoy, 0))

    @property
    def restantes(self) -> int:
        return max(0, self.cfg.daily_cap - self.enviados_hoy)

    def anotar(self) -> None:
        self.registro[self.hoy] = self.enviados_hoy + 1
        write_json(self.ruta, self.registro)

    def en_ventana(self, momento: datetime | None = None) -> tuple[bool, str]:
        ahora = momento or datetime.now()
        if self.cfg.skip_weekends and ahora.weekday() >= 5:
            return False, "es fin de semana (un mensaje de trabajo el sábado se lee peor)"
        inicio = time(self.cfg.window_start_h, 0)
        fin = time(self.cfg.window_end_h, 0)
        if not (inicio <= ahora.time() <= fin):
            return False, (
                f"fuera de la ventana de envío ({self.cfg.window_start_h}:00-{self.cfg.window_end_h}:00)"
            )
        return True, ""
