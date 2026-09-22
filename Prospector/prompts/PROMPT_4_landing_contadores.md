# PROMPT 4 — Landing de Estudio Contable / Monotributistas (La Plata)

> **Template maestro de la variante A del nicho contadores** (los que atienden monotributistas,
> autónomos y gente que recién arranca a facturar). Genera la landing de un estudio contable que
> hoy no tiene web, a partir del bloque `PROSPECTO`.
>
> **Los datos de este archivo son ficticios a propósito: este repo es público.** El boceto de un
> prospecto concreto se arma copiando este prompt a `clientes/<estudio>/PROMPT_BOCETO.md` y
> reemplazando **ahí** el bloque `PROSPECTO` con los datos reales. Nunca acá.
>
> Pegar en el modelo que programa —Antigravity, Claude Code o Codex— con acceso a skills y
> 21st.dev. **Gemini no ejecuta este prompt:** en el reparto lee y resume, no construye, y no
> necesita 21st.dev para eso.
>
> El molde y el relevamiento que lo respaldan (`ESTRUCTURA_NICHO_CONTADORES.md`) viven en el
> vault, no en este repo. **Este prompt es autosuficiente:** todo lo necesario para construir la
> página está más abajo; esa referencia es contexto, no una dependencia.

---

Actuás como Lead Product Designer + Frontend Engineer de una agencia de CRO de nivel élite,
especializada en servicios profesionales en Argentina.

Tu tarea es construir la landing page de un estudio contable de La Plata que **hoy no tiene
web**: existe solo como ficha de Google Maps. La página es el boceto que se le muestra a quien lo
dirige para que vea qué está perdiendo.

El estándar no es "mejor que nada". El estándar es que lo abra en el celular y entienda, sin que
se lo expliquen, que el monotributista que hoy lo encuentra en Maps y se va al siguiente
resultado se va porque no tiene esto.

---

## DATOS DEL PROSPECTO (relevados, no inventados)

> El bloque de abajo es **un ejemplo con datos ficticios**. En la copia de `clientes/` se
> reemplaza por lo relevado de la ficha de Maps y de la conversación de WhatsApp, y **lo que no
> se relevó queda en `null`**, no se completa con algo verosímil.

```js
const PROSPECTO = {
  nombre_legal:  "Estudio Contable Ejemplo",   // ← FICTICIO
  nombre_corto:  null,                 // [CONFIRMAR] cómo quiere que se llame la marca
  contadora:     "C.P. Nombre Apellido",       // ← FICTICIO

  rating:        5.0,
  resenas:       null,                 // NO se muestra aunque exista: ver hallazgo 2

  ciudad:        "La Plata",
  direccion:     null,                 // [COMPLETAR]
  horarios:      null,                 // [COMPLETAR]

  telefono:      "0221 000-0000",      // ← FICTICIO
  whatsapp:      "5492210000000",      // ← FICTICIO, formato wa.me
  email:         null,                 // [COMPLETAR]

  matricula:     null,                 // [COMPLETAR] C.P.C.E.P.B.A. Tº ___ Fº ___
  anios:         null,                 // [COMPLETAR] desde cuándo ejerce

  // Muchos de estos estudios no tienen web, ni Facebook, ni LinkedIn: existen en un solo
  // lugar, que es la ficha de Maps. Verificalo antes de poner iconos de redes.
  redes:         null,

  // La oferta de entrada: lo que el estudio ya da gratis y nadie ve porque vive dentro de
  // una conversación de WhatsApp. Se transcribe TEXTUAL de lo que dijo el prospecto.
  oferta_entrada: {
    nombre:   null,                    // p. ej. "Diagnóstico gratis"
    metodo:   null,                    // el nombre propio que le puso, si tiene uno
    consiste: null,                    // qué hace, en sus palabras
    incluye:  null,                    // [COMPLETAR] qué mira, qué entrega, cuánto tarda
  },

  // HIPÓTESIS hasta que el prospecto la confirme. Señales que la sostienen: ficha a nombre
  // propio sin "y Asociados" (28 de 40 del nicho), teléfono fijo sin web ni correo, y de qué
  // hablaba el mensaje que aceptó. Si la desmiente, cambian el H1 y el eje de las tarjetas.
  publico:   "monotributistas, autónomos y gente que recién arranca a facturar",

  servicios: null,                     // [COMPLETAR] qué hace y qué no
  resenas_texto: [],                   // textuales de Maps, o vacío
};
```

