# PROMPT 3 — Landing de Kinesiología / Fisioterapia (Mendoza)

> Doble propósito: genera **la página de KORPO** (lead `noweb-korpo-centro-de-postura-y-rehabi-34aa53c6`,
> contactado por WhatsApp el 15/09, respondió) y queda como **template maestro del nicho** para las
> otras 81 clínicas de fisioterapia de Mendoza que están en cola.
> Pegar en Antigravity / Claude Code / Gemini con acceso a skills y 21st.dev.
> Los datos del prospecto ya están cargados: se relevaron de su ficha de Maps, su Instagram y su
> Facebook el 15/09/2026. Lo que quedó en `null` es lo que no existe públicamente — sale como
> placeholder visible, nunca inventado.

---

Actuás como Lead Product Designer + Frontend Engineer de una agencia de CRO de nivel élite,
especializada en salud ambulatoria en Argentina.

Tu tarea es construir la landing page de un centro de kinesiología y fisioterapia de Mendoza que
**hoy no tiene web**: existe solo como ficha de Google Maps. La página es el boceto que se le
muestra al dueño para que vea qué está perdiendo.

El estándar no es "mejor que nada". El estándar es que el dueño la abra en el celular y entienda,
sin que se lo expliquen, que los pacientes que hoy se le van al de al lado se le van por no tener
esto.

---

## DATOS DEL PROSPECTO (relevados, no inventados)

```js
const PROSPECTO = {
  nombre_legal:  "KORPO Centro de Postura y Rehabilitación Deportiva",
  nombre_corto:  "KORPO",
  rating:        4.8,
  resenas:       122,          // fuente: Google Maps, 15/09/2026
  ciudad:        "Ciudad de Mendoza",
  direccion:     "Agustín Alvarez 446, M5500, Ciudad de Mendoza",
  // ⚠ CONFLICTO SIN RESOLVER: su Facebook dice "Salta 474 - Ciudad, Mendoza".
  // Maps está actualizado (el dueño responde reseñas hace un mes), Facebook no publica desde 2021.
  // Se usa la de Maps y se marca como "a confirmar" en el checklist final.

  telefonos: {
    fisioterapia: "+54 9 263 465-8148",   // el que figura en Maps y por el que se lo contactó
    rpg:          "+54 9 261 507-0347",
    atm:          "+54 9 261 209-3496",
  },
  whatsapp_principal: "5492634658148",     // para los links wa.me

  instagram:  "@korpo_rpg_fisio",          // 1.401 seguidores — hoy es su web de hecho
  facebook:   "korpocentrodepostura",      // desactualizado desde 2021
  email:      "licstellaruiz@gmail.com",

  horarios:   null,                        // solo se conoce "cierra 19:30". [COMPLETAR]

  tratamientos: [
    "RPG — Reeducación Postural Global",
    "Kinesiología y fisioterapia",
    "Rehabilitación deportiva",
    "SGA — Stretching Global Activo",
    "ATM — disfunción temporomandibular",
  ],

  equipo: [                                 // nombres mencionados por pacientes en reseñas reales
    { nombre: "Juan Cruz",        matricula: null },
    { nombre: "Gennaro",          matricula: null },
    { nombre: "Claudia Lavarda",  matricula: null },
    { nombre: "Cecilia Basualdo", matricula: null },
    { nombre: "Lic. Stella Ruiz", matricula: null, nota: "posible dirección" },
  ],

  diferenciador: "Sesiones de una hora completa, cuando otros centros dan menos.",
  // ↑ NO es marketing nuestro: lo dice una paciente, textual, en una reseña de hace un mes.
  // Es el argumento más fuerte que tienen y no está escrito en ningún lado propio.

  obras_sociales: null,                    // [COMPLETAR] — no figura en ninguna fuente pública.

  resenas_texto: [                         // TEXTUALES de Google Maps. No reescribir ni corregir.
    { autor: "Melisa Nieto", fecha: "hace un mes",
      texto: "Recomiendo Korpo. Realizan una hora de sesión a diferencia de otros centros, cuando es necesario realizan masajes para aliviar dolor. Juan Cruz y Gennaro siempre atentos a la evolución. Escuchan al paciente. Gracias chicos!" },
    { autor: "Elisabeth Paura", fecha: "hace 3 meses",
      texto: "Es mi centro de rehabilitación de referencia, excelentes profesionales, calidez y un lugar muy cómodo. Felicitaciones!!!" },
    { autor: "mariela lana", fecha: "hace 2 meses",
      texto: "Son unos genios!! Me atiendo con Claudia Lavarda y c Juan Cruz y excelentes los 2, super recomendables!!" },
    { autor: "—", fecha: "—", texto: "Excelente atención de parte de la doctora Cecilia Basualdo, muy recomendable." },
  ],
};
```

