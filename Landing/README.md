# Landing Page Mockup

Biblioteca de landing pages de alta conversión, organizadas por nicho de industria. Cada mockup es un **único archivo HTML autocontenido** (CSS y JS inline, sin build ni dependencias externas más allá de Google Fonts), pensado para personalizarse por prospecto en minutos editando un solo bloque de configuración — sin tocar el marcado.

## Estructura

```
nichos/
  <nombre_del_nicho>/
    mockup/      # Plantillas de demostración: el "molde" reutilizable del nicho
    landings/    # Proyectos reales para clientes que avanzaron (MVP en Vercel → producción en Cloudflare)
agent_skills/    # Skills para los agentes de IA que ensamblan y despliegan estas páginas
agencia/         # Landing propia de la agencia (no es un mockup de nicho, no se persigue a un prospecto con esto)
```

Nichos disponibles actualmente:

| Nicho | Mockups |
|---|---|
| `veterinarias_la_plata` | `veterinaria-aurora.html` (editorial, ilustrado, verde salvia) · `veterinaria-vivid.html` (fotográfico, colores vívidos, tipografía redondeada) |
| `contadores_la_plata` | `estudio-meridiano.html` (documental, retícula de hoja de trabajo, azul petróleo + ámbar) · `estudio-aesop.html` (minimalista, fotográfico, cálido) · `estudio-boca.html` (corporativo, azul noche + dorado) |
| `dentistas_la_plata` | `celestia-dental.html` (clínico moderno, ilustración 3D, azul) · `demo-dentistas/` (proyecto Astro, ver excepción abajo) |
| `abogados_la_plata` | `estudio-monocle.html` (clásico editorial, fotográfico, burdeos) · `demo-abogados/` y `juridico-dike/` (proyectos Astro, ver excepción abajo) |
| `inmobiliarias_la_plata` | `demo-inmobiliarias/` (proyecto Astro, ver excepción abajo) |
| `kinesiologia_mendoza` | `korpo-kinesiologia.html` (clínico cálido, bento grid, teal + coral, ruteo de WhatsApp por tratamiento) |

### Excepción: mockups en Astro

`demo-abogados/`, `demo-dentistas/`, `demo-inmobiliarias/` y `juridico-dike/` son proyectos [Astro](https://astro.build) completos (con build propio, dependencias de npm y su propio `CLAUDE.md`), importados de otro repo de mockups. Rompen la regla de "un único HTML autocontenido" a propósito — es una excepción documentada, no el estándar. Para correrlos: `cd` a la carpeta, `npm install`, `npm run dev`. No tienen `.env` commiteado (cada uno trae su `.env.example`); si alguno lo necesita para funcionar en local, pedile las credenciales a quien lo armó — nunca las hardcodees ni las commitees.

## Cómo funciona un mockup

Cada archivo trae, al tope del `<script>`, un objeto `CONFIG` con todo lo que cambia entre un cliente y otro: marca, contacto, horarios, servicios, equipo, reseñas, FAQ y paleta de color. Los tokens de color del CSS se recalculan en tiempo de ejecución a partir de 3 valores hex (`primario`, `acento`, `neutro`), así que cambiar la paleta reacomoda todo el diseño sin editar CSS.

Al final de cada archivo hay un bloque comentado con:
- Qué pasos seguir para personalizarlo para un prospecto nuevo (y cuánto tiempo toma cada uno).
- Qué campos de `CONFIG` son obligatorios y cuáles opcionales.
- Hipótesis de test A/B para la siguiente iteración.

**Importante:** las reseñas que trae cada plantilla son de ejemplo y están marcadas como tales en el código. Se reemplazan siempre por reseñas reales de Google al personalizar — nunca se presentan testimonios inventados como genuinos.

### Estándares de diseño

- Mobile-first, verificado a 375px sin overflow horizontal.
- Escala tipográfica fluida (`clamp`), espaciado en base 4/8px, tokens de color en CSS custom properties.
- Modo oscuro con tokens redefinidos por rol (no inversión de filtro).
- Accesibilidad WCAG 2.2 AA: contraste verificado en cada combinación texto/fondo, foco visible, `prefers-reduced-motion` respetado, alt en todas las imágenes.
- Animaciones de entrada, hover con spotlight/tilt y contadores animados, todas por debajo de 400ms.

## Previsualizar localmente

Con [Claude Code](https://claude.com/claude-code) ya está configurado un servidor estático en `.claude/launch.json` que sirve la raíz del repo. También podés levantar cualquier servidor estático desde la raíz, por ejemplo:

```bash
python -m http.server 8532
```

Y abrir `http://localhost:8532/` para la galería, o directo `http://localhost:8532/nichos/<nicho>/mockup/<archivo>.html`.

## Deploy

El repo se sirve como sitio estático (Vercel, Cloudflare Pages, o cualquier hosting estático conectado al repo de GitHub) sin ningún build step. `index.html` en la raíz es la galería que enlaza a cada mockup — sin él, la URL raíz del deploy da 404 aunque los mockups individuales carguen bien. Al agregar un nicho o un mockup nuevo, sumalo también ahí.

## Stack

HTML + CSS + JS vanilla (sin framework, sin build step). Componentes de referencia elegidos de [21st.dev](https://21st.dev) y reimplementados sin dependencias de React para mantener cada mockup como un archivo único y portable.
