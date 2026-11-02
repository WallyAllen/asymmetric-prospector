"""Contrato de la spec 011: el mail v6 para todos los rubros con web.

Todos los leads son ficticios (`ejemplo.com.ar`, `Negocio Ejemplo`): este repo
es público y `data/` no entra en un test. Los helpers son los de la 010.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.models import EmailDraft  # noqa: E402
from tests.test_plantilla_v6 import (LINKEDIN, REGLAS, _bloques, _Cfg, _f,  # noqa: E402
                                     _lead, _mail)

VETE = "veterinarias la plata"
GENERICO = "cerrajerias ejemplo"     # nicho que `rubro_de` no reconoce


class TestMailV6Rubros(unittest.TestCase):
    def test_redacta_otros_rubros_con_web(self):
        """El 27/10 quedaban 43 mails en `listo` fuera de inmobiliarias, todos con el
        borrador de septiembre: firma con `· UNLP`, razón social de Maps en el asunto."""
        lead = _lead(_f("carga_lenta"), nicho=VETE)
        lead.email_draft = EmailDraft(asunto="una pregunta sobre VETE | Ejemplo",
                                      cuerpo="Hola, VETE EJEMPLO,", generado_por="plantilla")
        _mail(lead)
        self.assertEqual("listo", lead.estado)
        self.assertEqual("plantilla-mail-v6", lead.email_draft.generado_por)
        self.assertEqual("carga_lenta", lead.email_draft.regla)
        self.assertEqual("formal", lead.email_draft.variante)
        self.assertIsNone(lead.email_draft.adjunto)

    def test_presentacion_y_firma_nombran_su_rubro(self):
        lead = _lead(_f("sin_contacto"), nicho=VETE)
        _mail(lead)
        cuerpo = lead.email_draft.cuerpo
        self.assertIn("webs para veterinarias", _bloques(cuerpo)[0])
        self.assertEqual(["Felipe Ejemplo Apellido", "Webs para veterinarias", LINKEDIN,
                          "+54 9 11 0000 0000"], _bloques(cuerpo)[-1].splitlines())
        self.assertNotIn("inmobiliaria", (cuerpo + lead.email_draft.asunto).lower())
        self.assertNotIn("UNLP", cuerpo)

    def test_rubro_generico_dice_paginas_web(self):
        """`GENERICO.plural` es "servicios de la zona": sirve para una búsqueda,
        no para decir qué hacés ("hago webs para servicios de la zona")."""
        lead = _lead(_f("carga_lenta"), nicho=GENERICO)
        _mail(lead)
        cuerpo = lead.email_draft.cuerpo
        self.assertNotIn("servicios de la zona", cuerpo)
        self.assertIn("paginas web", _bloques(cuerpo)[0])
        self.assertEqual("Paginas web", _bloques(cuerpo)[-1].splitlines()[1])

    def test_sin_la_prueba_social_de_inmobiliarias(self):
        """La web en curso es de una inmobiliaria: contársela a una veterinaria no
        prueba nada y suena a plantilla. Fuera de inmobiliarias, sin bloque 3."""
        for i in range(20):
            for regla in REGLAS:
                with self.subTest(regla=regla, i=i):
                    lead = _lead(_f(regla), id=f"ejemplo-{i}", nicho=VETE)
                    _mail(lead)
                    bloques = _bloques(lead.email_draft.cuerpo)
                    self.assertEqual(4, len(bloques), lead.email_draft.cuerpo)   # + firma
                    self.assertNotIn("Zona Norte", lead.email_draft.cuerpo)
                    self.assertIn("Felipe", bloques[0])
                    self.assertNotIn("Apellido", bloques[0])
                    self.assertIn("ejemplo.com.ar", bloques[1])

    def test_el_hallazgo_es_el_medido(self):
        lead = _lead(_f("sin_contacto"), nicho=VETE)
        _mail(lead)
        hallazgo = _bloques(lead.email_draft.cuerpo)[1].lower()
        self.assertIn("algo medido", hallazgo)
        self.assertIn("se va sin ponerse en contacto", hallazgo)

    def test_inaccesible_no_ofrece_boceto(self):
        lead = _lead(_f("sitio_inaccesible"), nicho=VETE)
        _mail(lead)
        cuerpo = lead.email_draft.cuerpo
        self.assertNotIn("boceto", cuerpo)
        self.assertIn("que error me aparecio", _bloques(cuerpo)[2])

    def test_estilo_felipe_y_validar_en_todos_los_rubros(self):
        from prospector.compose.writer import validar
        for i in range(30):
            for nicho in (VETE, GENERICO, "estudios juridicos la plata"):
                lead = _lead(_f(REGLAS[i % len(REGLAS)]), id=f"ejemplo-{i}", nicho=nicho)
                _mail(lead)
                with self.subTest(i=i, nicho=nicho):
                    self.assertNotRegex(lead.email_draft.cuerpo + lead.email_draft.asunto,
                                        r"[¿¡áéíóúÁÉÍÓÚ]")
                    self.assertEqual([], validar(lead.email_draft, canal="email",
                                                 dominio_propio="ejemplo.com.ar"))

    def test_cierre_sin_sin_compromiso(self):
        """"Sin compromiso" se defiende de una objeción que nadie hizo todavía."""
        for i in range(60):
            for nicho in (VETE, "inmobiliarias zona norte"):
                lead = _lead(_f("carga_lenta"), id=f"ejemplo-{i}", nicho=nicho)
                _mail(lead)
                with self.subTest(i=i, nicho=nicho):
                    self.assertNotIn("compromiso", lead.email_draft.cuerpo.lower())

    def test_no_toca_enviados_ni_retenidos_de_otros_rubros(self):
        enviado = _lead(_f("carga_lenta"), id="ejemplo-env", nicho=VETE, estado="enviado")
        enviado.email_draft = EmailDraft(asunto="x", cuerpo="lo que leyó", generado_por="plantilla")
        retenido = _lead(_f("carga_lenta"), id="ejemplo-ret", nicho=VETE, estado="auditado")
        retenido.email_draft = EmailDraft(asunto="x", cuerpo="retenido", generado_por="ia")
        _mail(enviado, retenido)
        self.assertEqual("lo que leyó", enviado.email_draft.cuerpo)
        self.assertEqual("auditado", retenido.estado)
        self.assertEqual("retenido", retenido.email_draft.cuerpo)

    def test_compose_forzado_no_vuelve_a_la_plantilla_de_septiembre(self):
        """Con `redactar_todos` en la etapa, `compose --forzar` pisaba la v6 de
        cualquier rubro con la plantilla o la IA de septiembre."""
        from prospector import pipeline
        leads = [_lead(_f("carga_lenta"), id="ejemplo-vete", nicho=VETE),
                 _lead(_f("sin_contacto"), id="ejemplo-gen", nicho=GENERICO),
                 _lead(_f("overflow_mobile"), id="ejemplo-inmo")]
        cfg = _Cfg()
        cfg.compose.use_ai = False
        cfg.ai = mock.Mock(enabled=False)
        cfg.audit = mock.Mock(min_score=0)
        with mock.patch.object(pipeline, "ensure_dirs"), \
                mock.patch.object(pipeline, "load_leads", side_effect=[leads, []]), \
                mock.patch.object(pipeline, "merge_leads", side_effect=lambda a, b: a), \
                mock.patch.object(pipeline, "save_leads"), \
                mock.patch.object(pipeline, "exportar_preview"), \
                mock.patch.object(pipeline, "exportar_whatsapp"):
            pipeline.redactar_correos(cfg, forzar=True)
        for lead in leads:
            with self.subTest(lead=lead.id):
                self.assertEqual("plantilla-mail-v6", lead.email_draft.generado_por)


if __name__ == "__main__":
    unittest.main()
