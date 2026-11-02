def traza_borrador(lead) -> dict:
    """Qué versión, variante y falla llevó el mensaje: va a cada fila del registro."""
    b = lead.email_draft
    return {"generado_por": b.generado_por if b else None,
            "variante": b.variante if b else None,
            "regla": b.regla if b else None}


from .mailer import cola_pendiente, construir_mensaje, enviar
from .preview import exportar as exportar_preview
from .quota import Quota
from .whatsapp import cola_pendiente as cola_whatsapp
from .whatsapp import cuota as cuota_whatsapp
from .whatsapp import exportar as exportar_whatsapp
from .whatsapp import registrar_envio as registrar_whatsapp

__all__ = [
    "cola_pendiente", "construir_mensaje", "enviar", "Quota",
    "exportar_whatsapp", "exportar_preview",
    "cola_whatsapp", "cuota_whatsapp", "registrar_whatsapp",
]
