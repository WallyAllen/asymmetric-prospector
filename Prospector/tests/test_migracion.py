"""La migración del formato antiguo no debe perder trabajo ya hecho."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.migrate import _es_legado, _migrar_archivo  # noqa: E402
from prospector.models import Lead  # noqa: E402


class TestMigracion(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_detecta_formato_legado(self):
        self.assertTrue(_es_legado({"cro_audit": {}}))
        self.assertTrue(_es_legado({"email_content": {}}))
        self.assertFalse(_es_legado({"audit": {}}))

    def test_migra_sin_fabricar_un_score_falso(self):
        """El score viejo salía de una sola opinión de IA sin métricas: no se
        traduce a un score nuevo, el lead vuelve a 'crudo' para remedirse."""
        ruta = self.tmp / "leads.json"
        ruta.write_text(json.dumps([
            {
                "url": "https://clinicasol.es",
                "email": "info@clinicasol.es",
                "screenshot_path": r"C:\otra\maquina\clinicasol.es.png",
                "cro_audit": {"problema_cro": "Sin CTA visible en el fold", "urgencia": 8},
            }
        ]), encoding="utf-8")

        convertidos = _migrar_archivo(ruta)
        self.assertEqual(convertidos, 1)

        datos = json.loads(ruta.read_text(encoding="utf-8"))
        lead = Lead.from_dict(datos[0])
        self.assertEqual(lead.estado, "crudo")
        self.assertIsNone(lead.audit)
        self.assertIsNone(lead.email_draft)
        self.assertEqual(lead.email, "info@clinicasol.es")  # el contacto no se pierde

    def test_es_idempotente(self):
        ruta = self.tmp / "leads.json"
        ruta.write_text(json.dumps([
            {"url": "https://x.es", "email": "a@x.es",
             "cro_audit": {"problema_cro": "X", "urgencia": 5}}
        ]), encoding="utf-8")
        self.assertEqual(_migrar_archivo(ruta), 1)
        self.assertEqual(_migrar_archivo(ruta), 0)  # segunda pasada: nada que hacer


if __name__ == "__main__":
    unittest.main(verbosity=2)
