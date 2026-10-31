"""Contrato de la spec 012: qué sistema usa la web del prospecto, y el mail según eso.

Todos los leads y URLs son ficticios (`ejemplo.com.ar`): este repo es público y
`data/` no entra en un test. Los helpers son los de la 010.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.models import EmailDraft, Metrics  # noqa: E402
from tests.test_plantilla_v6 import REGLAS, _bloques, _f, _lead, _mail  # noqa: E402

VETE = "veterinarias la plata"
TOKKO = ["https://static.tokkobroker.com/pictures/123.jpg", "https://ejemplo.com.ar/"]
WASI = ["https://images.wasi.co/inmuebles/b1.jpg"]
WORDPRESS = ["https://ejemplo.com.ar/wp-content/themes/x/style.css"]
NADA = ["https://ejemplo.com.ar/css/app.css", "https://www.googletagmanager.com/gtm.js"]


def _con_sistema(sistema: str | None, regla: str = "carga_lenta", **kw):
    lead = _lead(_f(regla), **kw)
    lead.audit.metrics.sistema_web = sistema
    return lead


class TestDeteccion(unittest.TestCase):
    def test_crm_inmobiliario_por_dominio(self):
        from prospector.audit.sistema import detectar_sistema
        self.assertEqual("tokko", detectar_sistema(None, TOKKO))
        self.assertEqual("wasi", detectar_sistema(None, WASI))

    def test_constructor_por_ruta_o_generator(self):
        from prospector.audit.sistema import detectar_sistema
        self.assertEqual("wordpress", detectar_sistema(None, WORDPRESS))
        self.assertEqual("wordpress", detectar_sistema("WordPress 6.4.2", NADA))
        self.assertEqual("wix", detectar_sistema("Wix.com Website Builder", []))
        self.assertEqual("wix", detectar_sistema(None, ["https://static.wixstatic.com/media/a.jpg"]))

    def test_el_crm_gana_al_constructor(self):
        """Un WordPress que muestra las propiedades de Tokko carga en Tokko: eso es lo
        que decide el mensaje, no el tema de WordPress."""
        from prospector.audit.sistema import detectar_sistema
        self.assertEqual("tokko", detectar_sistema("WordPress 6.4", WORDPRESS + TOKKO))

    def test_sin_firma_es_sin_detectar(self):
        """Medido y sin firma conocida: puede no usar nada o usar algo que no
        reconocemos. Desde afuera es lo mismo, y no se afirma ninguna de las dos."""
        from prospector.audit.sistema import detectar_sistema
        self.assertEqual("sin_detectar", detectar_sistema(None, NADA))
        self.assertEqual("sin_detectar", detectar_sistema("", []))

    def test_no_confunde_una_palabra_en_la_ruta(self):
        """Una nota del blog que habla de Tokko o de Wix no es una firma."""
        from prospector.audit.sistema import detectar_sistema
        self.assertEqual("sin_detectar", detectar_sistema(None, [
            "https://ejemplo.com.ar/blog/tokkobroker-com-vs-wasi-co",
            "https://ejemplo.com.ar/notas/wix-o-wordpress",
            "https://tokkobroker.com.ejemplo.com.ar/x.js",
        ]))

    def test_mayusculas_y_subdominios(self):
        from prospector.audit.sistema import detectar_sistema
        self.assertEqual("tokko", detectar_sistema(None, ["HTTPS://WWW.TokkoBroker.com/x"]))
        self.assertEqual("tokko", detectar_sistema(None, ["https://tokkobroker.com/x"]))

    def test_perfil(self):
        from prospector.audit.sistema import perfil_sistema
        self.assertEqual("crm", perfil_sistema("tokko"))
        self.assertEqual("crm", perfil_sistema("wasi"))
        for otro in ("wordpress", "wix", "sin_detectar", None, ""):
            with self.subTest(sistema=otro):
                self.assertEqual("desconocido", perfil_sistema(otro))

    def test_consolidar_guarda_el_sistema(self):
        from prospector.audit.signals import ProbeResult, _consolidar
        res = ProbeResult(desktop={"generador": None, "recursos": TOKKO})
        _consolidar(res)
        self.assertEqual("tokko", res.metrics.sistema_web)

    def test_sin_recursos_es_no_medido(self):
        """Un JS viejo o una medición sin la lista: None, no "sin_detectar"."""
        from prospector.audit.signals import ProbeResult, _consolidar
        res = ProbeResult(desktop={"generador": "WordPress 6.4"})
        _consolidar(res)
        self.assertIsNone(res.metrics.sistema_web)

    def test_json_viejo_carga(self):
        self.assertIsNone(Metrics.from_dict({"lcp_ms": 5300}).sistema_web)
        self.assertEqual("", EmailDraft.from_dict({"asunto": "x"}).sistema)


class TestMailSegunSistema(unittest.TestCase):
    def _linea(self, lead):
        from prospector.compose.lexicon import PROPIEDADES_MAIL_V6
        from prospector.compose.whatsapp import estilo_felipe
        cuerpo = lead.email_draft.cuerpo
        for perfil, opciones in PROPIEDADES_MAIL_V6.items():
            for opcion in opciones:
                for nombre in ("Tokko", "Wasi"):
                    texto = estilo_felipe(opcion.format(sistema=nombre))
                    if texto in cuerpo:
                        return perfil, texto
        return None, None

    def test_crm_nombra_el_suyo(self):
        """Galan siguió la charla cuando quedó claro que la web lee lo que ya cargan;
        Juliano cortó cuando sonó a otra cosa más para administrar."""
        for sistema, nombre in (("tokko", "Tokko"), ("wasi", "Wasi")):
            with self.subTest(sistema=sistema):
                lead = _con_sistema(sistema)
                _mail(lead)
                perfil, _ = self._linea(lead)
                self.assertEqual("crm", perfil)
                self.assertIn(nombre, lead.email_draft.cuerpo)
                self.assertEqual(sistema, lead.email_draft.sistema)

    def test_desconocido_no_afirma_nada(self):
        """Sin CRM detectado no se sabe si no usa nada o usa uno que no reconocemos:
        la frase tiene que ser cierta en los dos casos y no nombrar ningún producto."""
        for sistema, traza in (("sin_detectar", "sin_detectar"), (None, "no_medido"),
                               ("wordpress", "wordpress"), ("wix", "wix")):
            with self.subTest(sistema=sistema):
                lead = _con_sistema(sistema)
                _mail(lead)
                perfil, _ = self._linea(lead)
                self.assertEqual("desconocido", perfil)
                cuerpo = lead.email_draft.cuerpo.lower()
                for producto in ("tokko", "wasi", "wordpress", "wix"):
                    self.assertNotIn(producto, cuerpo)
                self.assertEqual(traza, lead.email_draft.sistema)

    def test_va_al_frente_del_bloque_de_la_oferta(self):
        for sistema in ("tokko", None):
            lead = _con_sistema(sistema, regla="overflow_mobile")
            _mail(lead)
            bloques = _bloques(lead.email_draft.cuerpo)
            self.assertEqual(5, len(bloques))          # la estructura de la 010 no cambia
            _, texto = self._linea(lead)
            self.assertTrue(bloques[3].startswith(texto), bloques[3])
            self.assertIn("boceto", bloques[3])

    def test_nunca_sistema_ni_crm_y_entra_en_el_tope(self):
        """"Sistema" y "CRM" abren la salida del "ya tenemos" (009). Con la línea
        nueva el peor mail sigue bajo las 150 palabras."""
        from prospector.compose.writer import validar
        for i in range(60):
            for regla in REGLAS:
                for sistema in ("tokko", "wasi", "sin_detectar", None):
                    lead = _con_sistema(sistema, regla=regla, id=f"ejemplo-{i}")
                    _mail(lead)
                    with self.subTest(i=i, regla=regla, sistema=sistema):
                        cuerpo = lead.email_draft.cuerpo.lower()
                        self.assertNotRegex(cuerpo, r"\b(sistema|crm)\b")
                        self.assertNotIn("compromiso", cuerpo)
                        self.assertEqual([], validar(lead.email_draft, canal="email",
                                                     dominio_propio="ejemplo.com.ar"))

    def test_inaccesible_no_lleva_la_linea(self):
        lead = _con_sistema("tokko", regla="sitio_inaccesible")
        _mail(lead)
        self.assertEqual((None, None), self._linea(lead))
        self.assertNotIn("Tokko", lead.email_draft.cuerpo)
        self.assertEqual("", lead.email_draft.sistema)

    def test_otros_rubros_no_la_llevan(self):
        """Depende de la 011: una veterinaria con mail v6 no carga propiedades."""
        lead = _con_sistema("tokko", nicho=VETE)
        _mail(lead)
        self.assertEqual((None, None), self._linea(lead))
        self.assertEqual("", lead.email_draft.sistema)

    def test_variedad(self):
        """Dos opciones por perfil, repartidas por lead como el resto del léxico."""
        vistas = {"crm": set(), "desconocido": set()}
        for i in range(40):
            for sistema in ("tokko", None):
                lead = _con_sistema(sistema, id=f"ejemplo-{i}")
                _mail(lead)
                perfil, texto = self._linea(lead)
                vistas[perfil].add(texto)
        self.assertGreaterEqual(len(vistas["crm"]), 2)
        self.assertGreaterEqual(len(vistas["desconocido"]), 2)


if __name__ == "__main__":
    unittest.main()
