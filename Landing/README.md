# Landing Page Mockup

Biblioteca de landing pages de alta conversión, organizadas por nicho de industria. Cada mockup es un **único archivo HTML autocontenido** (CSS y JS inline, sin build ni dependencias externas más allá de Google Fonts), pensado para personalizarse por prospecto en minutos editando un solo bloque de configuración — sin tocar el marcado.

## Estructura

```
nichos/
  <nombre_del_nicho>/
    mockup/      # Plantillas de demostración: el "molde" reutilizable del nicho
    landings/    # Proyectos reales para clientes que avanzaron (MVP en Vercel → producción en Cloudflare)
agent_skills/    # Skills para los agentes de IA que ensamblan y despliegan estas páginas
```

Nichos disponibles actualmente:

| Nicho | Mockups |
|---|---|
| `veterinarias_la_plata` | `veterinaria-aurora.html` (editorial, ilustrado, verde salvia) · `veterinaria-vivid.html` (fotográfico, colores vívidos, tipografía redondeada) |
| `contadores_la_plata` | `estudio-meridiano.html` (documental, retícula de hoja de trabajo, azul petróleo + ámbar) |

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

Con [Claude Code](https://claude.com/claude-code) ya está configurado un servidor estático en `.claude/launch.json` que sirve el directorio `nichos/`. También podés levantar cualquier servidor estático apuntando ahí, por ejemplo:

```bash
python -m http.server 8532 --directory nichos
```

Y abrir `http://localhost:8532/<nicho>/mockup/<archivo>.html`.

## Stack

HTML + CSS + JS vanilla (sin framework, sin build step). Componentes de referencia elegidos de [21st.dev](https://21st.dev) y reimplementados sin dependencias de React para mantener cada mockup como un archivo único y portable.
