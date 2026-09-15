# Plan de Implementación: Landing Page para Dikè & Asociados (abogadolaplata.com.ar)

## Objetivo

Construir la landing de conversión **directamente para Dikè & Asociados** usando su dominio premium (`abogadolaplata.com.ar`). No hay "template genérico" — el MVP sale como producto terminado, hosteado en Vercel, listo para mostrar en reunión presencial en La Plata. Después, el sistema de personalización via `estudio.js` permite clonar y adaptar para futuros clientes en < 30 minutos.

---

## 1. Stack Técnico

| Decisión | Elección | Por qué |
|:---|:---|:---|
| **Framework** | **Astro** | Genera HTML estático puro. Carga instantánea (<1s). Lighthouse 100. No necesitamos React ni interactividad compleja. Ideal para landing pages |
| **Hosting** | **Vercel** (free tier) | Deploy en 30 segundos. SSL gratis. Dominio custom gratis. CDN global |
| **CSS** | **Vanilla CSS** con custom properties | Sin dependencias. Variables CSS para cambiar colores del estudio en 1 línea |
| **Tipografía** | **Inter** (body) + **Playfair Display** (títulos) | Combinación profesional, legible, premium. Google Fonts gratis |
| **Imágenes** | Generadas con IA + fotos reales del estudio | Para el template genérico usamos placeholders de calidad. Para el personalizado, foto real del estudio |

> [!TIP]
> **¿Por qué Astro y no Next.js?** Next.js es lo que usa Chumba (nuestro benchmark), pero es overkill para una landing de 1 página. Astro genera HTML estático puro — cero JavaScript en el cliente = Lighthouse 100 garantizado. Cuando un prospecto necesite blog o múltiples páginas (Capa 2+), ahí sí migramos a Next.js.

---

## 2. Estructura de Secciones (basado en el benchmark Chumba y Asociados)

Cada sección tiene un **propósito de conversión** claro:

```
┌─────────────────────────────────────────────────────┐
│  TOP BAR: Zona + Teléfono                           │
│  NAVBAR: Logo + Links ancla + [WhatsApp CTA]        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  HERO                                               │
│  ─────                                              │
│  Subtítulo: "Abogados laborales · La Plata"         │
│  Título:    "Defendemos sus derechos"               │
│  Párrafo:   Copy de 2 líneas sobre el servicio      │
│  CTAs:      [Consultar mi caso] [WhatsApp]          │
│  Nota:      "Consulta confidencial y sin compromiso"│
│                                                     │
│  BARRA DE DATOS (3 columnas)                        │
│  ─────────────                                      │
│  "30 años" | "500+ casos" | "Consulta gratuita"     │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ÁREAS DE PRÁCTICA (grid 2x3 o lista)               │
│  ──────────────────                                 │
│  01 Despidos                                        │
│  02 Accidentes de trabajo                           │
│  03 Trabajo no registrado                           │
│  04 Enfermedades profesionales                      │
│  (Adaptable a la especialidad del estudio)          │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  CÓMO TRABAJAMOS (3 pasos)                          │
│  ─────────────────                                  │
│  01 Contanos tu caso (WhatsApp o teléfono)          │
│  02 Evaluamos qué te corresponde                    │
│  03 Reclamamos y te explicamos cada paso            │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  EL ESTUDIO (Confianza + Estatus)                   │
│  ──────────                                         │
│  Foto del estudio/abogado + Descripción             │
│  Sede + Teléfono + Email + Zona de atención         │
│  Bullets de diferenciación                          │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  TESTIMONIOS (carousel horizontal)                  │
│  ────────────                                       │
│  Rating 5.0 ★★★★★ (X opiniones)                    │
│  Cards con citas reales de Google                   │
│  Link: "Leerlas en Google"                          │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  FAQ (Preguntas frecuentes)                         │
│  ───                                                │
│  Accordion con 3-5 preguntas clave                  │
│  (genera Schema FAQ para SEO)                       │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  FORMULARIO → WHATSAPP DIRECTO                      │
│  ──────────────────────────────                      │
│  Nombre + Teléfono + "Describí tu caso"             │
│  [Enviar por WhatsApp]                              │
│  (abre wa.me/ con mensaje pre-formateado,           │
│   SIN email, SIN intermediarios)                    │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  FOOTER                                             │
│  ──────                                             │
│  Logo + datos del estudio + matrícula               │
│  © 2026 + "Sitio por [tu marca]"                    │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  BOTÓN FLOTANTE WHATSAPP (siempre visible)          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 3. Sistema de Personalización Rápida

Todo lo que cambia entre un estudio y otro se concentra en **UN solo archivo de configuración**:

```javascript
// src/data/estudio.js — ÚNICO ARCHIVO QUE SE EDITA POR CLIENTE
// PRIMERA BUILD: Dikè & Asociados (abogadolaplata.com.ar)

