// src/data/estudio.js — DATOS REALES DE DIKÈ & ASOCIADOS

export const estudio = {
  // ─── Identidad ───
  nombre: "Dikè & Asociados",
  titular: "Dr. Gabriel Darío Oviedo",
  especialidad: "Derecho Penal y Familia",
  slogan: "Defensa estratégica para resolver problemas legales complejos.",
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
  
  mensajesWhatsapp: {
    hero: "Hola Dr. Oviedo. Me comunico desde su página web. Necesito hacer una consulta legal.",
    area: (nombreArea) => `Hola Dr. Oviedo. Estuve viendo su web y necesito hacer una consulta sobre ${nombreArea}.`,
    formulario: (nombre, telefono, caso) => `Hola, soy ${nombre} (Tel: ${telefono}). Quiero consultar sobre: ${caso}`
  },
  whatsappUrl: (mensaje) => `https://wa.me/5492215901773?text=${encodeURIComponent(mensaje)}`,
  
  email: "estudiodike@gmail.com", // Solo para Schema markup, NO como CTA visible

  // ─── Credenciales (SOLO datos verificables) ───
  matricula: null, // No verificada — se agrega cuando se consiga
  fundacion: null, // No verificado

  stats: [
    { valor: "+15", etiqueta: "Años de Trayectoria" },
    { valor: "Directa", etiqueta: "Atención por Titulares" },
    { valor: "CALP", etiqueta: "Abogados Matriculados" }
  ],

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
    mensajeTemplate: (nombre, telefono, caso) =>
      `Hola, soy ${nombre} (Tel: ${telefono}). Quiero consultar sobre: ${caso}`,
    whatsappUrl: (mensaje) =>
      `https://wa.me/5492215901773?text=${encodeURIComponent(mensaje)}`,
  },

  // ─── SEO ───
  seo: {
    title: "Abogados en La Plata — Dikè & Asociados | Familia, Laboral, Penal",
    description: "Estudio jurídico integral en La Plata. Derecho de familia, laboral, penal, sucesiones y más. Consultá tu caso por WhatsApp: 221 590-1773.",
    canonical: "https://abogadolaplata.com.ar",
    locale: "es_AR",
  },
};
