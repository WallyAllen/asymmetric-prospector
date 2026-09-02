# ⚙️ Plan de automatización (v2)

Documento arquitectónico. El "cómo" ejecutable vive en `prospector/` y el "cómo se
usa" en `README.md`; aquí queda por qué el sistema está diseñado así.

## Principio rector: la asimetría

El trabajo caro (mockups, desarrollo) **nunca** se hace por adelantado. Lo que se
automatiza es la parte barata y repetible —encontrar, medir, demostrar, escribir—
y el esfuerzo humano se reserva para quien ya levantó la mano.

## Las cuatro etapas

### 1. Minado (`prospector/sources/`)
Google Maps con Scrapling: negocios reales con nombre, teléfono y reseñas. La señal
más valiosa que da Maps es la ausencia: **una ficha sin web es el prospecto de
máxima puntuación**, porque no hay que convencer a nadie de que su web es mala.

Los directorios y agregadores (Cylex, Lawzana, rankings, redes sociales) se
descartan por lista negra: no son clientes, son ruido. La deduplicación es por
dominio registrable, así que dos URLs del mismo negocio son un solo lead.

Después, una pasada de contacto visita cada web buscando el correo en el HTML, en
los `mailto:`, en el JSON-LD de schema.org, en las páginas de contacto y aviso
legal, y desofuscando los "hola (arroba) negocio (punto) com".

### 2. Auditoría (`prospector/audit/`)
Dos capas, en este orden:

**Capa objetiva (gratis, siempre).** Playwright abre la web en escritorio (1440px)
y en móvil real (390px, touch, UA de iPhone) y mide: estado HTTP, HTTPS, TTFB, LCP,
CLS, peso y número de peticiones, `meta viewport`, desborde horizontal, tamaños de
fuente, tamaño táctil de los botones, CTAs en la primera pantalla, formularios,
`tel:` y WhatsApp, títulos y meta descripciones, imágenes sin `alt` y
sobredimensionadas, popups fijos, items de menú, año del copyright y rastros de
tecnología obsoleta. Las reglas de `rules.py` convierten cada medición en un
`Finding` con tres piezas: **evidencia** (el dato duro), **argumento** (la
traducción a dinero perdido) y **zona** (el rectángulo a marcar en la captura).

**Capa de juicio (IA, solo donde hay negocio).** Únicamente si el score objetivo
supera el umbral, Gemini mira las dos capturas y la lista de mediciones. No busca
el problema —ya está medido—: lo confirma, le pone palabras humanas y señala dónde
mirar. Si contradice las métricas, el score baja. La IA nunca es punto único de
fallo: sin clave, sin cuota o con respuesta inválida, el pipeline continúa.

### 3. Redacción (`prospector/compose/`)
Dos motores intercambiables (IA y plantillas) y **un único filtro anti-slop** por el
que pasan los dos: fuera muletillas de bot, negritas de markdown, guiones largos y
frases de agencia; tope de longitud; validación de que no quedaron marcadores sin
rellenar. Si el borrador de la IA no pasa la validación, se usa el de plantilla.

El correo lleva la captura anotada embebida: el recuadro rojo sobre su propia web es
lo que separa este correo de los cincuenta que recibe al mes.

### 4. Envío (`prospector/deliver/`)
`smtplib` contra una cuenta real con contraseña de aplicación. Conexión abierta y
cerrada **por correo** (mantenerla viva durante una pausa de 10 minutos la mataba),
cuota diaria persistente, ventana horaria laborable, jitter de 6-14 minutos, lista
de supresión y registro idempotente. Simula por defecto.

## El disparador asimétrico

El prospecto responde "quiero ver cómo lo mejoraríais" → recién ahí se instancia el
agente que toma el mockup del nicho en `Landing/nichos/*/mockup`, lo adapta con los
datos del prospecto y despliega un MVP en minutos. El enlace es la excusa para la
llamada de cierre.

## Decisiones que conviene no revertir

- **El score no lo pone la IA.** Un modelo que "opina" que una web es mala genera
  argumentos indefendibles en cuanto el prospecto responde. Un LCP de 6,4 s no se
  discute.
- **Rutas relativas en los datos.** Mover la carpeta del proyecto no puede romper
  el histórico (ya pasó una vez).
- **Idempotencia por `lead.id`.** Reejecutar cualquier etapa nunca duplica ni
  reescribe trabajo ya hecho.
- **Simular por defecto.** El único comando irreversible del sistema exige pedirlo
  explícitamente.
