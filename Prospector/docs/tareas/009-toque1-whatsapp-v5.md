# 009 · Toque 1 por WhatsApp v5: la falla medida, no el sistema

> Estado: lista para Codex · Rama: `009-toque1-whatsapp-v5` · tests en `tests/test_whatsapp_v5.py`

## Qué pasa hoy

Los mensajes de WhatsApp a inmobiliarias de la cola (`generado_por="claude-v4-whatsapp"`)
se escribieron a mano en lote y no usan la auditoría. Abren describiendo la portada
("la portada es el buscador «…»"), siguen con una consecuencia de cajón que se repite
en decenas de mensajes, se presentan con "webs y sistemas" y cierran preguntando qué
sistema usan o cuántas tasaciones les entran por mes.

Medido sobre lo enviado desde el 15/10: tres de los rechazos registrados contestaron
"ya tenemos CRM/sistema", o sea que la pregunta del cierre les sirve de salida. En al
menos un caso la auditoría tenía una falla killer (LCP > 4 s) que el mensaje ignoró
para hablar del "Acceso Clientes".

```bash
py -m prospector lint
# la cola mezcla claude-v4-whatsapp (125) y plantilla-whatsapp (27)
```

`compose/whatsapp.py` ya tiene la forma correcta (hallazgo → consecuencia → boceto),
pero usa la consecuencia genérica de `audit/rules.py` ("ni turno, ni llamar"), que no
está escrita para una inmobiliaria, y deja liderar hallazgos que el prospecto no puede
comprobar (LCP de 2,5 a 4 s, texto chico, tap targets).

## Qué tiene que pasar

1. **Solo se redacta si hay una falla que se compruebe abriendo la web.** El hallazgo
   que lidera tiene que estar en `REGLAS_TOQUE1`:
   `carga_lenta` (solo `categoria == "killer"`, o sea ≥ 4 s), `sin_contacto`,
   `sin_tel_movil`, `overflow_mobile`, `sin_viewport`, `popup_intrusivo`,
   `sitio_inaccesible`. Se toma el primero de `audit.argumentables` que esté en la lista.
   - En inmobiliarias **no** lidera `sin_cta_fold`: el buscador hace de botón y el
     auditor no lo cuenta, así que la frase "no hay ningún botón" puede ser falsa.
   - Si ningún hallazgo califica: `estado = "descartado"`,
     `motivo_descarte = "sin falla verificable para toque 1"`. No se redacta nada.
   - La rama sin web (`url is None`) sigue como hoy.
2. **Estructura, menos de 75 palabras, tres bloques:**
   1. saludo + presentación: `Soy {nombre}, hago webs para {rubro.plural}.` La palabra
      "sistema" no aparece.
   2. observación con el dato medido + **una** consecuencia, escrita para el rubro.
   3. oferta del boceto **de esa pantalla** + una pregunta que se contesta con sí o no.
3. **Textos para inmobiliarias** (`rubro.plural == "inmobiliarias"`): los de la tabla
   de abajo, en `compose/lexicon.py`, elegidos con `elegir(..., lead.id, campo)` como
   el resto. Para los demás rubros sigue la `consecuencia` de `audit/rules.py`.
4. **Estilo de Felipe en todo mensaje de WhatsApp:** sin tildes (la ñ se mantiene),
   sin "¿" ni "¡". Se aplica al final, en una función `estilo_felipe(texto)` que
   llama `componer_whatsapp`. Los dominios no cambian (no tienen tildes).
5. **Frases prohibidas en WhatsApp toque 1** (`validar(canal="whatsapp")`):
   `sistema`, `crm`, `tokko`, `seguramente`, `por qué elegirte`, `por que elegirte`,
   `en un mes normal`, `cuántos pedidos`, `cuantos pedidos`, `la misma foto`,
   `el mismo buscador`. Cualquiera de ellas → el borrador no pasa la validación.
6. **Trazabilidad:** `generado_por = "plantilla-whatsapp-v5"` y un campo nuevo
   `EmailDraft.regla: str = ""` con el `rule_id` que lideró. Es lo que permite medir
   respuestas por regla después.
7. **Recompone la cola sin tocar lo enviado:** `compose` recompone todo lead en
   `auditado` o `listo_whatsapp` cuyo `generado_por` no sea `plantilla-whatsapp-v5`.
   `enviado`, `enviado_whatsapp`, `rebotado` y `respondido` no se tocan.
8. **Lint:** nueva métrica por canal, "oración más repetida del cuerpo" (salteando el
   primer bloque, el del saludo), objetivo **< 25 %**. Y una línea con la cantidad de
   mensajes por `regla`.
