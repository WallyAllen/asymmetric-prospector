# PROMPT 1 — Template Maestro de Landing Page para Veterinarias

> Plantilla por nicho: se construye **una sola vez**, se personaliza por prospecto en minutos.
> Pegar en Antigravity / Claude Code / Gemini con acceso a skills y 21st.dev.
> No hay variables que reemplazar: el objetivo es el template genérico.

---

Actuás como Lead Product Designer + Frontend Engineer de una agencia de CRO de nivel élite.

Tu tarea es construir el **template maestro del nicho veterinario**: una landing page de demostración para una veterinaria ficticia y genérica, diseñada para ser mostrada a decenas de clínicas distintas y personalizada para cada una en menos de diez minutos.

No estás diseñando para un cliente concreto. Estás diseñando el activo reutilizable que va a abrir todas las conversaciones del nicho.

## La marca ficticia
Usá una veterinaria inventada y neutra: **Veterinaria Aurora** — clínica de barrio, mediana, con consultorio, cirugía, peluquería y guardia. Sin ciudad definida (usá "tu ciudad" o un genérico como "Barrio Norte").

Que se sienta real y cálida, pero que no imite ni evoque a ninguna clínica existente. Nada de logos, nombres o textos tomados de veterinarias reales.

## Orden de ejecución (obligatorio, no lo saltees)
1. Leé las skills antes de escribir una línea de código: `ui-ux-pro-max`, `tailwind-design-system`, `page-cro`, `wcag-accessibility`.
2. Consultá 21st.dev y elegí explícitamente 4-6 componentes reales (nombrálos y citá su origen). Priorizá: hero con gradiente animado, bento grid, marquee de testimonios, tarjetas con spotlight/hover 3D, accordion animado, navbar flotante.
3. Recién entonces escribí el código.

## Requisito central: personalización en minutos

Al tope del archivo, un único bloque de configuración que concentre **todo** lo que cambia entre una veterinaria y otra:

```js
const CONFIG = {
  marca:      { nombre: "Veterinaria Aurora", tagline: "...", anios: 15 },
  contacto:   { telefono: "...", whatsapp: "...", direccion: "...", ciudad: "..." },
  horarios:   { /* por día, con flag de guardia 24h */ },
  servicios:  [ /* 6 items: título, descripción, ícono */ ],
  equipo:     [ /* 3-4 personas: nombre, rol, especialidad, foto */ ],
  resenas:    [ /* PLACEHOLDER — se reemplazan por reseñas reales de Google del prospecto */ ],
  faq:        [ /* 5 preguntas */ ],
  marca_color:{ primario: "...", acento: "...", neutro: "..." }
};
```

Reglas de esta capa:
- **Ningún texto de negocio hardcodeado en el HTML.** Todo sale de `CONFIG`.
- Los colores del bloque alimentan tokens CSS, para que cambiar el primario reacomode la paleta entera sin tocar nada más.
- El diseño tiene que aguantar variación: un nombre corto y uno largo, 4 servicios o 8, 2 miembros del equipo o 6. Probá los extremos antes de dar por cerrado el layout.
- Las reseñas del template son **placeholder explícito**, marcadas como tales en un comentario. Cuando se personaliza para un prospecto se cargan sus reseñas reales de Google — nunca testimonios inventados presentados como genuinos. Es la diferencia entre una demo y un fraude, y es lo primero que un cliente detecta.

## Psicología del nicho (esto define el copy, no lo inventes genérico)
El cliente de una veterinaria no compra un servicio: delega el miedo. Tres estados mentales:
- **Urgencia** ("mi perro está mal AHORA") → teléfono y horario visibles sin scroll.
- **Rutina** (vacunas, control) → necesita ver que sacar turno es fácil.
- **Confianza** (cirugía, internación) → necesita caras, equipamiento y prueba social.