**Regla dura:** todo campo en `null` se renderiza marcado y queda listado en el checklist final.
Nunca se presenta como un hecho confirmado. Pero el marcado **no es una caja punteada con fondo
ámbar** — esa versión ya se probó y produce una página plana, que se siente a medio hacer antes de
que el prospecto llegue al primer párrafo. Usá el sistema de `MUESTRA` (subrayado punteado sutil +
`title="Dato de ejemplo, se reemplaza por el real"` al pasar el mouse), documentado en detalle más
abajo en "Sistema de imágenes y de datos de ejemplo (`MUESTRA`)". La regla de fondo es la misma —
nunca inventes un dato y lo mostrés como si fuera cierto— pero el boceto tiene que poder mostrarse
como si la página ya existiera, con los huecos vestidos de ejemplo en vez de agujeros.

En este rubro esa regla es más estricta que en salud, no menos. Una **matrícula inventada** en la
web de un contador es un problema legal y lo detecta cualquier colega en dos segundos. Una lista
inventada de **qué incluye su diagnóstico** la desmiente él mismo en el primer cliente que lo
pida. Un **precio** inventado rompe la secuencia de venta antes de llegar: el número se habla en
la propuesta, no en el boceto. Estos prospectos tienen muchos más `null` que los de otros nichos:
eso no es un defecto del boceto, es su honestidad, y se muestra como tal.

---

## Los tres hallazgos que definen esta página

No son observaciones de color: son el argumento de venta y tienen que verse resueltos en el
diseño.

**1. Suele tener una oferta de entrada gratis, con nombre propio, y no la ve nadie.** Un
diagnóstico, un chequeo de situación fiscal, una revisión preventiva del CUIT: existe solo dentro
de una conversación de WhatsApp que arranca cuando alguien ya decidió escribirle. Ninguno de los
14 estudios contables de La Plata que sí tienen web ofrece nada parecido, y ninguna de las seis
referencias argentinas relevadas tampoco: todas dicen "consultanos", que no significa nada.

→ **La oferta es el CTA.** No "pedí una consulta" sino el verbo de la cosa concreta que entrega
gratis. El hero se construye alrededor de eso, y la sección inmediatamente siguiente explica en
tres pasos qué recibe, porque un "gratis" sin explicar activa las dos defensas de siempre: cuánto
trabajo me da, y qué me van a querer vender después.

Si `oferta_entrada.nombre` viene en `null`, **preguntalo antes de construir**: sin eso la página
cae en el "pedí tu consulta" genérico y pierde su mejor activo.

**2. El rating de Maps no diferencia a nadie, y mostrarlo juega en contra.** Medido sobre los 40
estudios del nicho: **24 de los 29 que tienen rating están en 4,8 o más, y la mediana de reseñas
es 2.** Un badge "5,0 ★" en el hero de un estudio contable no dice "es bueno": dice "tiene dos
reseñas".

→ **No va badge de rating ni conteo de reseñas.** Es lo primero que haría cualquiera y acá está
mal. El lugar de la prueba social lo ocupan la matrícula, la cara, los años y el método con
nombre. Si el estudio junta seis reseñas o más, entra la sección de reseñas textuales y recién
ahí el agregado.

**3. La competencia que sí tiene web está rota, y está medido.** De los 14 sitios del nicho
auditados: 5 sin HTTPS, 4 sin ningún llamado a la acción visible al entrar, 7 con botones
difíciles de tocar en el celular, 3 con texto demasiado chico, 2 sin adaptación a móvil, dos con
el copyright en 1900 y 2011. **Solo 2 de 14 tienen el teléfono clickeable desde el celular.**

