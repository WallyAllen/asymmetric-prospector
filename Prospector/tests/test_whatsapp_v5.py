"""Contrato de la spec 009: toque 1 por WhatsApp v5, la falla medida.

Todos los leads son ficticios (`ejemplo.com.ar`, `Inmobiliaria Ejemplo`): este
repo es público y `data/` no entra en un test.
"""
from __future__ import annotations

import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector import lint  # noqa: E402
from prospector.compose.whatsapp import (componer_whatsapp, estilo_felipe,  # noqa: E402
                                         redactar_whatsapp)
from prospector.compose.writer import validar  # noqa: E402
from prospector.config import ComposeSettings  # noqa: E402
from prospector.models import Audit, EmailDraft, Finding, Lead, Metrics  # noqa: E402

HOY = date(2026, 10, 26)
RECIENTE = "2026-10-20T12:00:00+00:00"   # 6 días antes de HOY
VIEJA = "2026-09-30T12:00:00+00:00"      # 26 días antes de HOY

INMOBILIARIA = "inmobiliarias zona norte"


def _f(rule_id: str, categoria: str = "killer", severidad: int = 8, peso: int = 20) -> Finding:
    return Finding(rule_id=rule_id, titulo=rule_id, severidad=severidad, peso=peso,
                   evidencia="dato medido", observacion="Algo medido.",
                   consecuencia="El que los busca se va sin ponerse en contacto.",
                   categoria=categoria)


def _lead(*hallazgos: Finding, nicho: str = INMOBILIARIA, id: str = "ejemplo-1",
          lcp_ms: float = 5300, auditado_el: str = RECIENTE,
          estado: str = "auditado") -> Lead:
    lead = Lead(id=id, nombre="Inmobiliaria Ejemplo", url="https://ejemplo.com.ar",
                telefono="1100000000", nicho=nicho, estado=estado)
    lead.audit = Audit(score=60, veredicto="critico", findings=list(hallazgos),
                       metrics=Metrics(lcp_ms=lcp_ms), auditado_el=auditado_el)
    return lead


class _Cfg:
    """Lo único de `Settings` que lee `redactar_whatsapp`."""

    def __init__(self) -> None:
        self.compose = ComposeSettings(sender_name="Felipe", sender_role="", sender_site="",
                                       sender_phone="", sender_proof="",
                                       sender_pitch="armo páginas web")


def _redactar(*leads: Lead) -> list[Lead]:
    return redactar_whatsapp(list(leads), _Cfg(), hoy=HOY)


def _cuerpo(lead: Lead) -> str:
    return componer_whatsapp(lead, _Cfg().compose).cuerpo


def _bloques(cuerpo: str) -> list[str]:
    return [b for b in cuerpo.split("\n\n") if b.strip()]


class TestQueLidera(unittest.TestCase):
    def test_sin_falla_verificable_se_descarta(self):
        """88 inmobiliarias de la cola no tienen nada que se compruebe abriendo
        la web. No se les escribe con una falla inventada."""
        lead = _lead(_f("sin_cta_fold", severidad=9), _f("tap_targets", "moderado"))
        _redactar(lead)
        self.assertEqual("descartado", lead.estado)
        self.assertEqual("sin falla verificable para toque 1", lead.motivo_descarte)
        self.assertIsNone(lead.email_draft)

    def test_carga_moderada_no_lidera(self):
        """Un LCP de 3 s no lo nota quien abre la web: no puede liderar."""
        lead = _lead(_f("carga_lenta", "moderado"), lcp_ms=3100)
        _redactar(lead)
        self.assertEqual("descartado", lead.estado)

    def test_sin_cta_fold_no_lidera_en_inmobiliarias(self):
        """El buscador hace de botón y el auditor no lo cuenta: "no hay ningún
        botón" puede ser falso."""
        lead = _lead(_f("sin_cta_fold", severidad=9), _f("sin_contacto", severidad=7))
        _redactar(lead)
        self.assertEqual("sin_contacto", lead.email_draft.regla)

    def test_lidera_la_primera_regla_de_la_lista(self):
        lead = _lead(_f("sin_cta_fold", severidad=9),
                     _f("carga_lenta", severidad=8),
                     _f("sin_contacto", severidad=7))
        _redactar(lead)
        self.assertEqual("carga_lenta", lead.email_draft.regla)
        self.assertIn("5,3 segundos", lead.email_draft.cuerpo)


