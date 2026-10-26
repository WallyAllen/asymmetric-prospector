"""La web de un comercio está en su ficha de Maps, no en la tarjeta del listado."""
import unittest

from scrapling.parser import Selector

from prospector.sources.google_maps import _parse_card

FICHA_CON_WEB = """
<div role="main" aria-label="Tienda Ejemplo La Plata">
  <a data-item-id="authority" href="https://tiendaejemplo.com.ar/"
     aria-label="Sitio web: tiendaejemplo.com.ar ">tiendaejemplo.com.ar</a>
  <button data-item-id="phone:tel:02210000000">0221 000-0000</button>
</div>
"""

FICHA_SIN_WEB = """
<div role="main" aria-label="Otra Tienda Ejemplo">
  <button data-item-id="address">C. 1 100</button>
</div>
"""

# Tarjeta del listado tal como la devuelve Maps para una tienda (15/10/2026):
# ningún enlace externo, aunque el negocio tiene web.
TARJETA_TIENDA = """
<div class="Nv2PK">
  <a href="https://www.google.com/maps/place/Tienda+Ejemplo+La+Plata/data=!4m7"
     aria-label="Tienda Ejemplo La Plata"></a>
  <div>Tienda Ejemplo La Plata 4,8(120) Tienda de ropa para jóvenes · C. 2 200
       Abierto · Cierra a las 8 p. m. · 0221 000-0000</div>
</div>
"""


class TestWebDesdeLaFicha(unittest.TestCase):
    def test_web_de_ficha_lee_authority(self):
        from prospector.sources.google_maps import _web_de_ficha
        self.assertEqual(_web_de_ficha(Selector(FICHA_CON_WEB)), "https://tiendaejemplo.com.ar/")

    def test_web_de_ficha_sin_web(self):
        from prospector.sources.google_maps import _web_de_ficha
        self.assertIsNone(_web_de_ficha(Selector(FICHA_SIN_WEB)))

    def test_tarjeta_de_tienda_no_trae_web(self):
        # Documenta por qué hace falta abrir la ficha: la tarjeta sola no alcanza.
        tarjeta = Selector(TARJETA_TIENDA).css("div.Nv2PK").first
        lead = _parse_card(tarjeta, "tiendas de ropa La Plata")
        self.assertEqual(lead.nombre, "Tienda Ejemplo La Plata")
        self.assertIsNone(lead.url)


if __name__ == "__main__":
    unittest.main()
