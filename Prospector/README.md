# 🎯 Prospector

Sistema de **prospección asimétrica**: encuentra negocios cuya web pierde clientes
(o que directamente no tienen web), lo demuestra con datos medidos y una captura
señalada, y les escribe un correo que parece escrito a mano. Todo local, sin SaaS
de pago, con la IA como accesorio y no como muleta.

```
  minar  ──▶  auditar  ──▶  redactar  ──▶  enviar
  Maps        señales        anti-slop      SMTP con
  + web       + reglas       + captura      cuota y jitter
              + jurado IA    anotada
```

## Instalación

```bash
cd scripts
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
python -m playwright install chromium
scrapling install                                  # navegador sigiloso
copy ..\.env.example ..\.env                       # y rellena lo que necesites
```

No hace falta clave de IA para que el sistema funcione: sin `GEMINI_API_KEY` la
auditoría usa solo señales objetivas y los correos salen del motor de plantillas.

Si vienes de los scripts `0X_*.py` anteriores (antes de este paquete), tus datos
en `data/02_audited/` y `data/03_composed/` están en un formato viejo que este
paquete ya no entiende por sí solo. Antes de tocar nada, migra una vez:

```bash
python -m prospector.migrate
```

Es seguro correrlo aunque no tengas datos viejos: si no encuentra restos del
formato anterior, no hace nada. En este proyecto ya recuperó 2 leads auditados
que estaban a punto de perderse.

## Uso

```bash
python -m prospector mine "clinicas dentales valencia"   # 1 · minar
python -m prospector audit                               # 2 · auditar
python -m prospector compose                             # 3 · redactar
python -m prospector send                                # 4 · simular envío
python -m prospector send --enviar-de-verdad --limite 5  #     enviar de verdad

python -m prospector run "fisioterapia sevilla"          # todo seguido (simula el envío)
python -m prospector status                              # estado del embudo
python -m prospector report                              # informe HTML con capturas
```

Todas las etapas son **idempotentes y reanudables**: puedes cortar con Ctrl+C y
retomar sin duplicar trabajo ni volver a gastar en IA. Los antiguos
`scripts/0X_*.py` siguen funcionando: ahora son alias de estos comandos.

## Cómo decide qué lead vale la pena

El score (0-100, más alto = más oportunidad) **no lo pone la IA**: lo suman reglas
sobre datos medidos en un navegador real, en escritorio y en móvil. Y el score
**no mide calidad ni buenas prácticas**: mide una sola cosa, si la web le está
costando clientes al negocio de forma demostrable, hoy. Una landing profesional
con un par de detalles de pulido (sin favicon, meta description floja) sigue
siendo una landing que convierte — eso no es un prospecto de valor, y el motor
está calibrado para no tratarlo como tal.

Cada regla se etiqueta con una categoría:

| Categoría | Qué significa | Peso |
|---|---|---|
| **killer** | Corta el embudo de raíz: nadie puede contactar, no hay CTA, el móvil no funciona, la web no carga | 18-38 (o 95-100 si está caída / sin web) |
| **moderado** | Fricción real pero no fatal: empeora la conversión sin matarla | 4-10 |
| **cosmético** | Detalles de pulido (SEO, favicon, alt text, menú largo). No mueven el score | 0-4 |

Un solo *killer* ya empuja el lead a "mejorable"; hacen falta dos (o un *killer*
fuerte más varios *moderados*) para llegar a "crítico". Toda la pila de hallazgos
*cosméticos* junta ni siquiera cruza el umbral de contacto: no se escribe a nadie
por no tener favicon.

| Señal medida | Categoría | Peso | Por qué importa |
|---|---|---|---|
| No tiene web (ficha de Maps a secas) | killer | 100 | El prospecto perfecto: no hay nada que criticar, hay todo que construir |
| Web caída o con error | killer | 95 | Cada visita se pierde entera |
| Sin `meta viewport` (no responsive) | killer | 38 | Más de la mitad del tráfico ve la web de escritorio miniaturizada |
| Ningún CTA en la primera pantalla | killer | 35 | Nadie ve cómo contactarte |
| Sin formulario, teléfono ni WhatsApp | killer | 35 | No hay ninguna forma de convertir, en toda la web |
| LCP > 4 s | killer | 28 | Una de cada cuatro personas abandona antes de que cargue |
| Desborde horizontal en móvil | killer | 22 | Hay que hacer scroll lateral para leer |
| Tecnología obsoleta (tablas, Flash) | killer | 20 | Partes del sitio directamente no funcionan |
| Primera pantalla vacía (sin CTA ni texto) | moderado | 10 | En 3 segundos no se entiende qué ofreces |
| Sin HTTPS | moderado | 10 | El navegador la marca «No segura» |
| Popup/cookies que tapa el contenido | moderado | 8 | Lo primero que se ve es un aviso, no la oferta |
| Texto o botones diminutos en móvil, CLS alto, teléfono no pulsable, copyright viejo | moderado | 4-7 | Fricción real, no siempre fatal |
| SEO básico, menú largo, imágenes sin optimizar/alt, sin favicon | cosmético | 0-4 | Pulido — no decide el veredicto |