class TestTexto(unittest.TestCase):
    def test_consecuencia_inmobiliaria_por_regla(self):
        """La consecuencia genérica ("se va sin ponerse en contacto") no está
        escrita para una inmobiliaria."""
        for regla in ("carga_lenta", "sin_contacto", "sin_tel_movil", "overflow_mobile",
                      "sin_viewport", "popup_intrusivo"):
            with self.subTest(regla=regla):
                medio = _bloques(_cuerpo(_lead(_f(regla))))[1]
                self.assertNotIn("ponerse en contacto", medio)
                self.assertRegex(medio.lower(), r"casa|propiedad|propietario|inmobiliaria")

    def test_otro_rubro_usa_consecuencia_de_rules(self):
        lead = _lead(_f("sin_contacto"), nicho="veterinarias la plata")
        self.assertIn("El que los busca se va sin ponerse en contacto", _cuerpo(lead))

    def test_no_menciona_sistema_crm_ni_pide_numeros(self):
        """Tres rechazos contestaron "ya tenemos CRM/sistema": la pregunta del
        cierre les servía de salida."""
        for i in range(30):
            cuerpo = _cuerpo(_lead(_f("carga_lenta"), id=f"ejemplo-{i}")).lower()
            self.assertNotRegex(cuerpo, r"sistema|crm|tokko|cuant[oa]s|por mes")

    def test_cierre_es_pregunta_si_no(self):
        for i in range(30):
            cuerpo = _cuerpo(_lead(_f("sin_tel_movil"), id=f"ejemplo-{i}"))
            self.assertTrue(cuerpo.rstrip().endswith("?"), cuerpo)
            # La pregunta es lo que sigue a la última coma: "Es sin cargo, te lo paso?".
            pregunta = re.split(r"(?<=[.?])\s+", cuerpo.strip())[-1].split(",")[-1].strip().lower()
            self.assertNotRegex(pregunta, r"^(que|cuant|como|por que)\b")

    def test_estilo_felipe_sin_tildes_ni_apertura(self):
        self.assertEqual("Hola, que tal? Te mando el boceto, queres verlo? Año, niño.",
                         estilo_felipe("Hola, ¿qué tal? Te mando el boceto, ¿querés verlo? Año, niño."))
        for i in range(30):
            cuerpo = _cuerpo(_lead(_f("overflow_mobile"), id=f"ejemplo-{i}"))
            self.assertNotRegex(cuerpo, r"[¿¡áéíóúÁÉÍÓÚ]")

    def test_menos_de_75_palabras(self):
        for regla in ("carga_lenta", "sin_contacto", "sin_tel_movil", "overflow_mobile",
                      "sin_viewport", "popup_intrusivo", "sitio_inaccesible"):
            for i in range(10):
                with self.subTest(regla=regla, i=i):
                    cuerpo = _cuerpo(_lead(_f(regla), id=f"ejemplo-{i}"))
                    self.assertLess(len(cuerpo.split()), 75)
                    self.assertEqual(3, len(_bloques(cuerpo)), cuerpo)
                    self.assertIn("inmobiliarias", _bloques(cuerpo)[0])

    def test_guarda_regla_y_version(self):
        lead = _lead(_f("popup_intrusivo"))
        _redactar(lead)
        self.assertEqual("listo_whatsapp", lead.estado)
        self.assertEqual("plantilla-whatsapp-v5", lead.email_draft.generado_por)
        self.assertEqual("popup_intrusivo", lead.email_draft.regla)
        # Los JSON viejos no traen `regla` y tienen que seguir cargando.
        self.assertEqual("", EmailDraft.from_dict({"cuerpo": "hola"}).regla)


