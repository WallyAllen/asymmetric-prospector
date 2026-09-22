"""Pruebas de tienda en Chromium contra páginas ficticias interceptadas."""
import tempfile
import unittest
from pathlib import Path

from prospector.audit.probe_js import AUDIT_JS
from prospector.audit.rules import enlace_tienda_roto, sin_vias_de_contacto, sin_telefono_pulsable
from prospector.audit.signals import ProbeResult, _consolidar
from prospector.audit.tienda import inspeccionar
from prospector.models import Audit, Lead, Metrics


class TestTiendaModelo(unittest.TestCase):
    def test_json_nuevo_y_legacy(self):
        lead = Lead(nombre="Tienda Demo", audit=Audit(tienda={"tipo": "sin_clasificar"}))
        self.assertEqual(Lead.from_dict(lead.to_dict()).audit.tienda, lead.audit.tienda)
        self.assertEqual(Audit.from_dict({"score": 20}).tienda, {})

    def test_timeouts_y_bloqueos_no_son_enlaces_rotos(self):
        for status in (None, 403, 429, 503):
            res = ProbeResult(ok=True, tienda={"paginas": [{"clase": "producto", "status": status}]})
            self.assertIsNone(enlace_tienda_roto(res))

    def test_mensaje_y_adjunto_corresponden_al_enlace_probado(self):
        from prospector.compose.writer import componer_por_plantilla, _ruta_adjunto
        from prospector.config import ComposeSettings
        pagina = {"clase": "producto", "url": "https://tienda.test/productos/remera",
                  "status": 404, "roto_confirmado": True}
        res = ProbeResult(ok=True, tienda={"paginas": [pagina]})
        hallazgo = enlace_tienda_roto(res)
        lead = Lead(nombre="Tienda Demo", url="https://tienda.test", nicho="ropa", audit=Audit(
            score=30, findings=[hallazgo], tienda=res.tienda,
            capturas={"tienda_producto": "data/ficticia.png", "principal": "data/portada-ficticia.png"},
            captura_marcada=True))
        self.assertEqual(_ruta_adjunto(lead), ("data/ficticia.png", False))
        cfg = ComposeSettings(sender_proof="", sender_site="", sender_phone="")
        texto = componer_por_plantilla(lead, cfg, tiene_adjunto=True, es_marcada=False).cuerpo
        self.assertIn("captura del enlace", texto)
        self.assertNotIn("Mirando la primera pantalla", texto)
        self.assertNotIn("zona marcada", texto)


class TestTiendaNavegador(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from playwright.async_api import async_playwright
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=True)
        self.context = await self.browser.new_context(viewport={"width": 390, "height": 844})
        self.visitas = []
        self.product_status = [200]
        self.home = '<a href="/productos/remera/">Remera</a><a href="/carrito/" aria-label="Carrito">Carrito</a>'
        self.product = '''<h1>Remera Demo</h1><select name="Talle"><option value="">Elegí talle</option>
          <option value="M">M</option></select><button>Agregar al carrito</button>
          <script type="application/ld+json">{"@type":"Product","name":"Remera Demo",
          "offers":{"price":"10000","priceCurrency":"ARS","availability":"https://schema.org/InStock"}}</script>'''

        async def responder(route):
            req = route.request
            self.visitas.append((req.method, req.url))
            ruta = req.url.split("tienda.test", 1)[-1]
            status, contenido = 200, self.home
            if ruta.startswith("/productos/"):
                status = self.product_status[0]
                if len(self.product_status) > 1:
                    self.product_status.pop(0)
                contenido = self.product if status == 200 else "Producto inexistente"
            elif ruta.startswith("/carrito/"):
                contenido = "<h1>Carrito vacío</h1>"
            await route.fulfill(status=status, content_type="text/html", body=contenido)
        await self.context.route("**/*", responder)

    async def asyncTearDown(self):
        await self.context.close()
        await self.browser.close()
        await self.pw.stop()

    async def inspeccion(self):
        return await inspeccionar(self.context, "https://tienda.test/", Path(self.tmp.name), 5000)

    async def test_recorrido_lectura_y_pendientes_sin_crear_pedidos(self):
        revision = await self.inspeccion()
        self.assertEqual(revision["tipo"], "tienda_online_indicios")
        self.assertEqual(len(revision["paginas"]), 2)
        producto = revision["paginas"][0]
        self.assertEqual(producto["senales"]["variantes"][0]["opciones"], ["M"])
        self.assertEqual(producto["senales"]["datos"][0]["ofertas"][0]["precio"], "10000")
        self.assertEqual(len(revision["pendientes"]), 3)
        self.assertTrue(all(m == "GET" for m, _ in self.visitas))
        self.assertTrue(all(Path(p).exists() for p in revision["capturas"].values()))

    async def test_404_repetido_genera_hallazgo_y_transitorio_no(self):
        self.product_status = [404, 404]
        revision = await self.inspeccion()
        hallazgo = enlace_tienda_roto(ProbeResult(ok=True, tienda=revision))
        self.assertIsNotNone(hallazgo)
        self.assertIn("dos visitas", hallazgo.evidencia)
        self.product_status = [404, 200]
        revision = await self.inspeccion()
        self.assertIsNone(enlace_tienda_roto(ProbeResult(ok=True, tienda=revision)))

    async def test_compra_valida_no_se_acusa_de_falta_de_contacto(self):
        self.home += '<a role="button">Menú</a>'
        page = await self.context.new_page()
        await page.goto("https://tienda.test/")
        datos = await page.evaluate(AUDIT_JS)
        res = ProbeResult(ok=True, desktop=datos, metrics=Metrics())
        _consolidar(res)
        self.assertTrue(res.metrics.tiene_compra)
        self.assertIsNone(sin_vias_de_contacto(res))
        self.assertIsNone(sin_telefono_pulsable(res))

    async def test_enlaces_externos_y_acciones_no_se_visitan(self):
        self.home = '''<a href="https://externo.test/products/remera">Producto externo</a>
          <a href="/cart/add?id=1">Agregar</a><a href="/checkout/">Pagar</a>
          <a href="https://wa.me/5491112345678">WhatsApp</a>'''
        revision = await self.inspeccion()
        self.assertEqual(revision["paginas"], [])
        self.assertEqual(self.visitas, [("GET", "https://tienda.test/")])


if __name__ == "__main__":
    unittest.main()
