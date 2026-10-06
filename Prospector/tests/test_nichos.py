"""Campañas aisladas sobre datos ficticios, sin red ni envíos."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from prospector import pipeline, report
from prospector.cli import _parser
from prospector.compose.lexicon import rubro_de
from prospector.compose.whatsapp import componer_whatsapp
from prospector.compose.writer import componer_por_plantilla
from prospector.config import ComposeSettings, Settings
from prospector.models import Audit, EmailDraft, Lead
from prospector.storage import load_leads, save_leads
from prospector.utils import coincide_nicho, es_indumentaria, is_directory, lead_id


class TestCampana(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rutas = {}
        for campo in ("RAW_FILE", "AUDITED_FILE", "COMPOSED_FILE"):
            ruta = Path(self.tmp.name) / (campo + ".json")
            self.rutas[campo] = ruta
            parche = patch.object(pipeline, campo, ruta)
            parche.start()
            self.addCleanup(parche.stop)
        self.cfg = Settings()
        self.cfg.compose = ComposeSettings(use_ai=False, sender_name="Felipe", sender_role="Diseño web",
                                          sender_site="", sender_phone="", sender_proof="")
        self.cfg.audit.min_score = 28
        self.ropa = Lead(nombre="Tienda Demo", nicho="Tiendas de Ropa La Plata",
                         telefono="+5491112345678")
        self.otro = Lead(nombre="Estudio Demo", nicho="Contadores La Plata", estado="respondido",
                         audit=Audit(score=10), email_draft=EmailDraft(cuerpo="Borrador conservado"))
        self.original = self.otro.to_dict()

    def test_filtro_y_parser(self):
        self.assertTrue(coincide_nicho("  INDUMENTARÍA   Córdoba", "indumentaria cordoba"))
        self.assertFalse(coincide_nicho("contadores", "ropa"))
        for comando in ("audit", "compose", "send", "status", "report", "enrich"):
            args = _parser().parse_args([comando, "--nicho", "ropa"])
            self.assertEqual(args.nicho, "ropa")
        self.assertFalse(_parser().parse_args(["send", "--nicho", "ropa"]).enviar_de_verdad)

    def test_auditar_limita_pendientes_y_conserva_otros_nichos(self):
        anterior = Lead(nombre="Ropa Anterior", nicho="ropa", estado="auditado", audit=Audit(score=30))
        siguiente = Lead(nombre="Ropa Siguiente", nicho="ropa")
        save_leads(self.rutas["RAW_FILE"], [self.otro, anterior, self.ropa, siguiente])
        with patch.object(pipeline, "ensure_dirs"):
            pipeline.auditar_leads(self.cfg, nicho="ropa", limite=1)
        guardados = load_leads(self.rutas["AUDITED_FILE"])
        self.assertEqual(guardados[0].to_dict(), self.original)
        self.assertEqual(guardados[2].estado, "auditado")
        self.assertEqual(guardados[2].audit.tienda["tipo"], "sin_web_enlazada")
        self.assertIsNone(guardados[3].audit)
        # Una segunda tanda avanza al siguiente pendiente.
        with patch.object(pipeline, "ensure_dirs"):
            pipeline.auditar_leads(self.cfg, nicho="ropa", limite=1)
        self.assertIsNotNone(load_leads(self.rutas["AUDITED_FILE"])[3].audit)

    def test_compose_filtra_incluso_con_forzar_y_es_idempotente(self):
        self.ropa.audit = Audit(score=100, veredicto="sin_web")
        self.ropa.estado = "auditado"
        save_leads(self.rutas["AUDITED_FILE"], [self.otro, self.ropa])
        with patch.object(pipeline, "ensure_dirs"), patch.object(pipeline, "exportar_preview"), \
             patch.object(pipeline, "exportar_whatsapp"):
            pipeline.redactar_correos(self.cfg, nicho="ropa", forzar=True)
            primera = self.rutas["COMPOSED_FILE"].read_bytes()
            pipeline.redactar_correos(self.cfg, nicho="ropa")
        self.assertEqual(primera, self.rutas["COMPOSED_FILE"].read_bytes())
        guardados = load_leads(self.rutas["COMPOSED_FILE"])
        self.assertEqual(guardados[0].to_dict(), self.original)
        self.assertIn("talles", guardados[1].email_draft.cuerpo)

    def test_send_filtra_y_preserva_simulacion(self):
        save_leads(self.rutas["COMPOSED_FILE"], [self.otro, self.ropa])
        with patch.object(pipeline, "ensure_dirs"), patch.object(pipeline, "enviar") as enviar:
            pipeline.enviar_correos(self.cfg, nicho="ropa", limite=5)
        seleccionados = enviar.call_args.args[0]
        self.assertEqual([l.id for l in seleccionados], [self.ropa.id])
        self.assertTrue(enviar.call_args.kwargs["simular"])
        self.assertEqual(load_leads(self.rutas["COMPOSED_FILE"])[0].to_dict(), self.original)

    def test_enrich_no_visita_otros_nichos(self):
        save_leads(self.rutas["RAW_FILE"], [self.otro, self.ropa])
        visitados = []

        async def enriquecer(leads, cfg, on_lead_done):
            visitados.extend(l.id for l in leads)
            leads[0].email = "hola@tienda.test"
            await on_lead_done(leads)
            return leads

        with patch.object(pipeline, "ensure_dirs"), patch.object(pipeline, "enrich_contacts", enriquecer):
            pipeline.enriquecer_contactos(self.cfg, nicho="ropa")
        self.assertEqual(visitados, [self.ropa.id])
        guardados = load_leads(self.rutas["RAW_FILE"])
        self.assertEqual(guardados[0].to_dict(), self.original)
        self.assertEqual(guardados[1].email, "hola@tienda.test")

    def test_whatsapp_filtra_antes_de_abrir_chats(self):
        from scripts import send_whatsapp
        with patch("sys.argv", ["send_whatsapp.py", "--nicho", "ropa"]), \
             patch.object(send_whatsapp, "load_leads", return_value=[self.otro]), \
             patch.object(send_whatsapp, "cola_whatsapp", return_value=[self.otro]), \
             patch.object(send_whatsapp, "cuota_whatsapp") as cuota, \
             patch.object(send_whatsapp.webbrowser, "open") as abrir, patch("builtins.print"):
            self.assertEqual(send_whatsapp.main(), 0)
        cuota.assert_not_called()
        abrir.assert_not_called()

    def test_run_no_procesa_otras_campanas(self):
        with patch.object(pipeline, "minar"), patch.object(pipeline, "auditar_leads") as auditar, \
             patch.object(pipeline, "redactar_correos") as redactar, \
             patch.object(pipeline, "enviar_correos") as enviar:
            pipeline.ejecutar_todo("ropa La Plata", self.cfg)
        for llamada in (auditar, redactar, enviar):
            self.assertEqual(llamada.call_args.kwargs["nicho"], "ropa La Plata")
        self.assertTrue(enviar.call_args.kwargs["simular"])

    def test_plataformas_no_colapsan_tiendas_y_conservan_ids_previos(self):
        a = "https://prospector-fixture-a.mitiendanube.com"
        b = "https://prospector-fixture-b.mitiendanube.com"
        self.assertNotEqual(lead_id(a), lead_id(b))
        self.assertFalse(is_directory("https://prospector-fixture.myshopify.com"))
        legacy = Lead(id="mitiendanube.com", nombre="Tienda Demo Anterior", url=a,
                      nicho="ropa", estado="respondido")
        save_leads(self.rutas["RAW_FILE"], [legacy])

        async def minar(query, cfg):
            return [Lead(nombre="Tienda Demo A", url=a), Lead(nombre="Tienda Demo B", url=b)]

        with patch.object(pipeline, "ensure_dirs"), patch.object(pipeline, "mine_google_maps", minar):
            leads = pipeline.minar("ropa", self.cfg, enriquecer=False)
        self.assertEqual(len(leads), 2)
        self.assertEqual(leads[0].id, legacy.id)
        self.assertEqual(leads[0].estado, "respondido")
        self.assertEqual(leads[1].url, b)

    def test_buscador_conserva_subdominios_de_tiendas(self):
        from prospector.sources.search import mine_search_engine
        respuesta = Mock()
        respuesta.css.return_value.getall.return_value = [
            "https://prospector-fixture-a.mitiendanube.com/productos/remera",
            "https://prospector-fixture-b.mitiendanube.com/productos/remera",
            "https://prospector-fixture.myshopify.com/products/remera"]
        self.cfg.mining.max_leads = 3
        with patch("scrapling.fetchers.Fetcher.post", return_value=respuesta):
            leads = mine_search_engine("ropa", self.cfg.mining, paginas=1)
        self.assertEqual(len(leads), 3)
        self.assertEqual(leads[0].url, "https://prospector-fixture-a.mitiendanube.com")
        self.assertEqual(len({l.id for l in leads}), 3)

    def test_report_no_incluye_otros_nichos_y_escapa_evidencia(self):
        self.ropa.audit = Audit(score=40, tienda={"tipo": "sin_clasificar", "paginas": [
            {"clase": "producto", "url": "<script>demo</script>", "status": 404}],
            "pendientes": ["Elegir talle"]})
        self.ropa.estado = "auditado"
        with patch.object(report, "load_leads", return_value=[self.ropa, self.otro]):
            destino = report.generar(Path(self.tmp.name) / "informe.html", nicho="ropa")
        texto = destino.read_text(encoding="utf-8")
        self.assertIn("Tienda Demo", texto)
        self.assertNotIn("Estudio Demo", texto)
        self.assertIn("&lt;script&gt;", texto)
        self.assertNotIn("<script>demo", texto)

    def test_redaccion_de_ropa_en_ambos_canales(self):
        for nicho in ("ropa deportiva", "indumentaria femenina", "boutique Córdoba"):
            self.assertTrue(es_indumentaria(nicho))
            self.assertIn("prenda", rubro_de(nicho).accion)
            self.ropa.nicho = nicho
            email = componer_por_plantilla(self.ropa, self.cfg.compose, tiene_adjunto=False)
            wa = componer_whatsapp(self.ropa, self.cfg.compose)
            for texto in (email.cuerpo, wa.cuerpo):
                self.assertIn("talles", texto)
                self.assertNotIn("turno", texto)
                self.assertNotIn("agregué", texto)


if __name__ == "__main__":
    unittest.main()