export const estudio = {
  // Identidad
  nombre: "Dikè & Asociados",
  especialidad: "Abogados penalistas y de familia",
  slogan: "Su defensa, nuestra prioridad",
  descripcion: "Estudio jurídico integral en La Plata especializado en derecho penal y de familia.",

  // Ubicación
  zona: "La Plata",
  direccion: "[A COMPLETAR — dato real del estudio]",
  provincia: "Buenos Aires",

  // Contacto — SIN EMAIL (WhatsApp es el único canal de conversión)
  telefono: "[A COMPLETAR]",
  telefonoDisplay: "[A COMPLETAR]",
  whatsapp: "[A COMPLETAR]",
  whatsappMensaje: "Hola, quiero hacer una consulta legal.",

  // Credenciales — SOLO datos verificables, NADA inventado
  matricula: "[A COMPLETAR — matrícula CALP real]",
  fundacion: null, // Si no se sabe, se oculta automáticamente
  // NO hay "casosResueltos" ni métricas genéricas

  // Áreas de práctica (adaptable)
  areas: [
    { nombre: "Derecho Penal", descripcion: "Defensa en causas penales. Actuamos con rapidez desde el primer momento.", color: "#0a2540" },
    { nombre: "Derecho de Familia", descripcion: "Divorcios, régimen de visitas, alimentos y adopción.", color: "#1a4a6e" },
    { nombre: "Derecho Civil", descripcion: "Contratos, sucesiones y reclamos de daños y perjuicios.", color: "#2d6a8f" },
    { nombre: "Derecho Laboral", descripcion: "Despidos, accidentes de trabajo, trabajo no registrado.", color: "#3d8ab0" },
  ],

  // Testimonios — Si no hay reseñas de Google, la sección se oculta automáticamente
  testimonios: [], // Vacío = sección oculta. Se llena con reseñas reales de Google.
  ratingPromedio: null,
  totalOpiniones: 0,
  googleMapsUrl: null,

  // FAQ
  faqs: [
    { pregunta: "¿La primera consulta tiene costo?", respuesta: "No. La primera evaluación de tu caso es gratuita y confidencial." },
    { pregunta: "¿Cómo es el proceso de consulta?", respuesta: "Nos contactás por WhatsApp, evaluamos tu situación y te explicamos las opciones legales disponibles." },
    { pregunta: "¿Atienden casos urgentes?", respuesta: "Sí. Podés escribirnos fuera de horario y te respondemos a la brevedad." },
  ],

  // Diseño (colores del estudio)
  colores: {
    primario: "#0a2540",    // Navy oscuro (autoridad)
    acento: "#2dd4bf",      // Teal (acción)
    fondo: "#f8fafc",       // Blanco cálido
    texto: "#1e293b",       // Gris oscuro
  },

  // Formulario → WhatsApp directo (NO email)
  formulario: {
    destino: "whatsapp", // Siempre WhatsApp. Sin opción de email.
    mensajeTemplate: (nombre, telefono, caso) =>
      `Hola, soy ${nombre} (Tel: ${telefono}). Quiero consultar sobre: ${caso}`,
  },
};
```

**Flujo de personalización (para futuros clientes):**
1. Copiás la carpeta del proyecto (`git clone`)
2. Editás `estudio.js` con los datos del nuevo prospecto (5-10 min)
3. Cambiás la foto hero (si tienen foto real)
4. `npm run build` → deploy a Vercel (2 min)
5. Listo: web personalizada en < 30 minutos

> [!IMPORTANT]
> **Los campos `null` o vacíos (`[]`) ocultan la sección automáticamente.** Si un estudio no tiene testimonios, la sección no aparece. Si no tienen año de fundación, no se muestra. Cero datos inventados.

---

## 4. Diseño Visual

### Paleta de colores base (inspirada en Chumba)

| Token | Valor | Uso |
|:---|:---|:---|
| `--navy` | `#0a2540` | Fondo hero, textos fuertes, confianza |
| `--navy-deep` | `#061b2e` | Fondo hero más oscuro |
| `--teal` | `#2dd4bf` | CTAs, acentos, líneas decorativas |
| `--paper` | `#f8fafc` | Fondo claro de secciones |
| `--muted` | `#64748b` | Texto secundario |
| `--whatsapp` | `#25D366` | Botón WhatsApp (color oficial) |

### Tipografía

| Fuente | Uso |
|:---|:---|
| **Playfair Display** (700, 800) | Títulos h1, h2 — sensación de estatus y seriedad |
| **Inter** (400, 500, 600) | Body text, botones, labels — legibilidad perfecta |

### Elementos de diseño premium

- Grain texture sutil en hero (como Chumba)
- Chamfer corners en botones (esquina superior derecha cortada)
- Border-left de 3px en cards de testimonios (diferentes colores)
- Animaciones de entrada sutiles (fade + translate al hacer scroll)
- Botón flotante WhatsApp con pulse animation
- Mobile-first responsive (breakpoints: 640px, 768px, 1024px)

---

## 5. SEO & Schema Markup

Integrado desde el template base:

```json
// Schema LegalService (automático por datos de estudio.js)
{
  "@type": ["Organization", "LegalService"],
  "name": "Estudio García & Asociados",
  "description": "...",
  "telephone": "+5492215551234",
  "address": { ... },
  "areaServed": [{ "@type": "City", "name": "La Plata" }],
  "hasOfferCatalog": { ... áreas de práctica ... }
}

// Schema FAQPage (automático por datos de estudio.js)
{
  "@type": "FAQPage",
  "mainEntity": [ ... faqs ... ]
}
```

**Meta tags automáticos:**
- `<title>` optimizado: "[Especialidad] en [Zona] — [Nombre del Estudio]"
- `<meta description>` con copy de conversión
- OG tags completos para WhatsApp/redes sociales
- Canonical URL
- `lang="es-AR"`

---

## 6. Estructura de Archivos

```
estudio-template/
├── src/
│   ├── data/
│   │   └── estudio.js          ← ÚNICO ARCHIVO QUE SE EDITA
│   ├── components/
│   │   ├── TopBar.astro
│   │   ├── Navbar.astro
│   │   ├── Hero.astro
│   │   ├── StatsBar.astro
│   │   ├── AreasGrid.astro
│   │   ├── HowWeWork.astro
│   │   ├── AboutStudio.astro
│   │   ├── Testimonials.astro
│   │   ├── FAQ.astro
│   │   ├── ContactForm.astro
│   │   ├── Footer.astro
│   │   ├── WhatsAppFloat.astro
│   │   └── SchemaMarkup.astro
│   ├── layouts/
│   │   └── Layout.astro         ← Head + meta tags + fonts
│   ├── styles/
│   │   └── global.css           ← Design system completo
│   └── pages/
│       └── index.astro          ← Ensambla todos los componentes
├── public/
│   ├── images/
│   │   ├── hero-placeholder.jpg
│   │   └── studio-placeholder.jpg
│   └── favicon.svg
├── astro.config.mjs
└── package.json
```

---

## 7. Plan de Ejecución

| Paso | Qué | Tiempo estimado |
|:---|:---|:---|
| **1** | Inicializar proyecto Astro + configurar | 10 min |
| **2** | Crear `global.css` (design system, tokens, tipografía) | 30 min |
| **3** | Crear `estudio.js` (archivo de configuración) | 10 min |
| **4** | Construir componentes (Hero → Footer, de arriba a abajo) | 2-3 horas |
| **5** | Generar imágenes placeholder (hero + estudio) | 15 min |
| **6** | Integrar Schema markup + meta tags | 20 min |
| **7** | Animaciones y polish (scroll, hover, WhatsApp pulse) | 30 min |
| **8** | Testing: mobile, Lighthouse, accesibilidad | 20 min |
| **Total** | | **~4-5 horas** |

---

## Decisiones Resueltas

| Decisión | Resolución |
|:---|:---|
| **Modo visual** | Hero Dark (`--navy-deep`) + secciones Light (`--paper`). Estándar premium legal |
| **Target** | Dikè & Asociados (`abogadolaplata.com.ar`) directo. Sin template genérico |
| **Formulario** | WhatsApp directo vía `wa.me/`. Sin email. Sin intermediarios |
| **Métricas** | Solo datos verificables. Campos `null` ocultan la sección automáticamente |

---

## Decisión Pendiente: Nombre de Marca

> [!IMPORTANT]
> Falta definir el nombre de tu agencia para el footer ("Sitio por [tu marca]").

El nombre debe proyectar **infraestructura tecnológica y métricas**, no "agencia de diseño web". Propuestas:

| Nombre | Concepto | Dominio sugerido |
|:---|:---|:---|
| **Metric** | Datos, medición, ROI. Suena a herramienta, no a freelancer | metric.com.ar |
| **Baseline** | Línea base de rendimiento. Técnico pero accesible | baseline.com.ar |
| **Signal** | La señal que el cliente necesita. Limpio, moderno | signal.com.ar |
| **Converge** | Convergencia de canales hacia conversión | converge.com.ar |
| **Vertex** | Punto más alto. Asociación con tecnología Google | vertex.com.ar |
| **Pragma** | Pragmatismo. Soluciones que funcionan, sin humo | pragma.com.ar |

> Podés elegir cualquiera de estas, proponer la tuya, o decirme la dirección conceptual que querés y te genero más.

---

## Verificación

- [ ] Lighthouse score 90+ en las 4 categorías
- [ ] Mobile-first: funciona perfecto en iPhone SE (pantalla más chica común)
- [ ] WhatsApp CTA funcional con mensaje pre-formateado que abre `wa.me/`
- [ ] Schema markup valida en Google Rich Results Test
- [ ] Carga en < 2 segundos en 3G
- [ ] El archivo `estudio.js` se edita y el sitio refleja los cambios sin tocar código
- [ ] Secciones con datos `null` o `[]` se ocultan automáticamente (sin datos inventados)
