# Brief Completo: Dikè & Asociados — Datos para el Mockup

> **Este archivo contiene todo lo que el agente del Antigravity IDE necesita para construir la landing page.**
> Copiá este archivo al chat del IDE o usalo como referencia.

---

## 1. Datos Verificados del Estudio

### Identidad
| Campo | Dato | Fuente |
|:---|:---|:---|
| **Nombre legal** | Estudio Jurídico Dikè & Asociados | Web + directorios |
| **Titular** | Dr. Gabriel Darío Oviedo | Legaltica, directorios legales |
| **Dominio principal** | abogadolaplata.com.ar | Verificado |
| **Dominio secundario** | art-laplata.com.ar | Verificado (dedicado a ART) |
| **Email** | estudiodike@gmail.com | Verificado |

### Contacto
| Campo | Dato |
|:---|:---|
| **Teléfono fijo 1** | 0221 452-0745 |
| **Teléfono fijo 2** | 0221 417-2159 |
| **WhatsApp** | +54 9 221 590-1773 |
| **WhatsApp (formato wa.me)** | `https://wa.me/5492215901773` |

### Ubicación
| Campo | Dato |
|:---|:---|
| **Dirección** | Calle 57 N° 1343 (entre 21 y 22) |
| **Ciudad** | La Plata |
| **Provincia** | Buenos Aires |
| **Código Postal** | B1900BOA |
| **Horario** | Lunes a Viernes, 18:00 a 20:00 hs (con turno previo) |

### Áreas de Práctica (verificadas en múltiples fuentes)

| # | Área | Subespecialidades |
|:---|:---|:---|
| 1 | **Derecho de Familia** | Divorcios, separaciones, tenencia, régimen de visitas, alimentos, adopción |
| 2 | **Derecho Laboral** | Despidos, indemnizaciones, accidentes de trabajo (ART), trabajo no registrado |
| 3 | **Derecho Penal** | Defensa penal, excarcelaciones, eximición de prisión |
| 4 | **Sucesiones** | Sucesiones, testamentos, declaratorias de herederos |
| 5 | **Responsabilidad Civil** | Daños y perjuicios, accidentes de tránsito |
| 6 | **Contratos** | Contratos en general, desalojos |

> [!NOTE]
> El estudio se posiciona como **integral** — atiende tanto particulares como empresas.

### Reputación Online
| Plataforma | Calificación | Notas |
|:---|:---|:---|
| **Google Maps** | ~4.4 - 5.0 estrellas | Opiniones positivas sobre trato personalizado y profesionalismo |
| **Legaltica** | Alta valoración | Destacan calidad de atención y capacidad de resolución |

---

## 2. Diagnóstico Técnico de la Web Actual

> [!CAUTION]
> **Este diagnóstico es el argumento de venta.** Muestra por qué necesitan una web nueva.

| Problema | Gravedad | Impacto en negocio |
|:---|:---|:---|
| `<title></title>` vacío | 🔴 CRÍTICO | Google no puede indexar ni mostrar el sitio. Dominio premium invisible |
| No indexado en Google | 🔴 CRÍTICO | `site:abogadolaplata.com.ar` devuelve 0 resultados |
| Sin meta description | 🔴 ALTO | Google muestra texto aleatorio en resultados |
| Sin WhatsApp visible | 🔴 ALTO | El canal #1 de conversión en Argentina no está expuesto |
| WordPress 6.2.10 | 🟡 MEDIO | Versión desactualizada, vulnerabilidades |
| Theme Astra sin personalizar | 🟡 MEDIO | Colores genéricos, menú rojo, CSS masivo |
| Colores actuales | ℹ️ INFO | Amarillo `#ffd936`, dorado `#dab200`, verde oliva `#536942` |
| Fuentes actuales | ℹ️ INFO | DM Sans + Forum |

---

## 3. Archivo `estudio.js` Pre-llenado