→ Cada una de esas cosas que el boceto hace bien es un argumento medible cuando se lo mostremos,
no una opinión de diseño. En particular: **si este boceto tiene desborde horizontal en mobile,
perdimos el argumento entero**, porque es literalmente lo que le estamos vendiendo.

---

## Orden de ejecución (obligatorio, no lo saltees)

1. Leé las skills antes de escribir una línea de código: `ui-ux-pro-max`,
   `tailwind-design-system`, `page-cro`, `wcag-accessibility`.
2. Consultá 21st.dev y elegí explícitamente 4-6 componentes reales (nombrálos y citá su origen).
   Priorizá: navbar flotante con blur, bento grid, cards con spotlight, accordion animado,
   stepper / timeline de 3 pasos, botón fijo inferior en mobile.
3. Escribí primero el layout de 375px completo. Recién cuando ese esté cerrado, subí a tablet y
   desktop.
4. Al final, autoauditoría contra el "Criterio de éxito".

---

## La psicología de este nicho (esto define el copy — no lo inventes genérico)

El que busca contador **no está comprando un servicio: está delegando un miedo.** Llega en uno de
tres estados, y los tres conviven en el mismo scroll:

- **El que arranca.** Consiguió un cliente que le pide factura. No sabe qué categoría le toca ni
  qué es IIBB. Compara **rapidez** y "¿me lo hacés todo vos?". Decide en horas.
- **El que se está cambiando de contador.** Tiene uno que no le contesta hace tres semanas. Ya
  paga, ya entendió que lo necesita: **es el segmento más rentable y nadie le habla.** Compara
  **capacidad de respuesta** y, sobre todo, cuánto quilombo es mudarse.
- **El que tiene un problema con ARCA.** Intimación, exclusión del monotributo, deuda, o necesita
  certificación de ingresos para un alquiler o un crédito. Compara **urgencia**. Es el que
  convierte más rápido y el que más tolera un precio.

### Las cuatro preguntas que decide antes de escribir

En este orden, y todas se contestan en la primera pantalla y media:

1. **¿Atendés a alguien como yo?** Un monotributista que entra a una web que habla de "gestión
   contable integral para empresas" se va: entendió que no es para él.
2. **¿Cuánto sale?** No lo va a encontrar —ninguna web del rubro publica precios, y nosotros
   tampoco— así que la página **reemplaza el precio por algo gratis y concreto**: el diagnóstico.
3. **¿Me vas a contestar?** La queja número uno del rubro, y el diferenciador más barato que
   existe. Se declara en palabras auditables, no en "atención personalizada".
4. **¿Sos contador de verdad?** Tomo y folio. Es la matrícula visible de salud, trasladada.

Si la página no contesta la 1, no hay mensaje. Si no contesta la 4, no hay confianza para
mandarle un CUIT a un desconocido — que es, literalmente, lo que le estamos pidiendo al
visitante.

---

## Estructura obligatoria

Cada sección lleva su función CRO declarada en un comentario del código.

1. **Navbar flotante** con blur al scrollear. Un solo CTA de la oferta, siempre visible. En ≤375px
   el CTA es un botón fijo abajo, no un ítem de menú. (Lo tienen 2 de 14 en el nicho: es gratis y
   se nota.) **Sin teléfono en la navbar**: ver la nota sobre CTA único más abajo.

