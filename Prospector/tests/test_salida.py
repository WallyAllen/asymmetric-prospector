"""Pruebas de los artefactos finales: captura anotada, correo MIME e informe."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.audit import rules  # noqa: E402
from prospector.audit.capture import anotar  # noqa: E402
from prospector.audit.signals import ProbeResult  # noqa: E402
from prospector.config import MailSettings  # noqa: E402
from prospector.deliver.mailer import construir_mensaje  # noqa: E402
from prospector.models import Audit, EmailDraft, Lead, Metrics  # noqa: E402


def _captura_falsa(destino: Path) -> Path:
    from PIL import Image, ImageDraw

    imagen = Image.new("RGB", (1440, 900), (245, 245, 248))
    draw = ImageDraw.Draw(imagen)
    draw.rectangle([0, 0, 1440, 90], fill=(30, 40, 60))
    draw.rectangle([80, 220, 900, 520], fill=(220, 220, 226))
    imagen.save(destino)
    return destino


class TestSalidas(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _hallazgos(self):
        res = ProbeResult(ok=True, metrics=Metrics(http_status=200, https=True,
                                                   ctas_en_fold=0, lcp_ms=5200,
                                                   tiene_viewport_meta=False))
        res.desktop = {"rects": {"fold": {"x": 0, "y": 0, "width": 1440, "height": 900},
                                 "hero": {"x": 80, "y": 220, "width": 820, "height": 300}}}
        return rules.evaluar(res)

    def test_anotacion_recorta_y_amplia_la_zona(self):
        """La captura ya no debe ser la pantalla entera con una marca perdida:
        tiene que recortar y ampliar alrededor de la zona del problema."""
        origen = _captura_falsa(self.tmp / "fold.png")
        _, _, hallazgos = self._hallazgos()
        destino = anotar(origen, self.tmp / "anotada.png", hallazgos, pie="Sin llamada a la acción")
        self.assertIsNotNone(destino)
        self.assertTrue(destino.exists())

        from PIL import Image

        antes, despues = Image.open(origen), Image.open(destino)
        # La zona de prueba (820x300 de una imagen de 1440x900) es bastante
        # menor al 82% del área total, así que sí debía recortarse: el ancho
        # final no puede ser el de la captura original sin tocar.
        self.assertNotEqual(despues.width, antes.width)

        rojos = sum(
            1 for r, g, b in despues.convert("RGB").getdata()
            if r > 170 and g < 110 and b < 110
        )
        self.assertGreater(rojos, 500, "no se dibujó el recuadro rojo sobre la zona")

    def test_zona_que_cubre_casi_todo_no_se_recorta(self):
        """Si la zona señalada es casi toda la captura (p. ej. 'sin CTA' usa el
        fold entero como zona), recortar no aporta nada: se usa la completa."""
        from prospector.models import Finding

        origen = _captura_falsa(self.tmp / "fold.png")
        hallazgo = Finding(
            rule_id="sin_cta_fold", titulo="Sin CTA", severidad=10, peso=35,
            categoria="killer", evidencia="0 CTAs",
            argumento="x", zona={"x": 0, "y": 0, "width": 1440, "height": 900},
        )
        destino = anotar(origen, self.tmp / "anotada2.png", [hallazgo], pie="Sin CTA")
        from PIL import Image

        antes = Image.open(origen)
        despues = Image.open(destino)
        self.assertEqual(despues.width, antes.width)  # sin recorte, ancho intacto

    def test_correo_multipart_con_imagen_embebida(self):
        origen = _captura_falsa(self.tmp / "anotada.png")
        lead = Lead(nombre="Clínica Sol", url="https://clinicasol.es", email="info@clinicasol.es")
        lead.audit = Audit(score=88, veredicto="critico")
        lead.email_draft = EmailDraft(asunto="algo que vi en clinicasol.es",
                                      cuerpo="Hola,\n\nEntré en tu web.\n\nFelipe",
                                      adjunto=str(origen))
        cfg = MailSettings()
        cfg.user = "yo@ejemplo.com"
        cfg.from_name = "Felipe"
        mensaje = construir_mensaje(lead, cfg)

        self.assertEqual(mensaje["To"], "info@clinicasol.es")
        self.assertIn("Felipe", mensaje["From"])
        tipos = {parte.get_content_type() for parte in mensaje.walk()}
        self.assertIn("text/plain", tipos)
        self.assertIn("text/html", tipos)
        self.assertIn("image/png", tipos)
        html = mensaje.get_body(preferencelist=("html",)).get_content()
        self.assertIn("cid:", html)

    def test_informe_html_se_genera(self):
        from prospector import report

        destino = report.generar(destino=self.tmp / "informe.html")
        self.assertTrue(destino.exists())
        contenido = destino.read_text(encoding="utf-8")
        self.assertIn("Informe de prospección", contenido)


if __name__ == "__main__":
    unittest.main(verbosity=2)
