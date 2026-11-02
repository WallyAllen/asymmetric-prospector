"""Contrato de la spec 010: mail v6 para inmobiliarias y variante de identidad en WhatsApp.

Todos los leads son ficticios (`ejemplo.com.ar`, `Inmobiliaria Ejemplo`): este
repo es público y `data/` no entra en un test.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.config import ComposeSettings  # noqa: E402
from prospector.models import Audit, EmailDraft, Finding, Lead, Metrics  # noqa: E402

HOY = date(2026, 10, 26)
RECIENTE = "2026-10-20T12:00:00+00:00"
VIEJA = "2026-09-30T12:00:00+00:00"
LINKEDIN = "https://www.linkedin.com/in/felipeborrazas/"
REGLAS = ("carga_lenta", "sin_contacto", "sin_tel_movil", "overflow_mobile",
          "sin_viewport", "popup_intrusivo", "sitio_inaccesible")


def _f(rule_id: str, categoria: str = "killer") -> Finding:
    return Finding(rule_id=rule_id, titulo=rule_id, severidad=8, peso=20,
                   evidencia="dato medido", observacion="Algo medido.",
                   consecuencia="El que los busca se va sin ponerse en contacto.",
                   categoria=categoria)


def _lead(*hallazgos: Finding, id: str = "ejemplo-1", nicho: str = "inmobiliarias zona norte",
          email: str | None = "hola@ejemplo.com.ar", estado: str = "listo",
          auditado_el: str = RECIENTE, rating: float | None = 4.9, resenas: int | None = 120) -> Lead:
    lead = Lead(id=id, nombre="Inmobiliaria Ejemplo", url="https://ejemplo.com.ar",
                email=email, telefono="1100000000", nicho=nicho, estado=estado,
                rating=rating, resenas=resenas)
    lead.audit = Audit(score=60, veredicto="critico", findings=list(hallazgos),
                       metrics=Metrics(lcp_ms=5300), auditado_el=auditado_el)
    return lead


def _compose(**cambios) -> ComposeSettings:
    base = dict(sender_name="Felipe Ejemplo Apellido", sender_role="Diseño y CRO · UNLP",
                sender_site=LINKEDIN, sender_phone="+54 9 11 0000 0000",
                sender_proof="", sender_pitch="armo páginas web")
    base.update(cambios)
    return ComposeSettings(**base)


class _Cfg:
    def __init__(self, **cambios) -> None:
        self.compose = _compose(**cambios)


def _bloques(cuerpo: str) -> list[str]:
    return [b for b in cuerpo.split("\n\n") if b.strip()]


def _mail(*leads: Lead) -> list[Lead]:
    from prospector.compose.mail_v6 import redactar_mail_v6
    return redactar_mail_v6(list(leads), _Cfg(), hoy=HOY)


class TestMailV6(unittest.TestCase):
    def test_redacta_listo_viejo_con_version_y_regla(self):
        lead = _lead(_f("carga_lenta"))
        lead.email_draft = EmailDraft(asunto="algo", cuerpo="Hola, INMOBILIARIA EJEMPLO,",
                                      generado_por="plantilla")
        _mail(lead)
        self.assertEqual("listo", lead.estado)
        self.assertEqual("plantilla-mail-v6", lead.email_draft.generado_por)
        self.assertEqual("carga_lenta", lead.email_draft.regla)
        self.assertEqual("formal", lead.email_draft.variante)
        self.assertIsNone(lead.email_draft.adjunto)

    def test_firma_completa_sin_unlp(self):
        """Lo que tenían los dos que pagaron: nombre, qué hace, LinkedIn y teléfono."""
        lead = _lead(_f("sin_contacto"))
        _mail(lead)
        firma = _bloques(lead.email_draft.cuerpo)[-1].splitlines()
        self.assertEqual(["Felipe Ejemplo Apellido", "Webs para inmobiliarias", LINKEDIN,
                          "+54 9 11 0000 0000"], firma)
        self.assertNotIn("UNLP", lead.email_draft.cuerpo)

    def test_estructura_y_saludo_sin_razon_social(self):
        for i in range(20):
            for regla in REGLAS:
                with self.subTest(regla=regla, i=i):
                    lead = _lead(_f(regla), id=f"ejemplo-{i}")
                    _mail(lead)
                    bloques = _bloques(lead.email_draft.cuerpo)
                    esperado = 4 if regla == "sitio_inaccesible" else 5   # + firma
                    self.assertEqual(esperado, len(bloques), lead.email_draft.cuerpo)
                    self.assertNotIn("Ejemplo,", bloques[0])
                    self.assertIn("Felipe", bloques[0])
                    self.assertNotIn("Apellido", bloques[0])  # el nombre completo va en la firma
                    self.assertIn("inmobiliarias", bloques[0])
                    self.assertIn("ejemplo.com.ar", bloques[1])

    def test_prueba_social_y_boceto_salvo_inaccesible(self):
        lead = _lead(_f("overflow_mobile"))
        _mail(lead)
        cuerpo = lead.email_draft.cuerpo
        self.assertIn("Zona Norte", cuerpo)
        self.assertIn("boceto", cuerpo)
        caida = _lead(_f("sitio_inaccesible"), id="ejemplo-caida")
        _mail(caida)
        self.assertNotIn("boceto", caida.email_draft.cuerpo)
        self.assertNotIn("Zona Norte", caida.email_draft.cuerpo)

    def test_reputacion_solo_si_es_establecida(self):
        alta = _lead(_f("carga_lenta"), id="ejemplo-alta", rating=4.9, resenas=120)
        baja = _lead(_f("carga_lenta"), id="ejemplo-baja", rating=4.1, resenas=120)
        poca = _lead(_f("carga_lenta"), id="ejemplo-poca", rating=4.9, resenas=12)
        _mail(alta, baja, poca)
        self.assertIn("4,9 con 120 reseñas", alta.email_draft.cuerpo)
        self.assertNotIn("reseñas", baja.email_draft.cuerpo)
        self.assertNotIn("reseñas", poca.email_draft.cuerpo)

    def test_estilo_felipe_y_validar(self):
        from prospector.compose.writer import validar
        for i in range(30):
            lead = _lead(_f(REGLAS[i % len(REGLAS)]), id=f"ejemplo-{i}")
            _mail(lead)
            with self.subTest(i=i):
                self.assertNotRegex(lead.email_draft.cuerpo + lead.email_draft.asunto,
                                    r"[¿¡áéíóúÁÉÍÓÚ]")
                self.assertEqual([], validar(lead.email_draft, canal="email",
                                             dominio_propio="ejemplo.com.ar"))
                self.assertNotRegex(lead.email_draft.cuerpo.lower(), r"sistema|crm|tokko")

    def test_puertas_de_la_009(self):
        vieja = _lead(_f("carga_lenta"), id="ejemplo-vieja", auditado_el=VIEJA)
        sin_falla = _lead(_f("sin_cta_fold"), id="ejemplo-sin-falla")
        error = _lead(_f("carga_lenta"), id="ejemplo-403")
        error.audit.metrics.http_status = 403
        _mail(vieja, sin_falla, error)
        self.assertEqual("auditado", vieja.estado)
        self.assertEqual("descartado", sin_falla.estado)
        self.assertEqual("sin falla verificable para toque 1", sin_falla.motivo_descarte)
        self.assertEqual("revisar_web", error.estado)
        for lead in (vieja, sin_falla, error):
            self.assertIsNone(lead.email_draft)

    def test_no_toca_enviados_ni_sin_email(self):
        # Los otros rubros dejaron de quedar afuera con la spec 011.
        enviado = _lead(_f("carga_lenta"), id="ejemplo-env", estado="enviado")
        enviado.email_draft = EmailDraft(asunto="x", cuerpo="lo que leyó", generado_por="plantilla")
        sin_mail = _lead(_f("carga_lenta"), id="ejemplo-sin-mail", email=None, estado="listo_whatsapp")
        _mail(enviado, sin_mail)
        self.assertEqual("lo que leyó", enviado.email_draft.cuerpo)
        self.assertEqual("listo_whatsapp", sin_mail.estado)

    def test_respeta_las_retenciones_a_mano(self):
        """Un `auditado` con borrador lo frenó Felipe a mano («No soy bot», afirmación
        de riesgo). La v6 no lo libera: 18 se habrían ido a la cola el 26/10."""
        retenido = _lead(_f("sin_tel_movil"), id="ejemplo-retenido", estado="auditado")
        retenido.email_draft = EmailDraft(asunto="x", cuerpo="borrador retenido", generado_por="ia")
        nuevo = _lead(_f("sin_tel_movil"), id="ejemplo-nuevo", estado="auditado")
        _mail(retenido, nuevo)
        self.assertEqual("auditado", retenido.estado)
        self.assertEqual("borrador retenido", retenido.email_draft.cuerpo)
        self.assertEqual("listo", nuevo.estado)
        self.assertEqual("plantilla-mail-v6", nuevo.email_draft.generado_por)

    def test_redactar_todos_no_pisa_la_v6(self):
        """Sin esto, `compose --forzar` volvía a la plantilla de septiembre."""
        from prospector.compose.writer import redactar_todos
        lead = _lead(_f("carga_lenta"))
        _mail(lead)
        cfg = _Cfg()
        cfg.compose.use_ai = False
        cfg.ai = mock.Mock(enabled=False)
        redactar_todos([lead], cfg, forzar=True)
        self.assertEqual("plantilla-mail-v6", lead.email_draft.generado_por)


class TestWhatsAppV6(unittest.TestCase):
    def _wa(self, lead: Lead, **cambios) -> EmailDraft:
        from prospector.compose.whatsapp import componer_whatsapp
        return componer_whatsapp(lead, _compose(**cambios))

    def _wa_lead(self, i: int, regla: str = "carga_lenta", **kw) -> Lead:
        return _lead(_f(regla), id=f"ejemplo-{i}", email=None, estado="auditado", **kw)

    def test_version_y_reparto_de_variantes(self):
        variantes = [self._wa(self._wa_lead(i)).variante for i in range(200)]
        self.assertEqual({"corta", "identidad"}, set(variantes))
        self.assertTrue(70 <= variantes.count("identidad") <= 130, variantes.count("identidad"))
        self.assertEqual("plantilla-whatsapp-v6", self._wa(self._wa_lead(0)).generado_por)

    def test_identidad_lleva_linkedin_corto_en_el_primer_bloque(self):
        from prospector.compose.writer import validar
        vistos = 0
        for i in range(60):
            for regla in REGLAS:
                borrador = self._wa(self._wa_lead(i, regla))
                bloques = _bloques(borrador.cuerpo)
                with self.subTest(i=i, regla=regla):
                    self.assertEqual(3, len(bloques))
                    self.assertLessEqual(len(borrador.cuerpo.split()), 95)
                    if borrador.variante == "identidad":
                        vistos += 1
                        self.assertIn("linkedin.com/in/felipeborrazas", bloques[0])
                        self.assertNotIn("https://", borrador.cuerpo)
                        self.assertNotIn("www.", borrador.cuerpo)
                        self.assertEqual([], validar(borrador, canal="whatsapp",
                                                     dominio_propio="ejemplo.com.ar",
                                                     enlace_propio="linkedin.com/in/felipeborrazas"))
                    else:
                        self.assertNotIn("linkedin", borrador.cuerpo.lower())
        self.assertGreater(vistos, 0)

    def test_sin_sender_site_o_sin_web_es_corta(self):
        self.assertEqual("corta", self._wa(self._wa_lead(1), sender_site="").variante)
        sin_web = self._wa_lead(2)
        sin_web.url = None
        self.assertEqual("corta", self._wa(sin_web).variante)
        vete = self._wa_lead(3, nicho="veterinarias la plata")
        self.assertEqual("corta", self._wa(vete).variante)

    def test_validar_sigue_rechazando_otros_enlaces(self):
        from prospector.compose.writer import validar
        base = "Hola, buenas. Soy Felipe, hago webs para inmobiliarias. " + "palabra " * 20
        otro = EmailDraft(cuerpo=f"{base} mirá otrositio.com.ar. Te lo paso?")
        self.assertTrue(validar(otro, canal="whatsapp", dominio_propio="ejemplo.com.ar",
                                enlace_propio="linkedin.com/in/felipeborrazas"))
        propio = EmailDraft(cuerpo=f"{base} linkedin.com/in/felipeborrazas. Te lo paso?")
        self.assertFalse(validar(propio, canal="whatsapp", dominio_propio="ejemplo.com.ar",
                                 enlace_propio="linkedin.com/in/felipeborrazas"))
        self.assertTrue(validar(propio, canal="whatsapp", dominio_propio="ejemplo.com.ar"))


class TestMedicion(unittest.TestCase):
    def test_variante_carga_de_json_viejo(self):
        self.assertEqual("", EmailDraft.from_dict({"cuerpo": "hola"}).variante)

    def test_traza_borrador(self):
        from prospector.deliver import traza_borrador
        lead = _lead(_f("carga_lenta"))
        lead.email_draft = EmailDraft(cuerpo="x", generado_por="plantilla-whatsapp-v6",
                                      regla="carga_lenta", variante="identidad")
        self.assertEqual({"generado_por": "plantilla-whatsapp-v6", "variante": "identidad",
                          "regla": "carga_lenta"}, traza_borrador(lead))
        lead.email_draft = None
        self.assertEqual({"generado_por": None, "variante": None, "regla": None},
                         traza_borrador(lead))

    def test_registro_whatsapp_guarda_la_traza(self):
        from prospector.deliver import whatsapp as entrega
        lead = _lead(_f("carga_lenta"), email=None, estado="listo_whatsapp")
        lead.email_draft = EmailDraft(cuerpo="x", generado_por="plantilla-whatsapp-v6",
                                      regla="carga_lenta", variante="corta")
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "registro_whatsapp.json"
            with mock.patch.object(entrega, "WHATSAPP_SENT_FILE", archivo):
                entrega.registrar_envio(lead)
            fila = json.loads(archivo.read_text(encoding="utf-8"))[0]
        self.assertEqual("corta", fila["variante"])
        self.assertEqual("plantilla-whatsapp-v6", fila["generado_por"])
        self.assertEqual("carga_lenta", fila["regla"])

    def test_mailer_guarda_la_traza(self):
        """El registro del mail se arma en `enviar`; se comprueba que usa la traza."""
        fuente = (Path(__file__).resolve().parent.parent / "prospector" / "deliver" / "mailer.py")
        self.assertRegex(fuente.read_text(encoding="utf-8"), r"traza_borrador\(lead\)")

    def test_lint_mail_saltea_la_firma(self):
        from prospector import lint
        firma = "Felipe Ejemplo Apellido\nWebs para inmobiliarias"
        cuerpos = [f"Hola, que tal?\n\nAbri ejemplo{i}.com.ar y tardo. Frase {i}.\n\n{firma}"
                   for i in range(5)]
        frase, _ = lint._oracion_mas_repetida(cuerpos, saltear_firma=True)
        self.assertNotIn("Webs para inmobiliarias", frase)


if __name__ == "__main__":
    unittest.main()