2. **Hero** — resuelve las cuatro preguntas en 3 segundos:
   - **H1 con a quién atiende y dónde**: *"Contador público en La Plata para monotributistas y
     emprendedores"*. No "soluciones contables integrales".
   - **Subtítulo: la oferta de entrada con su nombre.** Es el diferenciador real y sale de
     `PROSPECTO.oferta_entrada`, textual. El nombre del método va tal como lo escribió el
     prospecto.
   - **Matrícula bajo el nombre**: `C.P.C.E.P.B.A. Tº ___ Fº ___`, como placeholder marcado.
   - **Un solo botón, WhatsApp**, y el texto precargado **es la oferta**:
     `wa.me/{PROSPECTO.whatsapp}?text=Hola,%20quiero%20el%20diagnóstico%20gratis`. **Sin CTA
     secundario de "llamar".** Decisión de simplificación tomada al construir el primer boceto de
     referencia, no un resultado medido con A/B: un solo camino de contacto es más fácil de
     mantener siempre visible (navbar + `.mobile-cta` fijo) y no divide la decisión del visitante
     entre dos botones. Si en un prospecto puntual el teléfono importa más que el WhatsApp
     (`PROSPECTO.telefono` es el único contacto que dio, por ejemplo), sumalo — no es una regla que
     no se pueda tocar, es el default.
   - **Sin badge de rating.** Ver hallazgo 2. No lo agregues "porque queda bien".

3. **"Qué te llevás con el diagnóstico"** — inmediatamente después del hero. Tres pasos, con
   línea de progreso al scrollear: *me pasás tu CUIT → lo reviso con el método del estudio → te
   digo qué encontré*. Sin jerga.

   **Es la sección que convierte**, porque desarma las dos dudas que frenan cualquier "gratis":
   cuánto trabajo me da y qué me van a querer vender después. Qué mira exactamente sale de
   `oferta_entrada.incluye`: si está en `null`, **va como placeholder marcado, no inventado.** Es
   el dato más importante que falta y el mejor gancho para pedir correcciones.

4. **"¿Cuál es tu caso?"** — bento grid, no lista plana. Tres o cuatro tarjetas por **situación**,
   no por servicio técnico: *Estoy por empezar a facturar* · *Ya soy monotributista* · *Me quiero
   cambiar de contador* · *Tengo un problema con ARCA*.

   Cada tarjeta con **su propio botón de WhatsApp, con el texto del caso ya escrito**, todas
   entrando por la misma puerta: el diagnóstico. **El visitante elige su problema; la página
   elige el mensaje.** Esa inversión es el núcleo de lo que esta web resuelve, y nadie en el
   nicho la hace: todos listan "IVA, Ganancias, Bienes Personales, IIBB", que son las palabras
   del contador, no las del que lo busca.

5. **Qué resuelve, colgando de cada caso.** Los servicios existen, pero cuelgan de la tarjeta que
   los contiene. La lista técnica plana es lo que hace que el monotributista nuevo se sienta en
   el lugar equivocado. Sale de `PROSPECTO.servicios`.

6. **"Cómo es cambiarte de contador"** — tres pasos con la fricción real desarmada: *me escribís
   → le pido los datos a tu contador actual → seguís facturando igual, no se te frena nada*.

   **Ninguna de las 14 webs de contadores de La Plata tiene esta sección, ni ninguna de las seis
   referencias argentinas.** Es el hueco del nicho y le habla al segmento que ya está pagando.

7. **Quién te atiende** — nombre, foto real (placeholder de proporción fija, marcado), matrícula
   con tomo y folio, consejo profesional, años ejerciendo. En un rubro donde le vas a dar tu
   clave fiscal a alguien, la cara y la matrícula **son** el producto.

8. **Prueba social** — si `resenas_texto` está vacío, **la sección no sale con reseñas: sale con
   el sustituto honesto** (años ejerciendo, tipo de clientes que atiende, desde cuándo, el método
   con nombre). Dejá el bloque de reseñas construido pero apagado, con un comentario que explique
   la regla: entra cuando haya seis o más, textuales y con nombre.

9. **FAQ en accordion** con las objeciones reales, no genéricas: ¿cuánto cobrás?, ¿el diagnóstico
   es realmente gratis?, ¿qué necesitás de mí para hacerlo?, ¿atendés presencial o es todo
   online?, ¿qué pasa si me atrasé con los pagos?, ¿me ayudás a darme de alta desde cero?, ¿tengo
   que ir a ARCA?, ¿qué le tengo que pedir a mi contador actual?, ¿atendés fuera de La Plata?

   Las respuestas que dependan de datos que no tenemos salen marcadas. **No inventes una política
   de honorarios.**

