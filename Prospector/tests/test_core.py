"""Pruebas de humo del núcleo: no necesitan navegador, red ni claves de IA."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.audit import rules  # noqa: E402
from prospector.audit.signals import ProbeResult  # noqa: E402
from prospector.compose.writer import FRASES_PROHIBIDAS, componer_por_plantilla, limpiar  # noqa: E402
from prospector.config import ComposeSettings  # noqa: E402
from prospector.models import Audit, Lead, Metrics  # noqa: E402
from prospector.utils import (clean_emails, is_directory, lead_id, normalize_url,  # noqa: E402
                              registrable_domain)


class TestUtils(unittest.TestCase):
    def test_normalizacion(self):
        self.assertEqual(normalize_url("WWW.Ejemplo.com/inicio/?utm=x"), "https://ejemplo.com/inicio")
        self.assertEqual(normalize_url("ejemplo.com"), "https://ejemplo.com/")
        self.assertIsNone(normalize_url(""))

    def test_dominio_registrable(self):
        self.assertEqual(registrable_domain("https://blog.tienda.co.uk/x"), "tienda.co.uk")
        self.assertEqual(registrable_domain("https://www.clinica.es"), "clinica.es")

    def test_directorios_descartados(self):
        self.assertTrue(is_directory("https://www.cylex.es/valencia/abogado.html"))
        self.assertTrue(is_directory("https://lawzana.com/es/x"))
        self.assertFalse(is_directory("https://casesdedret.com/"))

    def test_limpieza_de_emails(self):
        crudos = ["INFO@Clinica.es", "logo@2x.png", "noreply@clinica.es", "juan@clinica.es"]
        limpios = clean_emails(crudos)
        self.assertEqual(limpios[0], "info@clinica.es")
        self.assertNotIn("logo@2x.png", limpios)
        self.assertNotIn("noreply@clinica.es", limpios)

    def test_id_estable(self):
        self.assertEqual(lead_id("https://www.clinica.es/x"), "clinica.es")
        sin_web = lead_id(None, "Clínica Sol", "a@b.com")
        self.assertTrue(sin_web.startswith("noweb-"))
        self.assertEqual(sin_web, lead_id(None, "Clínica Sol", "a@b.com"))


def _res(**metricas) -> ProbeResult:
    metricas.setdefault("https", True)
    res = ProbeResult(ok=True, metrics=Metrics(http_status=200, **metricas))
    res.desktop = {"rects": {"fold": {"x": 0, "y": 0, "width": 1440, "height": 900}}}
    return res


class TestReglas(unittest.TestCase):
    def test_web_sana_no_pasa_el_umbral(self):
        res = _res(
            tiene_viewport_meta=True, ctas_en_fold=3, tiene_formulario=True, tiene_tel=True,
            lcp_ms=1400, cls=0.02, peso_kb=900, favicon=True, og_image=True, h1=1,
            title="Clínica dental en Valencia | Sonrisa", meta_description="Implantes y ortodoncia",
            items_menu=5, palabras_en_fold=45, ano_copyright=2026,
            overflow_horizontal_mobile=False, texto_pequeno_mobile=0, tap_targets_pequenos=1,
        )
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertEqual(score, 0)  # ningún hallazgo: web sana de verdad
        self.assertEqual(veredicto, "sano")
        self.assertFalse(hallazgos)

    def test_landing_funcional_con_detalles_menores_no_es_critica(self):
        """El caso real que motivó este test: una landing con CTA, formulario y
        buen copy, pero un par de detalles de pulido (sin HTTPS, sin favicon,
        teléfono no pulsable) NO puede salir 'crítica'. Es una web que
        convierte; el score tiene que reflejar eso, no acumular puntos por
        cosas que no le cuestan un solo cliente al negocio."""
        res = _res(
            tiene_viewport_meta=True, ctas_en_fold=2, tiene_formulario=True, tiene_tel=False,
            tiene_whatsapp=False, https=False, lcp_ms=1800, cls=0.05, peso_kb=1200,
            favicon=False, og_image=True, h1=1,
            title="Abogados Cases de Dret · Mercantil Barcelona",
            meta_description="Despacho de derecho mercantil en Barcelona.",
            items_menu=4, palabras_en_fold=40, ano_copyright=2025,
            overflow_horizontal_mobile=False, texto_pequeno_mobile=0, tap_targets_pequenos=0,
        )
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertLess(score, 28, f"score {score} demasiado alto para una landing funcional")
        self.assertEqual(veredicto, "sano")
        self.assertFalse(any(h.categoria == "killer" for h in hallazgos))

    def test_web_horrible_puntua_alto(self):
        res = _res(
            tiene_viewport_meta=False, ctas_en_fold=0, tiene_formulario=False, tiene_tel=False,
            tiene_whatsapp=False, lcp_ms=6400, cls=0.42, peso_kb=5200, favicon=False,
            og_image=False, h1=0, title=None, meta_description=None, items_menu=14,
            palabras_en_fold=4, ano_copyright=2014, overflow_horizontal_mobile=True,
            ancho_scroll_mobile=1100, texto_pequeno_mobile=40, tap_targets_pequenos=20,
            popup_intrusivo=True,
        )
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertEqual(score, 100)
        self.assertEqual(veredicto, "critico")
        killers = [h for h in hallazgos if h.categoria == "killer"]
        self.assertGreaterEqual(len(killers), 2, "hacen falta al menos 2 killers para ser crítico")
        ids = {h.rule_id for h in hallazgos}
        for esperado in ("sin_viewport", "sin_cta_fold", "carga_lenta", "copyright_viejo"):
            self.assertIn(esperado, ids)

    def test_pila_de_hallazgos_cosmeticos_no_cruza_a_mejorable(self):
        """Favicon + SEO + menú largo + imágenes sin optimizar, todo junto,
        con el resto de la web sana: sigue siendo 'sano'. Ningún negocio
        recibe un correo solo por no tener favicon."""
        res = _res(
            tiene_viewport_meta=True, ctas_en_fold=2, tiene_formulario=True, tiene_tel=True,
            lcp_ms=1200, cls=0.01, peso_kb=800, favicon=False, og_image=False, h1=0,
            title="Web", meta_description=None, items_menu=12, palabras_en_fold=40,
            ano_copyright=2026, overflow_horizontal_mobile=False, texto_pequeno_mobile=0,
            tap_targets_pequenos=0,
        )
        res.desktop["imagenesSobredimensionadas"] = 5
        res.desktop["imagenes"] = 10
        res.desktop["imagenesSinAlt"] = 8
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertTrue(all(h.categoria == "cosmetico" for h in hallazgos))
        self.assertEqual(veredicto, "sano")

    def test_sitio_caido_es_inaccesible(self):
        res = ProbeResult(ok=False, error="Timeout", metrics=Metrics(error="Timeout"))
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertEqual(veredicto, "inaccesible")
        self.assertGreaterEqual(score, 90)
        self.assertTrue(any(h.rule_id == "sitio_inaccesible" for h in hallazgos))

    def test_sin_web_es_maxima_oportunidad(self):
        hallazgo = rules.finding_sin_web("Clínica Sol")
        self.assertEqual(hallazgo.peso, 100)
        self.assertEqual(hallazgo.categoria, "killer")
        self.assertIn("Clínica Sol", hallazgo.argumento)


class TestRedaccion(unittest.TestCase):
    def setUp(self):
        # Aislado de .env a propósito: los tests no pueden depender de la
        # config personal de quien los corre (p. ej. SENDER_PROOF real).
        self.cfg = ComposeSettings(sender_name="Felipe", sender_role="CRO",
                                    sender_site="", sender_proof="", max_findings_in_email=2)

    def _lead_auditado(self) -> Lead:
        res = _res(tiene_viewport_meta=False, ctas_en_fold=0, lcp_ms=5200)
        score, veredicto, hallazgos = rules.evaluar(res)
        lead = Lead(nombre="Clínica Sol", url="https://clinicasol.es", email="info@clinicasol.es",
                    nicho="clínicas dentales valencia")
        lead.audit = Audit(score=score, veredicto=veredicto, findings=hallazgos)
        return lead

    def test_plantilla_sin_marcadores_ni_slop(self):
        borrador = componer_por_plantilla(self._lead_auditado(), self.cfg)
        self.assertTrue(borrador.asunto)
        self.assertNotIn("[", borrador.cuerpo)
        self.assertNotIn("{", borrador.cuerpo)
        minuscula = borrador.cuerpo.lower()
        for frase in FRASES_PROHIBIDAS:
            self.assertNotIn(frase, minuscula)
        self.assertLess(len(borrador.cuerpo.split()), 170)

    def test_lead_sin_web_tiene_su_propio_angulo(self):
        lead = Lead(nombre="Bar Pepe", email="bar@pepe.es", nicho="bares madrid")
        lead.audit = Audit(score=100, veredicto="sin_web", findings=[rules.finding_sin_web("Bar Pepe")])
        borrador = componer_por_plantilla(lead, self.cfg)
        self.assertIn("Maps", borrador.cuerpo)

    def test_filtro_antislop(self):
        sucio = "Hola. Espero que este correo te encuentre bien. En el mundo actual, **todo** cambia."
        limpio = limpiar(sucio)
        self.assertNotIn("encuentre bien", limpio)
        self.assertNotIn("mundo actual", limpio)
        self.assertNotIn("**", limpio)


class TestModelos(unittest.TestCase):
    def test_ida_y_vuelta_json(self):
        lead = Lead(nombre="X", url="https://x.es", email="a@x.es")
        lead.audit = Audit(score=80, veredicto="critico",
                           findings=[rules.finding_sin_web("X")], metrics=Metrics(lcp_ms=3000))
        copia = Lead.from_dict(lead.to_dict())
        self.assertEqual(copia.id, lead.id)
        self.assertEqual(copia.audit.score, 80)
        self.assertEqual(copia.audit.findings[0].rule_id, "sin_web")
        self.assertEqual(copia.audit.metrics.lcp_ms, 3000)

    def test_fusion_conserva_trabajo_previo(self):
        from prospector.storage import merge_leads

        viejo = Lead(nombre="X", url="https://x.es", email="a@x.es")
        viejo.audit = Audit(score=90, veredicto="critico")
        viejo.estado = "auditado"
        nuevo = Lead(nombre="X", url="https://x.es", telefono="+34600000000")
        fusion = merge_leads([viejo], [nuevo])
        self.assertEqual(len(fusion), 1)
        self.assertEqual(fusion[0].audit.score, 90)
        self.assertEqual(fusion[0].telefono, "+34600000000")

    def test_fusion_no_pisa_auditoria_con_un_lado_vacio(self):
        """Reproduce el bug real: un archivo 'más adelante' en el embudo pero
        guardado con datos viejos no debe borrar la auditoría del otro lado,
        sea cual sea el orden en que se pasen existing/nuevos."""
        from prospector.storage import merge_leads

        compuesto_viejo = Lead(nombre="X", url="https://x.es", email="a@x.es")  # estado=crudo, sin audit
        auditado = Lead(nombre="X", url="https://x.es", email="a@x.es")
        auditado.audit = Audit(score=90, veredicto="critico")
        auditado.estado = "auditado"

        fusion = merge_leads([compuesto_viejo], [auditado])
        self.assertIsNotNone(fusion[0].audit)
        self.assertEqual(fusion[0].estado, "auditado")


if __name__ == "__main__":
    unittest.main(verbosity=2)