Por debajo de `AUDIT_MIN_SCORE` (28 por defecto) el lead se descarta: su web
funciona y no hay historia que contar. Por encima de `AUDIT_VISION_THRESHOLD`
(55) —y solo ahí, cuando ya hay evidencia objetiva fuerte— entra Gemini como
**jurado visual**: mira las dos capturas y, con instrucciones explícitas de ser
escéptico por defecto, confirma o desmiente el diagnóstico. Si dice que la web
se ve profesional pese a las métricas, el score baja con fuerza (-25 puntos) y
puede sacar al lead de la lista de contacto: es preferible descartar un caso
dudoso que enviar un correo con un argumento que el dueño del negocio puede
rebatir en diez segundos mirando su propia pantalla.

## La prueba visual

Por cada lead calificado se guardan cuatro capturas crudas en
`data/screenshots/<dominio>/` (escritorio fold y completa, móvil), más la
**anotada**: no es la pantalla entera con una marca perdida en algún rincón,
sino un recorte ampliado alrededor de la zona exacta del problema, con el
recuadro rojo, numerado, y el diagnóstico impreso al pie. Esa es la que viaja
embebida en el correo — lo primero que ve el prospecto es un primer plano de
su propio defecto, no un mapa de toda su pantalla. Si no hay una zona concreta
que señalar (el problema es "no hay ningún CTA en ningún lado", no un elemento
puntual), se usa la captura completa tal cual. Si el defecto principal es de
móvil, se manda la del móvil.

## Estructura

```
prospector/
  config.py        Toda la configuración, leída de .env
  models.py        Lead, Audit, Finding, Metrics, EmailDraft (JSON serializable)
  storage.py       Escritura atómica, fusión por lead.id, rutas relativas
  ai.py            Cliente Gemini con reintentos, throttle y degradación elegante
  sources/         google_maps.py · search.py · contacts.py
  audit/           probe_js.py · signals.py · rules.py · capture.py · vision.py · runner.py
  compose/         writer.py (motor IA + motor plantillas + filtro anti-slop)
  deliver/         mailer.py · quota.py
  pipeline.py      Las cuatro etapas encadenables
  cli.py           python -m prospector <comando>
  report.py        Informe HTML autocontenido
data/
  01_raw · 02_audited · 03_composed · 04_sent · screenshots · logs
tests/             17 pruebas sin red, sin navegador y sin claves
```

## Entrega en bandeja de entrada

- Conexión SMTP **por correo** (una sesión abierta durante una pausa de 10 minutos se cae).
- Cuota diaria persistente (`MAIL_DAILY_CAP`), ventana horaria laborable y sin fines de semana.
- Jitter aleatorio de 6 a 14 minutos entre envíos.
- Multipart texto + HTML con la captura embebida por `cid`.
- Lista de supresión en `data/04_sent/lista_supresion.txt`: un email o dominio por
  línea, nunca se vuelve a contactar. Los rebotes se añaden solos.
- `send` **simula por defecto**. Nada sale sin `--enviar-de-verdad`.

## Antes de enviar

Estás escribiendo a empresas sobre su propia web, con un motivo real y datos
verificables: eso es interés legítimo. Aun así, escribe desde una dirección real,
identifícate, responde a las bajas el mismo día y añade a quien lo pida a la lista
de supresión. Un dominio quemado no se recupera; la cuota diaria está para eso.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Cubren normalización de URLs, filtrado de directorios, limpieza de emails, el motor
de reglas completo (web sana / web pésima / sitio caído), el filtro anti-slop, la
anotación de capturas y la construcción del correo MIME.

## Este repositorio es público — lo que no se publica

El código es abierto a propósito: es más útil mirado que escondido, y lo que
diferencia una prospección de un spam no es el script, es el criterio con el que
se elige y se escribe.

Los **datos** son otra cosa. Nadie de los que aparecen en `data/` pidió estar
ahí: son negocios reales con su nombre, su teléfono, su mail y los defectos de
su web. Eso no se publica, ni siquiera "para mostrar cómo funciona".

Fuera del repositorio, por `.gitignore`:

```
data/01_raw/  02_audited/  03_composed/  04_sent/  05_whatsapp/  screenshots/
.env
```

Y hay un hook que corta el commit si algo de eso se cuela igual (por un
`git add -f`, por una regla mal editada, o por una clave de API pegada a mano).
Instalalo una vez por clon:

```bash
git config core.hooksPath Prospector/scripts/hooks
```

Si alguna vez tiene que entrar algo bloqueado, `git commit --no-verify` — pero
pensalo dos veces: en un repositorio público no hay marcha atrás, borrarlo
después no lo saca de los commits viejos.

Los ejemplos de `templates/primer_mensaje.md` son ficticios. Los informes que
vienen versionados usan datos de prueba, no leads reales.

## Licencia

MIT — ver [`LICENSE`](../LICENSE).
