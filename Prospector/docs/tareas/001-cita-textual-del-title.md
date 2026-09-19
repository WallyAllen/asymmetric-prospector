# 001 · Abrir el correo citando el título real de su página

> Estado: pendiente · Rama: `001-cita-title`

Última pendiente del `INFORME_REDACCION`. Las otras ocho ya están en el código
(verificado el 18/09: `observacion`/`consecuencia`/`puente` en `models.py`,
elección por `sha1` y `_RUBROS` en `lexicon.py`, `validar()` llamado en los dos
motores, empalme del "con" y decimales arreglados, `· UNLP` fuera de
`SENDER_ROLE`, `lint` existiendo).

## Qué pasa hoy

`metrics.title` está medido y guardado para el **89 %** de los leads con web, y
el redactor no lo usa. La apertura sale del hallazgo, que es lo mismo que le
llega a todos los que comparten ese hallazgo.

```bash
py -m prospector lint
# la apertura más repetida sigue siendo una oración de regla
```

## Qué tiene que pasar

Cuando hay `metrics.title`, el correo abre citando textualmente su propia
página antes de dar el hallazgo:

> Tu página se presenta como «Centro Odontológico Privado — Odontología integral
> en La Plata», pero en la primera pantalla no hay ni un botón para pedir turno.

Sin `title`, la apertura actual, sin cambios.

Es la personalización más barata que queda: un `if` y una comilla, sin IA, sin
red y sin clave. Y es verificable por el prospecto, que es lo que la hace valer.

## Criterio de aceptación

El test existe y falla antes de empezar.

```
tests/test_salida.py::test_apertura_cita_el_title
tests/test_salida.py::test_apertura_sin_title_no_cambia
```

El primero: un lead con `metrics.title` produce un cuerpo que contiene el título
entre comillas angulares. El segundo: un lead sin `title` produce exactamente el
cuerpo de hoy.

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `prospector/compose/writer.py`, `tests/test_salida.py`

**No tocar:** `audit/`, el score, ni el default de `send`. Nada de esto cambia
qué lead vale la pena: cambia cómo se le escribe.

**Tamaño:** el mínimo que haga pasar el test. Sin abstracciones, sin config
nueva, sin dependencias.

## Cuidados

- **Comillas angulares** («»), que es el sistema que usa el resto del corpus.
- **El título viene sucio**: puede traer el nombre del CMS, separadores raros,
  mayúsculas gritadas o 90 caracteres. Recortar y normalizar, y si queda
  irreconocible, caer a la apertura de hoy en vez de citar un engendro.
- **No tocar la rama "no cargó".** Si la web no abrió no hay `title`, y el
  mensaje tiene prohibido afirmar que la miró.

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector lint      # la apertura más repetida tiene que bajar
py -m prospector status
```
