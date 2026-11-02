# 011 · El mail v6 para todos los rubros, y la plantilla de septiembre sale de la etapa

> Estado: aplicada localmente el 2026-11-02 · Rama: `011-mail-v6-rubros` · test en `tests/test_mail_v6_rubros.py`
> Depende de 010: extiende `compose/mail_v6.py`, no lo reemplaza. La 010 tiene que
> estar commiteada en `master` antes de abrir esta rama; el test importa sus helpers.

## Qué pasa hoy

Revisión de la cola de mail del 27/10: 207 borradores sin enviar, todos `plantilla`
o `ia` de septiembre. Fallas que se repiten:

- firma `Diseño y CRO de landing pages · UNLP` (el lint ya marca la credencial);
- razón social de Maps cruda en asunto y cuerpo: `una pregunta sobre NEGOCIO EJEMPLO | Consultorio…`;
- trato mezclado en el mismo mail: "Tienen 4,8…" y después "tu web tarda…";
- cierres a la defensiva ("Sin compromiso", "No te compromete a nada");
- `Te adjunto la captura con la zona marcada.` en el 51 % de los mails.

En inmobiliarias la 010 ya lo resuelve: correr `compose` lleva 111 de `listo` a
67 v6 y 44 descartadas por no tener falla verificable (simulado en memoria, sin
guardar). Fuera de inmobiliarias quedan **43 en `listo`** con el borrador viejo
(25 del rubro genérico, 8 estudios jurídicos, 5 fisioterapia, resto sueltos), y
`redactar_mail_v6` las saltea por rubro. Encima, `compose --forzar` les vuelve a
pasar `redactar_todos`.

```bash
py -m prospector lint
# EMAIL · oración más repetida 51 % (objetivo < 25 %) · 9 no pasan la validación
```

## Qué tiene que pasar

1. `redactar_mail_v6` deja de filtrar por rubro: entra todo lead con `url`,
   `contactable` y estado `auditado` o `listo`. Las puertas, los estados que no
   se tocan y la retención a mano (`auditado` con borrador) quedan como están.
2. **Qué hace**, una sola expresión para presentación y firma:
   - rubro reconocido → `webs para {rubro.plural}` (firma: `Webs para {plural}`);
   - `GENERICO` → `páginas web` (firma: `Páginas web`). Su `plural` es
     "servicios de la zona": sirve para describir una búsqueda, no un oficio.
   `PRESENTACIONES_MAIL_V6` pasa de "webs para inmobiliarias" fijo a `{oficio}`.
   `firma_v6` recibe el oficio; para inmobiliarias sigue dando exactamente lo
   mismo (los tests de la 010 no cambian).
3. **Cuerpo fuera de inmobiliarias**, tres bloques y firma:
   1. saludo + presentación (igual que en inmobiliarias);
   2. reputación (mismo umbral) + el hallazgo del camino genérico de
      `componer_whatsapp`: `APERTURAS_CON_WEB` + `principal.observacion` +
      `principal.consecuencia` (o `rubro.cliente se va sin rubro.accion`).
      Sacalo a una función de `whatsapp.py` que usen los dos canales; no lo copies;
   3. `OFERTAS_CON_WEB` + `CIERRE_MAIL_V6`.
   Sin `QUE_HAGO_MAIL_V6`: la web en curso es de una inmobiliaria y contársela a
   una veterinaria no prueba nada.
   `sitio_inaccesible`: bloque 2 = el texto genérico de "no cargó" de
   `componer_whatsapp`; bloque 3 = `CIERRE_INACCESIBLE`; sin boceto.
4. `CIERRE_MAIL_V6`: la primera opción pierde el "Sin compromiso." final.
5. `pipeline.redactar_correos` deja de llamar a `redactar_todos`. Con eso deja de
   haber borradores `plantilla` o `ia` nuevos para mail. **No borres**
   `writer.py` ni `redactar_todos` en esta tarea: `asunto_para`, `validar`,
   `limpiar` y `dominio_de` viven ahí y los usa la v6. Achicar `writer.py` es
   otra spec.

## Criterio de aceptación

```
tests/test_mail_v6_rubros.py
```

```bash
pytest tests/ -x -q
```

Hoy fallan 9 de sus 10 tests. El que pasa es una guarda: enviados y retenidos
de otros rubros quedan intactos. Las dos fallas de
`tests/test_maps_ficha.py` son de la spec 008 y no cuentan acá.
`test_plantilla_v6.py::test_no_toca_enviados_ni_sin_email` ya se ajustó: dejó
de exigir que una veterinaria quede afuera.

## Alcance

**Tocar:** `prospector/compose/mail_v6.py`, `prospector/compose/whatsapp.py`
(solo extraer el hallazgo genérico), `prospector/compose/lexicon.py`
(`PRESENTACIONES_MAIL_V6`, `CIERRE_MAIL_V6`), `prospector/pipeline.py`.

**No tocar:** los tests, `writer.py`, el `.env`, `data/`. Nada que cambie el
default de `send` (simula), la idempotencia de las etapas ni el origen del score.
No recompongas la cola: correr `compose` sobre `data/` lo decide Felipe.

**Tamaño:** el mínimo que haga pasar el test. Sin config nueva, sin dependencias.

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector status
py -m prospector lint      # mail: oración más repetida < 35 % (objetivo de la 010)
```

## Notas para Felipe

- Después del merge, `py -m prospector compose` recompone la cola entera
  (inmobiliarias y el resto). Los 22 `auditado` con borrador siguen retenidos:
  se liberan pasándolos a `listo` a mano.
- "Webs para reformas" y "webs para agencias" salen tal cual del `plural` del
  rubro. Si suenan raros leídos en la cola, se cambia el `plural` en `lexicon.py`
  o pasan a `páginas web`. Son 3 leads hoy.

## Verificacion del 2026-11-02

- Suite: 137 tests aprobados y 2731 subtests; 2 fallas preexistentes de la spec 008 (`_web_de_ficha`).
- Regeneracion autorizada por Felipe: 4 mails habilitados revisados, 2 regenerados validos y 2 devueltos a auditoria por mediciones vencidas. Respaldo local previo a guardar.
- Retenidos y enviados intactos. Verificacion realizada antes del commit.