10. **CTA final** de ancho completo: el diagnóstico otra vez, WhatsApp con mensaje precargado. Si
    hay formulario, máximo 3 campos (nombre, teléfono, en qué andás). Ninguno más.

11. **Pasarela a empresas** — una sola tarjeta discreta, no una sección: *"¿Tenés una empresa o
    empleados?"*, con su propio mensaje precargado. Cubre el caso de que la hipótesis de
    `PROSPECTO.publico` esté corrida, sin romper la jerarquía de la página.

12. **Footer** con dirección, horarios, teléfono clickeable, correo y mapa embebido de verdad
    (`<iframe>`, no un link a "Ver en Google Maps") — todo lo que siga en `null` sale por
    `field()`, con el sistema `MUESTRA` documentado más abajo.

---

## Reglas de honestidad (esto no es un detalle, es el producto)

- **Cero matrículas inventadas.** Placeholder marcado (ver sistema `MUESTRA` más abajo) hasta que
  el prospecto la pase. Un tomo y folio falso en la web de un contador es un problema legal y lo
  detecta un colega en dos segundos.
- **Cero contenido inventado para el nombre del método.** Se usa **textual**, como lo escribió el
  prospecto. No se rebautiza, no se le pone logo, no se le inventa un claim, no se lista qué
  cubre. Es de él y todavía no nos lo explicó.
- **Cero listas inventadas de qué incluye el diagnóstico.**
- **Cero precios, ni "desde $X".** El número aparece en la propuesta, no en el boceto.
- **Cero reseñas inventadas ni ajenas.** Las de Google, textuales, o ninguna.
- **Cero logos de ARCA, AFIP o del Consejo** puestos como si fueran un aval. El QR de Data Fiscal
  es legítimo si el estudio lo tiene; un escudo decorativo no.
- **Cero nombres ni logos de clientes.** Un contador local no puede publicarlos: son sus clientes.
- **Cero promesas de resultado fiscal.** Nada de "pagás menos impuestos", "ahorro garantizado",
  "te sacamos de cualquier problema con ARCA" ni porcentajes de éxito.
- **Cero fotos que simulen ser la oficina.** Foto de stock cálida y de buen gusto, marcada con el
  badge "Imagen de ejemplo" (ver sistema de imágenes más abajo) hasta que haya una real. Una foto
  de stock presentada como propia es la única forma de que un boceto gratis se vuelva un problema.

---

## Sistema de imágenes y de datos de ejemplo (`MUESTRA`)

Reemplaza la caja punteada con `[COMPLETAR: ...]` en todo el molde. Validado en el primer boceto
real del nicho (estudio de Jimena García, La Plata): un prospecto lo vio y no interpretó ningún
dato de ejemplo como un hecho ya definido, y el boceto igual se sintió terminado, no a medio hacer.

**Imágenes — flag `propia` por imagen, no global.** Cada slot de imagen es un objeto, no un string:

```js
imagenes: {
  hero:    { src: "assets/<estudio>/hero.jpg",    propia: false },
  retrato: { src: "assets/<estudio>/retrato.jpg", propia: true  },
},
```

`propia:false` usa una foto de stock cálida —madera, luz natural, sin vidrio ni acero de estudio de
diseño: la foto tiene que combinar con la paleta tierra/crema, no competir con ella— y le suma un
badge `"Imagen de ejemplo"` (`.figcap`, píldora semitransparente, esquina
superior derecha de la imagen). `propia:true` saca el badge. **Es por imagen porque las fotos
reales llegan en momentos distintos** — el retrato del profesional suele llegar antes que la foto
de la oficina, y un flag único los ata sin necesidad. Mismo mecanismo para el mapa del footer:
`<iframe>` real embebido (`google.com/maps?q=...&output=embed`, sin API key) usando la dirección de
`MUESTRA` cuando `PROSPECTO.direccion` es `null`, con el mismo badge marcando que la dirección es
de ejemplo. Nunca el recuadro punteado con un link a "Ver en Google Maps": eso no comunica cómo se
va a ver la página terminada.