class TestCola(unittest.TestCase):
    def test_recompone_v4_y_no_toca_enviados(self):
        v4 = _lead(_f("carga_lenta"), id="ejemplo-v4", estado="listo_whatsapp")
        v4.email_draft = EmailDraft(cuerpo="texto v4", generado_por="claude-v4-whatsapp")
        enviado = _lead(_f("carga_lenta"), id="ejemplo-enviado", estado="enviado_whatsapp")
        enviado.email_draft = EmailDraft(cuerpo="lo que leyó", generado_por="claude-v4-whatsapp")
        respondido = _lead(_f("carga_lenta"), id="ejemplo-resp", estado="respondido")
        respondido.email_draft = EmailDraft(cuerpo="lo que leyó", generado_por="plantilla-whatsapp")

        _redactar(v4, enviado, respondido)

        self.assertEqual("plantilla-whatsapp-v5", v4.email_draft.generado_por)
        self.assertEqual("lo que leyó", enviado.email_draft.cuerpo)
        self.assertEqual("enviado_whatsapp", enviado.estado)
        self.assertEqual("lo que leyó", respondido.email_draft.cuerpo)
        self.assertEqual("respondido", respondido.estado)

    def test_recompone_v4_aunque_tenga_email(self):
        """Si ya está en `listo_whatsapp`, se lo pasó a este canal a propósito."""
        v4 = _lead(_f("carga_lenta"), id="ejemplo-v4-mail", estado="listo_whatsapp")
        v4.email = "hola@ejemplo.com.ar"
        v4.email_draft = EmailDraft(cuerpo="texto v4", generado_por="claude-v4-whatsapp")
        _redactar(v4)
        self.assertEqual("plantilla-whatsapp-v5", v4.email_draft.generado_por)

    def test_auditoria_vieja_no_se_redacta(self):
        """El mensaje afirma algo que el prospecto comprueba abriendo la web:
        un "no cargó" de hace tres semanas puede ser falso hoy."""
        nueva = _lead(_f("sitio_inaccesible"), id="ejemplo-nuevo", auditado_el=VIEJA)
        v4 = _lead(_f("carga_lenta"), id="ejemplo-v4", auditado_el=VIEJA, estado="listo_whatsapp")
        v4.email_draft = EmailDraft(cuerpo="texto v4", generado_por="claude-v4-whatsapp")

        _redactar(nueva, v4)

        for lead in (nueva, v4):
            with self.subTest(lead=lead.id):
                self.assertEqual("auditado", lead.estado)
                self.assertIsNone(lead.email_draft)
                self.assertEqual("auditoría de más de 14 días: re-auditar antes de redactar",
                                 lead.motivo_descarte)

    def test_auditoria_reciente_si_se_redacta(self):
        lead = _lead(_f("sitio_inaccesible"), auditado_el=RECIENTE)
        _redactar(lead)
        self.assertEqual("listo_whatsapp", lead.estado)
        self.assertNotIn("boceto", lead.email_draft.cuerpo)   # inaccesible no ofrece boceto


class TestValidarYLint(unittest.TestCase):
    def test_validar_rechaza_frases_prohibidas_toque1(self):
        base = "Hola, buenas. Soy Felipe, hago webs para inmobiliarias. " + "palabra " * 20
        for frase in ("sistema", "crm", "tokko", "seguramente", "por qué elegirte",
                      "por que elegirte", "en un mes normal", "cuántos pedidos",
                      "cuantos pedidos", "la misma foto", "el mismo buscador"):
            with self.subTest(frase=frase):
                borrador = EmailDraft(cuerpo=f"{base} {frase}. Te lo paso?")
                self.assertTrue(validar(borrador, canal="whatsapp",
                                        dominio_propio="ejemplo.com.ar"))

    def test_lint_oracion_mas_repetida(self):
        """La apertura sola no alcanza: con cinco cierres, el cierre era la
        oración más repetida del corpus (26 %) y el lint no lo veía."""
        cuerpos = [
            f"Hola, buenas. Soy Felipe.\n\nEntré a ejemplo{i}.com.ar y tardó. Te lo paso?"
            for i in range(4)
        ] + ["Hola, buenas. Soy Felipe.\n\nOtra cosa distinta. Te lo mando?"]
        frase, pct = lint._oracion_mas_repetida(cuerpos)
        self.assertEqual("Te lo paso?", frase)
        self.assertEqual(80.0, pct)
        # El saludo se saltea: si contara, "Hola, buenas." daría 100 %.

        leads = []
        for i, regla in enumerate(("carga_lenta", "carga_lenta", "sin_contacto")):
            lead = _lead(_f(regla), id=f"ejemplo-{i}")
            lead.estado = "listo_whatsapp"
            lead.email_draft = EmailDraft(cuerpo=cuerpos[i], generado_por="plantilla-whatsapp-v5",
                                          regla=regla)
            leads.append(lead)
        texto = lint.informe(leads)
        self.assertIn("oración más repetida", texto)
        self.assertRegex(texto, r"carga_lenta\D+2")


if __name__ == "__main__":
    unittest.main()