9. **No se redacta sobre una auditoría vieja.** Si `audit.auditado_el` tiene más de
   `MAX_DIAS_AUDITORIA = 14` días (constante en `compose/whatsapp.py`, no config),
   el lead no se redacta: `email_draft = None`, `estado = "auditado"`,
   `motivo_descarte = "auditoría de más de 14 días: re-auditar antes de redactar"`.
   Aplica también a un `listo_whatsapp` v4 que se iba a recomponer.
   `redactar_whatsapp` recibe `hoy: date | None = None` (por defecto, la fecha
   local) para que el test no dependa del reloj.
   - Por qué: el mensaje afirma algo que el prospecto comprueba abriendo la web. Un
     "no cargó" o un "tardó 6 segundos" de hace tres semanas puede ser falso hoy, y
     un mensaje que afirma algo falso sobre su web quema el número y el contacto.
   - Cómo se refresca: `py -m prospector audit --forzar --nicho inmobiliaria`.
     `merge_leads` ya adopta la auditoría con `auditado_el` más nuevo, así que el
     `compose` siguiente redacta sobre la medición fresca. No hace falta tocar
     `storage.py`.
   - Medido el 26/10 después de fusionar con `02_audited`: las 53 inmobiliarias
     con web que quedaron redactadas tienen la auditoría de hace 10 días. A partir
     del 30/10 cualquier `compose` las deja sin redactar hasta re-auditarlas.

### Textos (inmobiliarias)

`{v}` sale de `VERBO` y `{vc}` de `VERBO_CELU`; `{d}` es `dominio_de(lead)`;
`{s}` es `metrics.lcp_ms / 1000` con coma decimal (`_coma`). `OFERTA` va por regla:
la oferta nombra lo que se arregla. `sitio_inaccesible` no ofrece boceto: cierra con
`CIERRE_INACCESIBLE`.