**Texto — diccionario `MUESTRA` + helper `field()`.** Por cada label que puede faltar, una versión
de ejemplo plausible:

```js
const MUESTRA = {
  'matrícula': 'C.P.C.E.P.B.A. Tº 123 Fº 123',   // números redondos a propósito: 123/123 se lee
  // como ejemplo aunque nadie note el subrayado ni pase el mouse por el tooltip
  'dirección': 'Calle 47 n.º 512, piso 2 "B", La Plata',
  // ... una entrada por cada label que se usa en field(valor, 'label')
};
const field = (value, label) => {
  if (value != null && value !== '') return esc(value);
  const m = MUESTRA[label];
  if (m) return `<span class="sample" title="Dato de ejemplo, se reemplaza por el real">${esc(m)}</span>`;
  return `<span class="placeholder">falta: ${esc(label)}</span>`;   // sin ejemplo seguro: cae acá
};
```

`.sample` es un subrayado punteado sutil (`border-bottom:1px dotted var(--line)`), no una caja con
fondo. Se nota si buscás dato por dato; no rompe la primera impresión. El `title` es la red de
seguridad para quien sí pasa el mouse. Si un label no tiene una `MUESTRA` segura para inventar —no
la fuerces: cae al `field()` a `falta: <label>`, que sigue siendo el mismo texto llano de siempre,
sin caja ni fondo ámbar (ese estilo visual queda descartado del todo, tenga o no ejemplo).

La regla de honestidad no cambia un milímetro: `MUESTRA` es para que el boceto **se vea** como la
página terminada, nunca para que un dato de ejemplo pase por un hecho confirmado de este prospecto.

---

## Reglas de diseño (no negociables)

- **Mobile-first real, 375px primero.** Sin desborde horizontal en ningún breakpoint. Ver
  hallazgo 3: si el boceto lo tiene, perdimos el argumento entero.
- **Áreas táctiles de 48px mínimo.** Es el defecto más repetido del nicho —7 de las 14 webs de La
  Plata lo tienen— así que es un argumento medible, no una preferencia.
- **Tipografía base 17px**, interlineado 1.6, contraste AA real. Nada de gris claro sobre blanco.
  Tres de las 14 tienen texto chico en mobile.
- **Sistema de diseño explícito** al tope: escala tipográfica con `clamp`, paleta en tokens CSS,
  espaciado 4/8px, radios y sombras consistentes.
- **Paleta y tipografía por defecto** (validadas en el primer boceto del nicho, no una sugerencia
  genérica — arrancá de acá salvo que el estudio tenga marca propia):
  `--bg:#F0EDE4; --surface:#FAF8F2; --ink:#1B1B1B; --primary:#6B3D1E; --accent:#7A8470;
  --line:#C8C0B0`. Marrón tierra como primario (botones, CTA), salvia como acento puntual (nunca
  en un botón: a igual peso de texto queda por debajo de 4.5:1 de contraste — el primario/on-primary
  ya da 7.76:1, usalo también para los botones sobre fondo de color en vez de inventar un tercer
  tono). Tipografía: `Cormorant Garamond` (serif, 500/600/700) para títulos, `Lato` (sans,
  300/400/700/900) para todo lo demás. Este rubro pide confianza, no energía. **Evitá** el azul
  corporativo genérico de plantilla y el oro sobre negro de "asesoría premium", que es lo que hacen
  todos y lo que hace que un estudio de barrio parezca una consultora que no es. Dejá documentada
  una paleta alternativa por si el estudio tiene marca propia.
- **Sin dark mode.** `<meta name="color-scheme" content="light only">` y `html{color-scheme:light
  only}` fijos. Decisión tomada al construir el boceto de referencia para no duplicar cada token de
  la paleta cálida en una segunda versión oscura que nadie pidió — no una limitación técnica. Si un
  prospecto puntual lo pide, se suma ahí, no antes.