La landing resuelve los tres en el mismo scroll, en ese orden. El copy del template tiene que ser lo bastante concreto para emocionar y lo bastante neutro para servirle a cualquier clínica.

## Estructura obligatoria (cada sección con su función CRO declarada en un comentario del código)
1. **Navbar flotante** con blur al scrollear + CTA "Sacar turno" siempre visible + teléfono clickeable en mobile.
2. **Hero**: promesa en una línea sobre qué resuelven y para quién, subtítulo con la ciudad, CTA primario (turno) y secundario (WhatsApp urgencias). Fondo con gradiente animado sutil. Badge de confianza (años, pacientes). Debe responder "qué hacen y cómo los contacto" en 3 segundos.
3. **Barra de urgencia**: horarios de hoy + estado abierto/cerrado calculado en vivo + guardia 24h.
4. **Servicios en bento grid** con íconos y micro-interacciones al hover. Nada de listas planas.
5. **Prueba social**: reseñas en cards con marquee infinito + rating agregado.
6. **Equipo**: fotos con hover que revela especialidad. Es la sección que más mueve la aguja en salud.
7. **Cómo funciona**: 3 pasos con línea de progreso animada al scrollear.
8. **FAQ** en accordion animado, con las objeciones reales del rubro (precios, obras sociales, urgencias, primera visita).
9. **CTA final** de ancho completo con formulario corto (nombre, teléfono, motivo) o botón a WhatsApp.
10. **Footer** con mapa, dirección, horarios y redes.

## Reglas de diseño (no negociables)
- **Mobile-first real.** Diseñá el breakpoint de 375px primero y verificá que nada desborde horizontalmente. Este es el problema exacto que le vendemos al prospecto: si el mockup lo tiene, perdimos el argumento entero.
- **Sistema de diseño explícito** al tope: escala tipográfica con `clamp`, paleta en tokens CSS, escala de espaciado 4/8px, radios y sombras consistentes.
- **Paleta por defecto**: verde salvia o azul confianza como primario, un acento cálido para los CTA, neutros cálidos de fondo. Nada de azul corporativo genérico. Documentá una paleta alternativa por si el prospecto tiene marca propia.
- **Tipografía**: máximo 2 familias de Google Fonts, con stack de fallback real.
- **Dark mode** con tokens redefinidos, no invertidos a mano.
- **Accesibilidad**: contraste AA mínimo, focus visible, `prefers-reduced-motion` respetado en todas las animaciones, alt en todas las imágenes.
- **Imágenes**: placeholders de alta calidad, neutros y reemplazables, con proporción fija para que el layout no salte al cambiarlas.

## Animaciones (el "efecto wow" que justifica el precio)
- Entrada por sección con stagger al scrollear (IntersectionObserver o Framer Motion).
- Hover con spotlight o tilt en las tarjetas de servicio.
- Contadores animados en las métricas de confianza.
- Transición suave del navbar al pasar el hero.
- Todo por debajo de 400ms. Si una animación se nota como "animación", está mal calibrada.

## Entregable
Un único archivo HTML autocontenido: CSS y JS inline, sin dependencias externas salvo Google Fonts y CDNs permitidos. Tiene que abrir bien con doble clic y verse impecable en un iPhone.

Al final, un bloque comentado con:
- Qué componentes de 21st.dev usaste y por qué.
- **Checklist de personalización**: los pasos exactos para adaptarlo a un prospecto nuevo, en orden, con tiempo estimado.
- Qué campos de `CONFIG` son obligatorios y cuáles opcionales.
- 3 hipótesis de test A/B para la siguiente iteración.

## Criterio de éxito
Dos pruebas, ambas obligatorias:
1. Un dueño de veterinaria lo abre en el celular y siente que su web actual quedó atrás.
2. Vos podés convertirlo en la landing de una clínica específica editando solo `CONFIG`, en menos de diez minutos, sin tocar el marcado.

Si falla la primera, no vende. Si falla la segunda, no escala.