```python
VERBO      = ("Entré a {d}", "Abrí {d}", "Miré {d}")
VERBO_CELU = ("Entré a {d} desde el celu", "Abrí {d} en el celu", "Miré {d} desde el celular")
SALUDOS = ("Hola, ¿qué tal?", "Hola, buenas.", "Hola, ¿cómo va?", "Buenas, ¿qué tal?")
PRESENTACIONES = (
    "Soy {nombre}, hago webs para {plural}.",
    "Soy {nombre} y armo webs para {plural}.",
    "Te escribo por algo puntual. Soy {nombre}, hago webs para {plural}.",
    "Me llamo {nombre} y trabajo haciendo webs de {plural}.",
    "Soy {nombre}, diseño webs para {plural}.",
)
OBSERVACION = {
    "carga_lenta": (
        "{v} y tardó {s} segundos en mostrar algo.",
        "{v} y la portada tardó {s} segundos en aparecer, con una conexión normal.",
        "{v}: {s} segundos hasta que se ve la portada.",
    ),
    "sin_contacto": (
        "{v} y no encontré cómo consultar: no hay formulario, ni teléfono para tocar, ni WhatsApp.",
        "{v} y no hay forma de consultar desde la web: ni WhatsApp, ni teléfono para tocar, ni formulario.",
    ),
    "sin_tel_movil": (
        "{vc} y la única forma de consultar es un formulario: no hay WhatsApp ni teléfono para tocar.",
        "{vc} y para consultar hay que llenar un formulario; no hay botón de WhatsApp ni de llamar.",
    ),
    "overflow_mobile": (
        "{vc} y la página se sale de la pantalla: hay que arrastrar para los costados para leer.",
        "{vc} y queda más ancha que la pantalla, así que se lee cortada.",
    ),
    "sin_viewport": (
        "{vc} y se ve la web de la compu en miniatura: hay que hacer zoom para leer.",
        "{vc} y aparece la versión de escritorio achicada; sin zoom no se lee.",
    ),
    "popup_intrusivo": (
        "{v} y lo primero que aparece es un aviso que tapa la pantalla y hay que cerrar.",
    ),
    "sitio_inaccesible": (
        "Quise entrar a {d} y no cargó, probé dos veces.",
    ),
}
# El que más pesa para una inmobiliaria es el propietario que quiere vender: llega
# recomendado y mira la web antes de llamar. El comprador consulta en el portal.
CONSECUENCIA_INMOBILIARIA = {
    "carga_lenta": (
        "El propietario que te recomendaron entra a mirarte antes de llamar, y lo primero que ve es la espera.",
        "El que busca casa tiene diez pestañas abiertas y cierra la que tarda.",
        "En ese tiempo, el que estaba mirando una propiedad ya volvió atrás.",
        "El que está eligiendo a quién darle su casa para vender compara dos o tres webs, y la que tarda queda última.",
    ),
    "sin_contacto": (
        "El que ve una casa que le gusta tiene que salir a buscar tu número, y casi siempre lo deja para después.",
        "El propietario que te recomendaron entra a mirarte y no tiene cómo escribirte desde ahí.",
    ),
    "sin_tel_movil": (
        "El que mira casas desde el celu quiere escribir por WhatsApp y listo; un formulario lo deja para después.",
        "El que encontró la casa que buscaba quiere preguntar ya, y un formulario lo enfría.",
    ),
    "overflow_mobile": (
        "Casi todo el que busca casa lo hace desde el celu, y lo ve roto en los primeros segundos.",
        "El propietario que te recomendaron entra a mirarte desde el celu y se lleva esa imagen.",
    ),
    "sin_viewport": (
        "Casi todo el que busca casa lo hace desde el celu, y nadie hace zoom para leer una ficha.",
        "El propietario que te recomendaron entra a mirarte desde el celu y se lleva esa imagen.",
    ),
    "popup_intrusivo": (
        "El que entra a ver propiedades tiene que sacarse eso de encima antes de ver una sola casa.",
        "La primera impresión de la inmobiliaria termina siendo un cartel que estorba.",
    ),
    "sitio_inaccesible": (
        "El que te busca y se encuentra con eso no vuelve a probar: entra al siguiente resultado.",
        "El propietario que te recomendaron te busca para chequearte y termina llamando a la otra que le nombraron.",
    ),
}
# La oferta nombra lo que se arregla; "esa pantalla" no dice nada.
OFERTA = {
    "carga_lenta": (
        "Te armo un boceto de esa misma portada cargando rápido.",
        "Te hago un boceto de cómo quedaría esa portada, liviana.",
        "Te muestro en un boceto cómo sería esa portada sin la espera.",
    ),
    "sin_contacto": (
        "Te armo un boceto de la portada con la consulta a un toque.",
        "Te hago un boceto de cómo quedaría con un botón de WhatsApp a la vista.",
    ),
    "sin_tel_movil": (
        "Te armo un boceto de cómo se vería en el celu con un botón de WhatsApp.",
        "Te hago un boceto de esa misma web con la consulta por WhatsApp a un toque.",
    ),
    "overflow_mobile": (
        "Te armo un boceto de cómo se vería bien en el celu.",
        "Te hago un boceto de esa portada adaptada al celular.",
    ),
    "sin_viewport": (
        "Te armo un boceto de cómo se vería bien en el celu.",
        "Te hago un boceto de esa portada adaptada al celular.",
    ),
    "popup_intrusivo": (
        "Te armo un boceto de la portada sin ese aviso, mostrando las propiedades de entrada.",
    ),
}
CIERRE = ("¿Te lo paso?", "¿Te lo mando?", "¿Querés verlo?", "Es sin cargo, ¿te lo paso?", "¿Te sirve que te lo pase?", "¿Lo querés ver?", "Si te sirve, ¿te lo mando?")
CIERRE_INACCESIBLE = ("Si querés te paso qué error me apareció, ¿te sirve?",)
```

**Por qué estos textos y no los del primer borrador (revisión 26/10):**

- Salió *"Google cuenta como lenta toda web que pasa de 4 segundos, y te muestra menos en
  las búsquedas"*: la segunda mitad no se puede sostener si el prospecto pregunta.
- Salió *"El que llega desde un aviso de Zonaprop… vuelve al portal"*: el que viene de
  Zonaprop consulta dentro de Zonaprop; la web no está en ese camino.
- Entró el **propietario que quiere vender** en todas las reglas. Es el único argumento
  de la v4 que valía (al comprador lo traen los portales; al que vende, la recomendación,
  y antes de llamar mira la web), sin la pregunta por números que la acompañaba.
- La oferta ya no dice "esa pantalla arreglada": dice qué se arregla (cargando rápido,
  con WhatsApp a la vista, adaptada al celu, sin el aviso).
- Siete cierres en vez de cinco: con cinco, el cierre era la oración más repetida (26 %).
- Se acortó la observación de carga: "medido entrando como entraría cualquiera" iba en
  todas las variantes y sumaba palabras sin dato.

Cómo queda, con datos ficticios (después de `estilo_felipe`):

> Hola, buenas. Soy Felipe y armo webs para inmobiliarias.
>
> Entre a ejemplopropiedades.com.ar y la portada tardo 5,3 segundos en aparecer, con una conexion normal. El propietario que te recomendaron entra a mirarte antes de llamar, y lo primero que ve es la espera.
>
> Te hago un boceto de como quedaria esa portada, liviana. Te lo paso?

