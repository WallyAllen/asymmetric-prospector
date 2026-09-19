# 006 · Medición

> Estado: pendiente · Rama: `006-stats` · Fase 5 · depende de 003

Sin esto, todo lo anterior es fe.

## Qué pasa hoy

`registro_envios.json` guarda id, nombre, email, url, asunto, score y fecha. No
guarda `message_id`, ni variante, ni toque. No hay comando que conteste "¿cuál
es mi tasa de respuesta?".

## Qué tiene que pasar

Registro enriquecido con `message_id`, `toque`, `variante`, `nicho` y
`veredicto`, y un comando `py -m prospector stats`:

```
Últimos 30 días · 49 enviados · 3 nichos

  entregados      47   (95,9%)
  rebotados        2   ( 4,1%)  ⚠ por encima del 2%
  respondidos      ?
  bajas            ?

  por toque:     1 → 49 env · ? resp
  por variante:  con_captura / sin_captura
  por nicho:     inmobiliarias / contadores
  por score:     90-100 · 70-89 · <70
```

**El corte por score es el que importa** y el que nadie mira: es el único bucle
de retorno que tiene el motor de reglas. Ver `El score se calibra con las
respuestas` en el vault.

## Criterio de aceptación

```
tests/test_core.py::test_stats_corta_por_score
tests/test_core.py::test_stats_sin_envios_no_rompe
```

```bash
pytest tests/ -x -q
py -m prospector stats
```

## Alcance

**Tocar:** `deliver/mailer.py` (registro), `report.py` o un `stats.py` nuevo,
`cli.py`, `tests/test_core.py`

**No tocar:** el score. Esto lo mide, no lo cambia.