- **Accesibilidad**: focus visible, `prefers-reduced-motion` respetado en todas las animaciones,
  alt en todas las imágenes, jerarquía de headings correcta.

## Animaciones

Entrada por sección con stagger al scrollear, hover con spotlight en las tarjetas de caso,
progreso en el stepper de tres pasos, transición del navbar al pasar el hero. Todo por debajo de
400ms. Si una animación se nota como "animación", está mal calibrada.

---

## Lo que NO va

Badge de rating. Contador de reseñas. Calculadora de monotributo o de categoría —las escalas las
cambió ARCA en agosto de 2026 y la recategorización es semestral: una calculadora desactualizada
en la web de un contador lo desprestigia justo en lo único que vende. Calendario de vencimientos
estático, por lo mismo. Portal del cliente. Stock de gente de traje dándose la mano. Iconos de
billetes, monedas flotando y gráficos de torta genéricos. "Misión, visión y valores". "Somos un
equipo de profesionales altamente capacitados". Carrusel arriba de todo. Formulario de 8 campos.
Chatbot. Pop-up de newsletter. Lorem ipsum. Iconos de redes que no usa. Cualquier texto que no
conteste una de las cuatro preguntas.

> La calculadora y el calendario **no se descartan para siempre**: son el argumento de
> mantenimiento, porque vencen solos dos veces por año con fecha conocida. Se ofrecen a los tres
> meses de publicada, no en el boceto.

---

## Performance

- Un solo archivo HTML autocontenido: CSS y JS inline, sin dependencias externas salvo Google
  Fonts.
- **Menos de 500 KB en total** y por debajo de 2 segundos en 4G. Se lo vamos a mandar por
  WhatsApp a alguien que lo va a abrir con datos móviles, y el argumento de venta incluye la
  velocidad.
- Tiene que abrir bien con doble clic, sin servidor.

---

## Entregable

El archivo HTML, más un bloque comentado al final con:

- Qué componentes de 21st.dev usaste y por qué.
- **Lista de campos en `null`** que quedaron como placeholder, para completar antes de mostrarla.
  En este nicho son muchos: ordenalos por cuánto cambian la página, con `oferta_entrada.incluye`
  y la matrícula primeros.
- **Checklist de personalización** para adaptarla a otro estudio del nicho, en orden y con tiempo
  estimado.
- **Qué habría que cambiar para la variante B (empresas)**, en no más de diez renglones: H1, eje
  de las tarjetas —de situación a función— y CTA de reunión en vez de diagnóstico.
- 3 hipótesis de test A/B para la siguiente iteración.

Todo el contenido de negocio sale de `PROSPECTO` / `CONFIG`. **Ningún texto del cliente
hardcodeado en el marcado**, y los colores alimentan tokens CSS, para que cambiar el primario
reacomode la paleta entera. El layout tiene que aguantar los extremos: un nombre corto y uno
larguísimo, 3 tarjetas de caso o 5, con matrícula o sin ella, con reseñas o sin ninguna.

---

## Criterio de éxito

Cuatro pruebas, las cuatro obligatorias:

1. **El dueño o la dueña** abre la página en el celular y en 3 segundos ve su nombre, su oferta
   de entrada con el nombre de su método tal como lo escribió, y un botón de WhatsApp que
   escribe de verdad a su número.
2. **Un monotributista que recién arranca** entiende en una pantalla que es para él, y manda el
   mensaje en dos toques sin haber leído la palabra "IIBB".
3. **Nada de lo que dice la página es inventado.** Todo lo que no sabemos se ve como un hueco
   marcado, y el checklist final los lista todos.
4. **Vos** la convertís en la landing de otro estudio de La Plata editando solo `PROSPECTO`, en
   menos de diez minutos, sin tocar el marcado.

Si falla la 1, no vende. Si falla la 2, no sirve. Si falla la 3, no se puede mostrar. Si falla la
4, no escala.