## Criterio de aceptación

```
tests/test_whatsapp_v5.py::test_sin_falla_verificable_se_descarta
tests/test_whatsapp_v5.py::test_carga_moderada_no_lidera
tests/test_whatsapp_v5.py::test_sin_cta_fold_no_lidera_en_inmobiliarias
tests/test_whatsapp_v5.py::test_lidera_la_primera_regla_de_la_lista
tests/test_whatsapp_v5.py::test_consecuencia_inmobiliaria_por_regla
tests/test_whatsapp_v5.py::test_otro_rubro_usa_consecuencia_de_rules
tests/test_whatsapp_v5.py::test_no_menciona_sistema_crm_ni_pide_numeros
tests/test_whatsapp_v5.py::test_cierre_es_pregunta_si_no
tests/test_whatsapp_v5.py::test_estilo_felipe_sin_tildes_ni_apertura
tests/test_whatsapp_v5.py::test_menos_de_75_palabras
tests/test_whatsapp_v5.py::test_guarda_regla_y_version
tests/test_whatsapp_v5.py::test_recompone_v4_y_no_toca_enviados
tests/test_whatsapp_v5.py::test_validar_rechaza_frases_prohibidas_toque1
tests/test_whatsapp_v5.py::test_lint_oracion_mas_repetida
tests/test_whatsapp_v5.py::test_auditoria_vieja_no_se_redacta
tests/test_whatsapp_v5.py::test_auditoria_reciente_si_se_redacta
```

Los tests ya están escritos en `tests/test_whatsapp_v5.py` y hoy fallan: son el
contrato. Si un test y este texto se contradicen, manda el test; avisá en el PR.

Los leads de los tests se arman a mano con datos ficticios (`ejemplo.com.ar`,
`Inmobiliaria Ejemplo`), nunca desde `data/`.

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `prospector/compose/whatsapp.py`, `prospector/compose/lexicon.py`,
`prospector/compose/writer.py` (solo `validar` y la lista de prohibidas de WhatsApp),
`prospector/models.py` (solo `EmailDraft.regla`), `prospector/lint.py`,
`tests/test_whatsapp_v5.py`.

**No tocar:** `audit/rules.py` (el score y sus umbrales quedan como están), el
redactor de correo, el default de `send`, la idempotencia de las etapas, ni ningún
lead en estado enviado.

**Tamaño:** el mínimo que haga pasar los tests. Sin config nueva ni dependencias.
`EmailDraft.regla` tiene default `""` para que los JSON viejos sigan cargando.

## Medición de referencia (prototipo sobre la cola del 23/10)

| | v4 en cola | v5 prototipo | v5.1 (26/10) |
|---|---|---|---|
| mensajes (inmobiliarias con web) | 125 | 54 | 53 |
| oración del cuerpo más repetida | — | 24 % | 21 % |
| palabras (mediana / máx) | 83 / 95 | 60 / 69 | 56 / 71 |
| menciona sistema/CRM o pide números | casi todos | 0 | 0 |

88 inmobiliarias de la cola quedan descartadas por no tener una falla verificable.
Es el costo buscado: no se les escribe con una falla inventada.

## Para después (fuera de esta tarea)

- `sin_cta_fold` para inmobiliarias: contar el botón del buscador como acción y, si
  aun así da 0, recién ahí volverlo a la lista.
- Toque 2: con `EmailDraft.regla` ya se puede cruzar respuestas por regla (spec 006).
  El texto del seguimiento por WhatsApp está en la spec 004, sección *WhatsApp*.

## Qué se descartó de la otra v5 (borrador de claude.ai, 26/10)

Se escribió sin acceso a la cola y choca con esta spec en tres puntos:

- **Lideraba con "no hay nada para el propietario que quiere vender".** Es describir
  la portada, no una falla medida: es exactamente lo que este toque deja atrás.
- **"Con una inmobiliaria de Zona Norte estamos armando justo eso."** Prueba social
  que el prospecto no puede comprobar, repetida en decenas de mensajes de la misma
  zona. Si va, va en `SENDER_PROOF` y para todos, no como frase del toque 1.
- **Cierre "Te muestro como quedaria en la tuya?"**: ya cubierto por `CIERRE`.

Lo que sí entró: re-chequear la web antes de escribir (punto 9) y el seguimiento
por permiso (spec 004).

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector audit --forzar --nicho inmobiliaria   # refresca las de más de 14 días
py -m prospector compose --nicho inmobiliaria
py -m prospector lint
py -m prospector status
```