```javascript
// src/data/estudio.js — DATOS REALES DE DIKÈ & ASOCIADOS

export const estudio = {
  // ─── Identidad ───
  nombre: "Dikè & Asociados",
  titular: "Dr. Gabriel Darío Oviedo",
  especialidad: "Derecho Penal y Familia",
  slogan: "Defensa estratégica para resolver problemas legales complejos.", // Cambiado: Adiós al "integral" genérico.
  descripcion: "Estudio jurídico en La Plata. Actuamos con celeridad en urgencias penales y conflictos de familia. Atención directa por los titulares del estudio.",

  // ─── Ubicación ───
  zona: "La Plata",
  direccion: "Calle 57 N° 1343 (entre 21 y 22)",
  ciudad: "La Plata",
  provincia: "Buenos Aires",
  codigoPostal: "B1900BOA",
  horario: "Lunes a Viernes, 18:00 a 20:00 hs",
  requiereTurno: true,

  // ─── Contacto (SIN EMAIL como canal de conversión) ───
  telefono: "+542214520745",
  telefonoDisplay: "0221 452-0745",
  telefonoAlt: "+542214172159",
  telefonoAltDisplay: "0221 417-2159",
  whatsapp: "+5492215901773",
  whatsappDisplay: "221 590-1773",
  email: "estudiodike@gmail.com", // Solo para Schema markup, NO como CTA visible

  // ─── Sistema de WhatsApp Contextual ───
  // Diferentes mensajes según dónde haga clic el usuario
  mensajesWhatsapp: {
    hero: "Hola Dr. Oviedo. Me comunico desde su página web. Necesito hacer una consulta legal.",
    area: (nombreArea) => `Hola Dr. Oviedo. Estuve viendo su web y necesito hacer una consulta sobre ${nombreArea}.`,
    formulario: (nombre, telefono, caso) => `Hola, soy ${nombre} (Tel: ${telefono}). Quiero consultar sobre: ${caso}`
  },
  whatsappUrl: (mensaje) => `https://wa.me/5492215901773?text=${encodeURIComponent(mensaje)}`,

  // ─── Credenciales (SOLO datos verificables) ───
  matricula: null, // No verificada — se agrega cuando se consiga
  fundacion: null, // No verificado
  // NO hay casosResueltos ni métricas inventadas

  // ─── Áreas de Práctica ───
  areas: [
    {
      nombre: "Derecho de Familia",
      descripcion: "Divorcios, separaciones, régimen de visitas, alimentos y adopción. Te acompañamos en cada paso del proceso.",
      icono: "family",
    },
    {
      nombre: "Derecho Laboral",
      descripcion: "Despidos, indemnizaciones, accidentes de trabajo y trabajo no registrado. Evaluamos tu caso y te decimos qué te corresponde.",
      icono: "laboral",
    },
    {
      nombre: "Derecho Penal",
      descripcion: "Defensa penal, excarcelaciones y eximición de prisión. Actuamos con rapidez desde el primer momento.",
      icono: "penal",
    },
    {
      nombre: "Sucesiones",
      descripcion: "Sucesiones, testamentos y declaratorias de herederos. Simplificamos un proceso que parece complejo.",
      icono: "sucesiones",
    },
    {
      nombre: "Daños y Perjuicios",
      descripcion: "Accidentes de tránsito y responsabilidad civil. Reclamamos la indemnización que te corresponde.",
      icono: "danos",
    },
    {
      nombre: "Contratos y Desalojos",
      descripcion: "Redacción, revisión de contratos y procesos de desalojo para propietarios e inquilinos.",
      icono: "contratos",
    },
  ],

  // ─── Testimonios (vacío = sección oculta) ───
  testimonios: [],
  ratingPromedio: null,
  totalOpiniones: 0,
  googleMapsUrl: null,

  // ─── FAQ ───
  faqs: [
    {
      pregunta: "¿La primera consulta tiene costo?",
      respuesta: "Contactanos por WhatsApp o teléfono para coordinar una consulta. Te explicamos tu situación legal sin compromiso.",
    },
    {
      pregunta: "¿Necesito turno previo?",
      respuesta: "Sí, atendemos con turno previo de lunes a viernes. Podés coordinar tu turno por WhatsApp o por teléfono.",
    },
    {
      pregunta: "¿Qué áreas del derecho manejan?",
      respuesta: "Brindamos asesoramiento integral: familia, laboral, penal, sucesiones, daños y perjuicios, contratos y desalojos.",
    },
    {
      pregunta: "¿Atienden casos de ART y accidentes laborales?",
      respuesta: "Sí. Evaluamos tu incapacidad, revisamos el porcentaje otorgado por la ART y reclamamos lo que te corresponde.",
    },
  ],

  // ─── Diseño ───
  colores: {
    primario: "#0a2540",    // Navy oscuro (autoridad)
    acento: "#2dd4bf",      // Teal (acción)
    fondo: "#f8fafc",       // Blanco cálido
    texto: "#1e293b",       // Gris oscuro
  },

  // ─── Formulario → WhatsApp Directo ───
  formulario: {
    destino: "whatsapp",
    campos: ["nombre", "telefono", "caso"],
    // La lógica de ruteo la maneja 'mensajesWhatsapp.formulario'
  },

  // ─── SEO ───
  seo: {
    title: "Abogados en La Plata — Dikè & Asociados | Familia, Laboral, Penal",
    description: "Estudio jurídico integral en La Plata. Derecho de familia, laboral, penal, sucesiones y más. Consultá tu caso por WhatsApp: 221 590-1773.",
    canonical: "https://abogadolaplata.com.ar",
    locale: "es_AR",
  },
};
```

---

## 4. Instrucciones para el Agente del IDE

### ✅ Lo que tiene que hacer:
1. Inicializar proyecto **Astro** en el workspace
2. Copiar el `estudio.js` de arriba en `src/data/estudio.js`
3. Seguir la estructura de secciones del plan: TopBar → Navbar → Hero → StatsBar → AreasGrid → HowWeWork → AboutStudio → Testimonials (condicional) → FAQ → ContactForm → Footer → WhatsAppFloat
4. **Diseño Visual & Contraste:** El Hero DEBE tener una capa de fondo negra con 70% de opacidad (`rgba(0,0,0,0.7)`) sobre la imagen para que el texto blanco tenga contraste perfecto.
5. **Embudos de Conversión (CRÍTICO):** Solo puede haber **UN ÚNICO botón primario en el Hero** que dirija a WhatsApp. ELIMINAR botones secundarios del navbar. ELIMINAR la sobrecarga de CTAs. Solo Hero CTA + Botón Flotante.
6. **Sistema WhatsApp Contextual:** Implementar la lógica del objeto `mensajesWhatsapp`. Los botones de cada tarjeta de "Área de Práctica" deben enviar el mensaje específico de esa área. El formulario arma el mensaje completo.
7. **Tipografía:** Inter (body) + Playfair Display (títulos) — Google Fonts
8. **Formulario:** Abre WhatsApp directamente con `wa.me/` — NO envía email
9. **Secciones condicionales:** Si `testimonios` es `[]` o `matricula` es `null`, la sección no se renderiza
10. **Botón flotante WhatsApp:** Siempre visible, asegurando que no choque con colores del footer.
11. **Schema markup:** LegalService + FAQPage automático desde `estudio.js`
12. **Generar imágenes:** con `generate_image` para hero y foto del estudio (interior jurídico elegante en La Plata)
11. **Benchmark visual:** Estudiar `chumbayasociados.com` como referencia de diseño premium

### ❌ Lo que NO tiene que hacer:
- No usar TailwindCSS — Vanilla CSS con custom properties
- No inventar datos que no estén en este archivo
- No poner email como canal de contacto visible
- No poner métricas genéricas ("500+ casos")
- No usar los colores actuales del sitio (amarillo/verde oliva del Astra)

---

## 5. Datos que FALTAN

| Dato | Cómo conseguirlo |
|:---|:---|
| Matrícula CALP | Preguntar al Dr. Oviedo |
| Año de fundación | Preguntar directamente |
| Foto real del estudio | Sacar en la reunión presencial |
| Reseñas de Google Maps | Buscar el CID en Google Maps |
| Nombre de tu marca/agencia | Para el footer: "Sitio por [marca]" |

> [!IMPORTANT]
> Usar `generate_image` para crear placeholders profesionales hasta tener fotos reales.