**Regla dura:** todo campo en `null` se renderiza como un bloque visualmente marcado
(`[COMPLETAR: obras sociales]`, fondo ámbar, borde punteado) y queda listado en el checklist final.
Nunca se rellena con un valor verosímil. Una obra social inventada le pone un paciente enojado en
la puerta al cliente; una matrícula inventada es directamente un problema legal. Ese es el error
que quema la venta en el primer minuto.

---

## Los tres hallazgos que definen esta página

No son observaciones de color: son el argumento de venta y tienen que verse resueltos en el diseño.

**1. Tres teléfonos distintos para tres servicios.** Su Instagram —que es su web de hecho— pide
que el paciente elija entre `263 465-8148` (fisioterapia), `261 507-0347` (RPG) y `261 209-3496`
(ATM) *antes* de saber cuál de los tres necesita. Nadie que llega con dolor de espalda sabe si
eso es RPG o kinesiología. El que duda, no escribe.

→ La página resuelve esto con **un solo punto de entrada**: un CTA de WhatsApp, y el ruteo al
número correcto lo hace la página según el tratamiento que el paciente elige, no el paciente
según el número.

**2. La dirección no coincide entre plataformas.** Maps dice Agustín Alvarez 446, Facebook dice
Salta 474. Un paciente que googlea puede terminar en la puerta equivocada.

→ La página es la **fuente única de verdad**: una dirección, un mapa, un "cómo llegar". Es
exactamente lo que una web hace y una ficha de Maps no.

**3. Tienen el mejor argumento del rubro y no lo usan.** "Realizan una hora de sesión a diferencia
de otros centros" está escrito por una paciente en una reseña, no por ellos en ningún lado. En un
rubro donde la queja estándar es la sesión de 20 minutos con el aparatito, eso es *la* ventaja
competitiva.

→ Va en el hero, dicho como propio pero verificable: la reseña que lo respalda aparece más abajo,
textual y con nombre.

---

## Orden de ejecución (obligatorio, no lo saltees)

1. Leé las skills antes de escribir una línea de código: `ui-ux-pro-max`, `tailwind-design-system`,
   `page-cro`, `wcag-accessibility`.
2. Consultá 21st.dev y elegí explícitamente 4-6 componentes reales (nombrálos y citá su origen).
   Priorizá: navbar flotante con blur, bento grid, cards con spotlight, accordion animado,
   marquee de reseñas, badge de rating.
3. Escribí primero el layout de 375px completo. Recién cuando ese esté cerrado, subí a tablet y
   desktop.
4. Al final, autoauditoría contra el "Criterio de éxito".

---

## La psicología de este nicho (esto define el copy — no lo inventes genérico)

El paciente de kinesiología **no elige una clínica: resuelve un trámite con dolor encima.** Llega
en uno de tres estados, y los tres conviven en el mismo scroll:

- **Derivado / post-quirúrgico** — tiene una orden médica en la mano. La decisión clínica ya la
  tomó el traumatólogo. Él solo busca dónde, y busca rápido porque la recuperación tiene ventana.
  No compara calidad: compara **cobertura y disponibilidad**.
- **Dolor crónico** — cervical, lumbar, contractura de meses. Viene de probar otra cosa que no le
  funcionó. Necesita creer que acá sí. Compara **especialidad concreta y prueba social**.
- **Deportista lesionado** — tiene una fecha: volver a jugar. Compara **equipamiento y si trabajan
  con deportistas**.

### Las cuatro preguntas que decide antes de escribir

En este orden, y todas se contestan en la primera pantalla y media:

1. **¿Me cubre mi obra social? ¿Y si no, cuánto sale particular?**
2. **¿Cuándo me pueden atender?** (esta semana, no "a la brevedad")
3. **¿Dónde quedan y cómo llego?**
4. **¿Quién me atiende y qué matrícula tiene?**

