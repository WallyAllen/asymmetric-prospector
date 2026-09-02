"""JavaScript de auditoría que se inyecta en la página.

Devuelve datos duros y, sobre todo, los rectángulos de las zonas problemáticas:
esos rectángulos son los que después se marcan en rojo sobre la captura.
"""

AUDIT_JS = r"""
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const rectOf = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    if (!r || (r.width <= 0 && r.height <= 0)) return null;
    return { x: Math.max(0, r.left), y: Math.max(0, r.top + window.scrollY),
             width: Math.min(r.width, vw), height: r.height };
  };
  // Un <h1> o <section> es un bloque: su caja ocupa el 100% del contenedor
  // aunque el texto real ocupe la mitad. Para recortar la captura alrededor
  // de lo que el ojo realmente ve, hace falta el borde del CONTENIDO, no el
  // del bloque: se mide con un Range sobre los nodos internos, que sí se
  // ciñe al texto/imagen renderizados.
  const contentRectOf = (el) => {
    if (!el) return null;
    try {
      const range = document.createRange();
      range.selectNodeContents(el);
      const r = range.getBoundingClientRect();
      if (r && r.width > 0 && r.height > 0) {
        return { x: Math.max(0, r.left), y: Math.max(0, r.top + window.scrollY),
                 width: Math.min(r.width, vw), height: r.height };
      }
    } catch (e) { /* elemento sin contenido seleccionable */ }
    return rectOf(el);
  };
  const visible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) < 0.1) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const txt = (el) => (el.innerText || el.textContent || '').trim();

  const ACTION = /(contact|contacta|llamar|llama|pedir|solicit|reserv|agend|cita|presupuest|compra|comprar|cotiz|whatsapp|escríb|escrib|empieza|empezar|prueba|demo|consulta|book|call|quote|start|buy)/i;
  const NAV_ONLY = /^(inicio|home|nosotros|about|blog|servicios|services|productos|contacto|contact|faq|legal|privacidad|cookies)$/i;

  // ---------- Meta / SEO ----------
  const meta = (n) => { const e = document.querySelector(`meta[name="${n}"]`); return e ? (e.content||'').trim() : null; };
  const metaProp = (p) => { const e = document.querySelector(`meta[property="${p}"]`); return e ? (e.content||'').trim() : null; };

  // ---------- CTAs en el primer pantallazo ----------
  const clickables = Array.from(document.querySelectorAll('a[href], button, input[type=submit], [role=button]'));
  const nav = document.querySelector('header nav, nav, header');
  const inNav = (el) => nav ? nav.contains(el) : false;
  const foldCtas = [];
  for (const el of clickables) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.top > vh * 0.95 || r.top + r.height < 0) continue;
    const label = txt(el).slice(0, 80);
    const aria = (el.getAttribute('aria-label') || '').slice(0, 80);
    const both = label + ' ' + aria;
    if (!both.trim()) continue;
    const isAction = ACTION.test(both) && !NAV_ONLY.test(label.trim());
    const looksButton = (() => {
      const s = getComputedStyle(el);
      const bg = s.backgroundColor || '';
      const solid = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
      return solid && r.height >= 32 && r.width >= 80;
    })();
    if (isAction || (looksButton && !inNav(el) && !NAV_ONLY.test(label.trim()))) {
      foldCtas.push({ label: label || aria, rect: rectOf(el), enNav: inNav(el) });
    }
  }

  // ---------- Texto del fold ----------
  let foldText = '';
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (!parent || !visible(parent)) continue;
    const r = parent.getBoundingClientRect();
    if (r.top > vh || r.bottom < 0) continue;
    foldText += ' ' + (node.textContent || '');
  }
  const foldWords = foldText.trim().split(/\s+/).filter(Boolean).length;

  // ---------- Hero / H1 ----------
  const h1s = Array.from(document.querySelectorAll('h1')).filter(visible);
  const heroCandidate = h1s[0] || document.querySelector('header, .hero, section');

  // ---------- Imágenes ----------
  const imgs = Array.from(document.images);
  let sinAlt = 0, sobredimensionadas = 0, mayorImg = null, mayorArea = 0;
  for (const img of imgs) {
    if (!img.alt || !img.alt.trim()) sinAlt++;
    const r = img.getBoundingClientRect();
    if (img.naturalWidth && r.width && img.naturalWidth > r.width * 2.5 && r.width > 50) {
      sobredimensionadas++;
    }
    const area = r.width * r.height;
    if (r.top < vh && area > mayorArea) { mayorArea = area; mayorImg = img; }
  }

  // ---------- Overlays intrusivos (cookies, popups) ----------
  let popup = null, popupArea = 0;
  for (const el of document.body.querySelectorAll('div,section,aside,dialog')) {
    const s = getComputedStyle(el);
    if (s.position !== 'fixed' && s.position !== 'sticky') continue;
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    const area = r.width * r.height;
    const z = parseInt(s.zIndex || '0', 10) || 0;
    if (area > vw * vh * 0.12 && z >= 100 && r.height < vh * 0.95) {
      if (area > popupArea) { popupArea = area; popup = el; }
    }
  }

  // ---------- Legibilidad y toques ----------
  let textoPequeno = 0, tapPequenos = 0;
  const muestras = Array.from(document.querySelectorAll('p,li,span,a,div,button,td')).slice(0, 1200);
  for (const el of muestras) {
    if (!visible(el)) continue;
    const contenido = txt(el);
    if (!contenido || contenido.length < 3) continue;
    const size = parseFloat(getComputedStyle(el).fontSize) || 16;
    if (size < 13 && el.children.length === 0) textoPequeno++;
    if (el.matches('a,button,[role=button]')) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && (r.width < 40 || r.height < 32)) tapPequenos++;
    }
  }

  // ---------- Menú ----------
  const menuItems = nav ? Array.from(nav.querySelectorAll('a')).filter(visible).length : 0;

  // ---------- Copyright ----------
  const footer = document.querySelector('footer') || document.body;
  const footTxt = (footer.innerText || '').slice(-1500);
  const years = (footTxt.match(/(19|20)\d{2}/g) || []).map(Number);
  const anoCopyright = years.length ? Math.max(...years) : null;

  // ---------- Rendimiento ----------
  const navEntry = performance.getEntriesByType('navigation')[0] || {};
  const paints = {};
  for (const p of performance.getEntriesByType('paint')) paints[p.name] = p.startTime;

    // ---------- Detección de directorio/agregador ----------
    // Un directorio lista múltiples negocios: tiene muchos tel: y mailto: distintos.
    const telsUnicos = new Set(
      Array.from(document.querySelectorAll('a[href^="tel:"]'))
        .map(a => a.href.replace('tel:', '').replace(/\s/g, ''))
        .filter(Boolean)
    ).size;
    const emailsUnicos = new Set(
      Array.from(document.querySelectorAll('a[href^="mailto:"]'))
        .map(a => a.href.replace('mailto:', '').split('?')[0].toLowerCase())
        .filter(Boolean)
    ).size;
    // Título estilo directorio: "Mejores X en Y", "Los 10 mejores...", "Directorio de..."
    const tituloDir = /\b(mejores?|top\s*\d|directorio\s+de|gu[ií]a\s+de|listado\s+de|d[oó]nde\s+encontrar)\b/i.test(
      document.title + ' ' + (document.querySelector('h1')?.innerText || '')
    );

    return {
    title: (document.title || '').trim() || null,
    metaDescription: meta('description'),
    generador: meta('generator'),
    tieneViewportMeta: !!document.querySelector('meta[name="viewport"]'),
    favicon: !!document.querySelector('link[rel~="icon"]'),
    ogImage: !!metaProp('og:image'),
    h1: h1s.length,
    idioma: document.documentElement.lang || null,
    formularios: document.querySelectorAll('form').length,
    inputsVisibles: Array.from(document.querySelectorAll('form input,form textarea')).filter(visible).length,
    telLinks: document.querySelectorAll('a[href^="tel:"]').length,
    mailtoLinks: document.querySelectorAll('a[href^="mailto:"]').length,
    whatsapp: document.querySelectorAll('a[href*="wa.me"],a[href*="api.whatsapp"],a[href*="whatsapp.com/send"]').length,
    ctasEnFold: foldCtas.length,
    ctas: foldCtas.slice(0, 5),
    palabrasEnFold: foldWords,
    imagenes: imgs.length,
    imagenesSinAlt: sinAlt,
    imagenesSobredimensionadas: sobredimensionadas,
    textoPequeno: textoPequeno,
    tapPequenos: tapPequenos,
    itemsMenu: menuItems,
    anoCopyright: anoCopyright,
    overflowHorizontal: document.documentElement.scrollWidth > vw + 8,
    anchoScroll: document.documentElement.scrollWidth,
    anchoVentana: vw,
    altoDocumento: document.documentElement.scrollHeight,
    popupIntrusivo: !!popup,
    scriptsExternos: document.querySelectorAll('script[src]').length,
    flash: !!document.querySelector('object[type*="flash"],embed[type*="flash"]'),
    tablasLayout: document.querySelectorAll('table[width],table[border]').length,
    telsUnicos: telsUnicos,
    emailsUnicos: emailsUnicos,
    tituloDirectorio: tituloDir,
    rects: {
      hero: contentRectOf(heroCandidate),
      nav: rectOf(nav),
      cta: foldCtas.length ? foldCtas[0].rect : null,
      popup: rectOf(popup),
      imagenPrincipal: rectOf(mayorImg),
      fold: { x: 0, y: 0, width: vw, height: vh },
    },
    timing: {
      ttfb: navEntry.responseStart || null,
      domReady: navEntry.domContentLoadedEventEnd || null,
      load: navEntry.loadEventEnd || null,
      fcp: paints['first-contentful-paint'] || null,
    },
  };
}
"""

# Observadores que deben registrarse ANTES de que la página cargue.
WEB_VITALS_INIT_JS = r"""
window.__vitals = { lcp: null, cls: 0 };
try {
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    if (entries.length) window.__vitals.lcp = entries[entries.length - 1].startTime;
  }).observe({ type: 'largest-contentful-paint', buffered: true });
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__vitals.cls += entry.value;
    }
  }).observe({ type: 'layout-shift', buffered: true });
} catch (e) { /* navegador sin soporte */ }
"""
