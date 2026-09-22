# 007 · Sub-rubro de contadores

> Estado: pendiente · Rama: `007-subrubro-contadores`

## Qué pasa hoy

`rubro_de()` resuelve "contador" a un único `Rubro` cuyo `cliente` es "el
monotributista que necesita ordenarse". Sobre los 40 leads del nicho
"Contadores La Plata", 12 tienen señal de sociedad en el nombre de Maps ("y
Asociados", "SRL", "SA"): a esos la redacción les habla de un problema que no
tienen.

```bash
py -c "from prospector.compose.lexicon import rubro_de; print(rubro_de('contadores La Plata', nombre='Pérez y Asociados').cliente)"
# el monotributista que necesita ordenarse   ← mismo texto que un estudio unipersonal
```

## Qué tiene que pasar

`rubro_de(nicho, nombre=None)` recibe también el nombre del lead. Para el
rubro contador, si `nombre` trae señal de sociedad, `cliente` pasa a "la
empresa que necesita llevar la contabilidad al día". Sin señal, o para
cualquier otro rubro, el comportamiento no cambia.

`componer_por_plantilla()` (writer.py:498) y `componer_whatsapp()`
(whatsapp.py:107) pasan `lead.nombre` en la llamada existente a `rubro_de`.

## Criterio de aceptación

```
tests/test_core.py::TestLexico::test_rubro_de_contador_distingue_sociedad
```

El test ya está escrito y hoy falla (`TypeError: rubro_de() got an unexpected
keyword argument 'nombre'`).

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `prospector/compose/lexicon.py` (firma de `rubro_de` y la señal de
sociedad), `prospector/compose/writer.py:498`, `prospector/compose/whatsapp.py:107`.

**No tocar:** el resto de los `_RUBROS`. Ninguno de los otros nichos distingue
por nombre todavía — no es parte de esta tarea inventarles esa distinción.

**Tamaño:** un `frozenset` o tupla con las palabras de señal ("asociados",
"srl", "s.r.l", " sa ", "s.a.") y un `if` en `rubro_de`. No hace falta un
`Rubro` nuevo por sociedad: alcanza con devolver el mismo `Rubro` de contador
con `cliente` reemplazado (`dataclasses.replace`).

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector status
py -m prospector lint      # toca compose/
```