Si la página no contesta la 1, no hay llamada. Es el dato más buscado y el que el 90% de las webs
de salud de Argentina esconde en el footer o directamente no pone. Acá va arriba, en texto grande,
legible sin scrollear.

---

## Estructura obligatoria

Cada sección lleva su función CRO declarada en un comentario del código.

1. **Navbar flotante** con blur al scrollear. CTA "Pedir turno" siempre visible + teléfono
   clickeable en mobile. En ≤375px el CTA es un botón fijo abajo, no un ítem de menú.
2. **Hero** — resuelve las 4 preguntas de arriba en 3 segundos:
   - H1 con el servicio y el lugar: *"Kinesiología y rehabilitación en Ciudad de Mendoza"*.
   - Subtítulo con el diferenciador real: **la sesión de una hora completa**. Es lo único que los
     separa del resto y hoy no lo dice nadie más que sus pacientes.
   - Badge de rating real: **4,8 ★ · 122 reseñas en Google**. Es el activo que hoy tienen preso en
     Maps; acá es lo primero que se ve.
   - Línea de cobertura visible sin scroll: *"Atendemos [obras sociales] y particular"*.
   - CTA primario: **un solo botón de WhatsApp**, con mensaje precargado
     (`wa.me/5492634658148?text=Hola,%20quiero%20sacar%20un%20turno`).
   - CTA secundario: llamar.
3. **Franja de obras sociales** — inmediatamente después del hero, nombres en texto legible (no
   logos pixelados), y una línea honesta para el caso particular: valor de sesión o "consultanos".
   Es la sección que nadie construye y todos necesitan.
4. **Estado en vivo**: abierto/cerrado calculado contra los horarios reales + "próximo turno
   disponible" si el dato existe.
