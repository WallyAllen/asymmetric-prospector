"""Precalificación de indumentaria en móvil: señales y enlaces, sin crear pedidos.

No encontrar un selector no demuestra un fallo. Las pruebas de variantes,
stock, agregado al carrito, envío y pago quedan explícitamente pendientes.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


TIENDA_JS = r"""
() => {
  const visible = e => {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const links = [...document.querySelectorAll('a[href]')].filter(visible);
  const locales = links.filter(e => {
    const u = new URL(e.href);
    return u.origin === location.origin && !u.search && !u.hash && /^https?:$/.test(u.protocol);
  });
  const productos = locales.filter(e => /\/(products?|productos?)\/[^/]+\/?$/i.test(new URL(e.href).pathname));
  const carrito = locales.find(e => /\/(cart|carrito|carro)\/?$/i.test(new URL(e.href).pathname));
  const compra = [...document.querySelectorAll('button,a,input[type=submit],[role=button]')]
    .filter(visible).some(e => /(agregar al carrito|añadir al carrito|add to cart|comprar|buy now)/i
      .test((e.innerText || '') + ' ' + (e.value || '') + ' ' + (e.getAttribute('aria-label') || '')));
  const whatsapp = links.some(e => /https:\/\/(wa\.me\/|(?:api\.|web\.)?whatsapp\.com\/send)/i.test(e.href));
  const variantes = [...document.querySelectorAll('select')].filter(visible)
    .map(e => ({nombre: e.getAttribute('aria-label') || e.name || e.id,
      opciones: [...e.options].filter(o => !o.disabled && o.value).map(o => o.text.trim())}));
  const datos = [];
  const visitar = obj => {
    if (!obj || typeof obj !== 'object') return;
    if (Array.isArray(obj)) { obj.forEach(visitar); return; }
    const tipos = [].concat(obj['@type'] || []);
    if (tipos.some(t => /^(?:https?:\/\/schema.org\/)?Product$/i.test(t))) {
      datos.push({nombre: obj.name || null, ofertas: [].concat(obj.offers || []).map(o => ({
        precio: o.price ?? o.lowPrice ?? null, moneda: o.priceCurrency || null,
        disponibilidad: o.availability || null}))});
    }
    Object.values(obj).forEach(visitar);
  };
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try { visitar(JSON.parse(s.textContent)); } catch (_) { /* JSON inválido: no inferir */ }
  }
  return {productos: [...new Set(productos.map(e => e.href))].slice(0, 3),
    carrito: carrito?.href || null, compra, whatsapp, variantes, datos: datos.slice(0, 3)};
}
"""


def clasificar(senales: dict) -> str:
    if senales.get("compra") or senales.get("carrito"):
        return "tienda_online_indicios"
    if senales.get("whatsapp") and (senales.get("productos") or senales.get("datos")):
        return "catalogo_whatsapp_indicios"
    return "sin_clasificar"


async def inspeccionar(context, url: str, carpeta: Path, timeout: int) -> dict:
    page = await context.new_page()
    resultado = {"tipo": "no_medido", "paginas": [], "capturas": {}, "pendientes": [
        "Elegir talle y color y contrastar disponibilidad",
        "Agregar una prenda y comprobar contenido y total del carrito",
        "Comprobar costo de envío y avance al checkout sin pagar",
    ]}
    respuesta = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    if not respuesta or respuesta.status >= 400:
        return resultado
    await page.wait_for_timeout(600)
    home = await page.evaluate(TIENDA_JS)
    resultado.update(tipo=clasificar(home), senales=home)
    origen = urlparse(page.url).netloc
    objetivos = [("producto", home["productos"][0])] if home["productos"] else []
    if home["carrito"]:
        objetivos.append(("carrito", home["carrito"]))
    for clase, destino in objetivos:
        prueba = {"clase": clase, "url": destino, "status": None, "roto_confirmado": False}
        resultado["paginas"].append(prueba)
        try:
            respuesta = await page.goto(destino, wait_until="domcontentloaded", timeout=timeout)
            if urlparse(page.url).netloc != origen or not respuesta:
                prueba["estado"] = "revisar_redireccion"
                continue
            prueba["status"] = respuesta.status
            if respuesta.status in {404, 410}:
                repetida = await page.goto(destino, wait_until="domcontentloaded", timeout=timeout)
                prueba["roto_confirmado"] = bool(repetida and repetida.status == respuesta.status
                                                and urlparse(page.url).netloc == origen)
            elif respuesta.ok:
                await page.wait_for_timeout(400)
                prueba["senales"] = await page.evaluate(TIENDA_JS)
                if clase == "producto" and prueba["senales"]["compra"]:
                    resultado["tipo"] = "tienda_online_indicios"
            ruta = carpeta / f"tienda-{clase}.png"
            await page.screenshot(path=str(ruta), animations="disabled")
            resultado["capturas"][f"tienda_{clase}"] = str(ruta)
        except Exception as exc:
            prueba["estado"] = "no_medido"
            prueba["error"] = type(exc).__name__
            prueba["roto_confirmado"] = False
    return resultado
