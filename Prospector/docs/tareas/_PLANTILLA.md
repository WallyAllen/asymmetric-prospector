# NNN · <título en una línea, lo que cambia para el usuario>

> Estado: pendiente · Rama: `NNN-nombre-corto`

## Qué pasa hoy

Dos o tres líneas. El comportamiento actual, con el comando que lo reproduce.

```bash
py -m prospector <comando>
# lo que imprime hoy
```

## Qué tiene que pasar

Dos o tres líneas. El comportamiento nuevo. Sin justificar, sin alternativas:
la decisión ya se tomó antes de escribir esta spec.

## Criterio de aceptación

El test existe y falla antes de empezar. Esto es el contrato: cuando pasa,
la tarea terminó.

```
tests/test_<x>.py::test_<nombre>
```

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `prospector/<modulo>.py`, `tests/test_<x>.py`

**No tocar:** todo lo demás. En particular, nada que cambie el default de
`send` (simula), la idempotencia de las etapas, ni el origen del score
(reglas medidas, no IA).

**Tamaño:** el mínimo que haga pasar el test. Sin abstracciones, sin
scaffolding, sin config nueva, sin dependencias nuevas. Si hace falta una
dependencia, no la agregues: devolvé la spec diciendo cuál y por qué.

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector status
py -m prospector lint      # solo si tocaste compose/ o templates/
```