5. **Tratamientos en bento grid** — no una lista plana. Exactamente los cinco que hacen (RPG,
   kinesiología y fisioterapia, rehabilitación deportiva, SGA, ATM), sin agregar ninguno. Cada uno
   con **dos cosas**:
   - una línea que traduzca la sigla al problema del paciente ("RPG: si te duele la espalda todos
     los días y ya probaste todo", no "Reeducación Postural Global");
   - su propio botón de WhatsApp, que rutea al número correcto de `PROSPECTO.telefonos` de forma
     transparente. **El paciente elige su problema; la página elige el teléfono.** Esa inversión
     es el núcleo de lo que esta web resuelve.
6. **El espacio y el equipamiento** — en kinesiología la prueba es física: el gimnasio, las
   camillas, los aparatos. Placeholders de proporción fija, marcados como reemplazables por fotos
   reales del lugar.
7. **Equipo con matrícula** — nombre, especialidad y **MP ####**. La matrícula visible es señal de
   seriedad en salud y además es lo que exige la normativa de publicidad sanitaria.
8. **Prueba social real** — las reseñas de Google textuales, con nombre de pila y fecha, en cards
   con marquee. Arriba, el agregado: 4,8 sobre 122. Link a la ficha de Maps para verificar.
9. **Cómo es la primera sesión** — 3 pasos con línea de progreso al scrollear: *mandás la orden
   por WhatsApp → te damos el turno → primera sesión de evaluación de X minutos*. Esta sección
   elimina la fricción más grande del rubro, que es no saber qué pasa cuando llegás.
10. **FAQ en accordion** con las objeciones reales, no genéricas: ¿necesito orden médica?,
    ¿cuántas sesiones voy a necesitar?, ¿qué obras sociales toman?, ¿hay coseguro?, ¿cuánto dura
    la sesión?, ¿atienden sin obra social?, ¿hay dónde estacionar?.
11. **CTA final** de ancho completo: WhatsApp con mensaje precargado. Si hay formulario, máximo
    3 campos (nombre, teléfono, motivo). Ninguno más.
12. **Footer** con mapa embebido, dirección, horarios completos, teléfono y redes.

---

## Reglas de honestidad (esto no es un detalle, es el producto)

- **Cero testimonios inventados.** Las reseñas son las de Google, textuales. Si no están cargadas,
  la sección sale con placeholder marcado, no con testimonios verosímiles. Un testimonio falso lo
  detecta el dueño en dos segundos —conoce a sus pacientes— y ahí se terminó la conversación.
- **Cero promesas clínicas.** Nada de "curamos", "recuperación garantizada", "sin dolor",
  porcentajes de éxito ni "los mejores de Mendoza". Publicidad sanitaria y, además, es el registro
  que hace desconfiar.
- **Cero obras sociales inventadas.** Ver la regla dura de arriba.
- **Cero fotos que simulen ser el lugar.** Placeholders neutros y marcados. Una foto de stock de
  otra clínica presentada como propia es la única forma de que un boceto gratis se vuelva un
  problema.
- **Cero métricas infladas.** "15 años de experiencia" solo si el dato está en `PROSPECTO`.

---

## Reglas de diseño (no negociables)

- **Mobile-first real, 375px primero.** Sin desborde horizontal en ningún breakpoint. Este es
  literalmente el problema que le vendemos al prospecto: si el boceto lo tiene, perdimos el
  argumento entero.
- **Tipografía para la edad del paciente.** Buena parte del público de kinesiología pasa los 50:
  base 17-18px, interlineado 1.6, contraste AA+ real. Nada de gris claro sobre blanco.
- **Áreas táctiles de 48px mínimo.** Se navega con dolor, a veces con una sola mano.
- **Sistema de diseño explícito** al tope: escala tipográfica con `clamp`, paleta en tokens CSS,
  espaciado 4/8px, radios y sombras consistentes.
- **Paleta**: azul o verde clínico como primario pero cálido, un acento para los CTA, neutros
  tibios de fondo. Evitá el blanco hospital estéril y el azul corporativo genérico. Dejá
  documentada una paleta alternativa por si el prospecto tiene marca propia.
- **Dark mode** con tokens redefinidos, no invertidos a mano.
- **Accesibilidad**: focus visible, `prefers-reduced-motion` respetado en todas las animaciones,
  alt en todas las imágenes, jerarquía de headings correcta.

## Animaciones

Entrada por sección con stagger al scrollear, hover con spotlight en las cards de tratamiento,
contador animado en el rating, transición del navbar al pasar el hero. Todo por debajo de 400ms.
Si una animación se nota como "animación", está mal calibrada.

## Lo que NO va

Carrusel de stock arriba de todo. "Bienvenidos a nuestra clínica". "Misión, visión y valores".
Formulario de 8 campos. Chatbot. Pop-up de newsletter. Lorem ipsum. Iconos de redes que no usan.
Un mapa que ocupa una pantalla entera. Cualquier texto que no conteste una de las cuatro preguntas.

---

## Performance

- Un solo archivo HTML autocontenido: CSS y JS inline, sin dependencias externas salvo Google Fonts.
- **Menos de 500 KB en total** y por debajo de 2 segundos en 4G. Se lo vamos a mandar por WhatsApp
  a alguien que lo va a abrir con datos móviles, y el argumento de venta incluye la velocidad.
- Tiene que abrir bien con doble clic, sin servidor.

---

## Entregable

El archivo HTML, más un bloque comentado al final con:

- Qué componentes de 21st.dev usaste y por qué.
- **Lista de campos en `null`** que quedaron como placeholder, para completar antes de mostrarla.
- **Checklist de personalización** para adaptarla a otra clínica del nicho, en orden y con tiempo
  estimado.
- 3 hipótesis de test A/B para la siguiente iteración.

Todo el contenido de negocio sale de `PROSPECTO` / `CONFIG`. **Ningún texto del cliente
hardcodeado en el marcado**, y los colores alimentan tokens CSS, para que cambiar el primario
reacomode la paleta entera. El layout tiene que aguantar los extremos: un nombre corto y uno
larguísimo, 4 tratamientos u 9, 2 kinesiólogos o 6.

---

## Criterio de éxito

Tres pruebas, las tres obligatorias:

1. **El dueño** la abre en el celular y en 3 segundos ve su nombre, su 4,8 con 122 reseñas y un
   botón de WhatsApp que escribe de verdad a su número.
2. **Un paciente con orden médica** averigua si le cubren la obra social sin scrollear más de una
   pantalla, y saca el turno en dos toques.
3. **Vos** la convertís en la landing de otra clínica de Mendoza editando solo `PROSPECTO`, en
   menos de diez minutos, sin tocar el marcado.

Si falla la 1, no vende. Si falla la 2, no sirve. Si falla la 3, no escala.
