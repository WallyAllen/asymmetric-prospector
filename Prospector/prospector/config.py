"""Configuración central. Todo lo ajustable vive aquí, nada de constantes sueltas."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "01_raw"
AUDITED_DIR = DATA_DIR / "02_audited"
COMPOSED_DIR = DATA_DIR / "03_composed"
SENT_DIR = DATA_DIR / "04_sent"
WHATSAPP_DIR = DATA_DIR / "05_whatsapp"
SHOTS_DIR = DATA_DIR / "screenshots"
LOGS_DIR = DATA_DIR / "logs"
TEMPLATES_DIR = BASE_DIR / "templates"

RAW_FILE = RAW_DIR / "leads_crudos.json"
AUDITED_FILE = AUDITED_DIR / "leads_auditados.json"
COMPOSED_FILE = COMPOSED_DIR / "leads_listos.json"
SENT_FILE = SENT_DIR / "registro_envios.json"
SUPPRESSION_FILE = SENT_DIR / "lista_supresion.txt"


def _load_dotenv() -> None:
    """Carga .env sin depender de python-dotenv (una dependencia menos)."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
MOBILE_VIEWPORT = {"width": 390, "height": 844}
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


@dataclass(slots=True)
class MiningSettings:
    max_leads: int = field(default_factory=lambda: _env_int("MINE_MAX_LEADS", 40))
    max_scrolls: int = field(default_factory=lambda: _env_int("MINE_MAX_SCROLLS", 8))
    fetch_contacts: bool = field(default_factory=lambda: _env_bool("MINE_FETCH_CONTACTS", True))
    include_without_site: bool = field(
        default_factory=lambda: _env_bool("MINE_INCLUDE_WITHOUT_SITE", True)
    )
    nav_timeout_ms: int = field(default_factory=lambda: _env_int("MINE_NAV_TIMEOUT_MS", 30000))
    headless: bool = field(default_factory=lambda: _env_bool("HEADLESS", True))


@dataclass(slots=True)
class AuditSettings:
    nav_timeout_ms: int = field(default_factory=lambda: _env_int("AUDIT_TIMEOUT_MS", 30000))
    concurrency: int = field(default_factory=lambda: _env_int("AUDIT_CONCURRENCY", 3))
    headless: bool = field(default_factory=lambda: _env_bool("HEADLESS", True))
    # Umbral de score (0-100). Por debajo, el sitio está sano: se descarta.
    min_score: int = field(default_factory=lambda: _env_int("AUDIT_MIN_SCORE", 28))
    # Solo se paga IA por encima de este score.
    vision_threshold: int = field(default_factory=lambda: _env_int("AUDIT_VISION_THRESHOLD", 55))
    use_vision: bool = field(default_factory=lambda: _env_bool("AUDIT_USE_VISION", True))
    annotate: bool = field(default_factory=lambda: _env_bool("AUDIT_ANNOTATE", True))


@dataclass(slots=True)
class ComposeSettings:
    use_ai: bool = field(default_factory=lambda: _env_bool("COMPOSE_USE_AI", True))
    sender_name: str = field(default_factory=lambda: _env("SENDER_NAME", "Felipe"))
    sender_role: str = field(default_factory=lambda: _env("SENDER_ROLE", "Diseño y CRO de landing pages"))
    sender_site: str = field(default_factory=lambda: _env("SENDER_SITE", ""))
    # Una línea de prueba social REAL y verificable (p. ej. "hice esto mismo
    # para un estudio contable acá en La Plata"). Vacío por defecto: nunca se
    # inventa una referencia, solo se usa si vos la completás en .env.
    sender_proof: str = field(default_factory=lambda: _env("SENDER_PROOF", ""))
    max_findings_in_email: int = field(default_factory=lambda: _env_int("COMPOSE_MAX_FINDINGS", 2))


@dataclass(slots=True)
class MailSettings:
    server: str = field(default_factory=lambda: _env("SMTP_SERVER", "smtp.gmail.com"))
    port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 587))
    user: str = field(default_factory=lambda: _env("SMTP_USER"))
    password: str = field(default_factory=lambda: _env("SMTP_PASSWORD"))
    from_name: str = field(default_factory=lambda: _env("SENDER_NAME", "Felipe"))
    reply_to: str = field(default_factory=lambda: _env("REPLY_TO"))
    daily_cap: int = field(default_factory=lambda: _env_int("MAIL_DAILY_CAP", 30))
    jitter_min_s: int = field(default_factory=lambda: _env_int("MAIL_JITTER_MIN_S", 360))
    jitter_max_s: int = field(default_factory=lambda: _env_int("MAIL_JITTER_MAX_S", 840))
    # Ventana horaria local en la que se permite enviar (hora de oficina = más humano).
    window_start_h: int = field(default_factory=lambda: _env_int("MAIL_WINDOW_START", 9))
    window_end_h: int = field(default_factory=lambda: _env_int("MAIL_WINDOW_END", 19))
    skip_weekends: bool = field(default_factory=lambda: _env_bool("MAIL_SKIP_WEEKENDS", True))


@dataclass(slots=True)
class AISettings:
    api_key: str = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    model: str = field(default_factory=lambda: _env("GEMINI_MODEL", "gemini-2.5-flash"))
    temperature_vision: float = field(default_factory=lambda: _env_float("GEMINI_TEMP_VISION", 0.2))
    temperature_copy: float = field(default_factory=lambda: _env_float("GEMINI_TEMP_COPY", 0.75))
    max_retries: int = field(default_factory=lambda: _env_int("GEMINI_MAX_RETRIES", 3))
    min_interval_s: float = field(default_factory=lambda: _env_float("GEMINI_MIN_INTERVAL_S", 4.0))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


@dataclass(slots=True)
class Settings:
    mining: MiningSettings = field(default_factory=MiningSettings)
    audit: AuditSettings = field(default_factory=AuditSettings)
    compose: ComposeSettings = field(default_factory=ComposeSettings)
    mail: MailSettings = field(default_factory=MailSettings)
    ai: AISettings = field(default_factory=AISettings)


def ensure_dirs() -> None:
    for d in (RAW_DIR, AUDITED_DIR, COMPOSED_DIR, SENT_DIR, WHATSAPP_DIR, SHOTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


settings = Settings()
