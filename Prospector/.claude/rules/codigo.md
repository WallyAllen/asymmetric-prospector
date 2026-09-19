---
paths:
  - "prospector/**/*.py"
  - "tests/**/*.py"
  - "scripts/*.py"
---

# Convenciones del código

Este paquete ya tiene un estilo y está sostenido. Seguilo en vez de imponer el
tuyo.

- `from __future__ import annotations` en todos los módulos. Tipos modernos
  (`list[str] | None`), no `Optional` ni `List`.
- **Todo en español**: nombres de función, docstrings, comentarios, subcomandos
  y flags (`--limite`, `--forzar`, `--sin-ia`, `--reanudar`). No traduzcas al
  inglés lo que ya está en español.
- **Los docstrings explican el porqué, con el número que lo motivó.** Mirá
  `lint.py` o `compose/lexicon.py`: dicen qué problema existía y qué pasó
  cuando se hizo de la otra manera. Un docstring que repite el nombre de la
  función no vale la línea que ocupa.
- `cli.py` no lleva lógica: parsea y delega en `pipeline.py`.
- **Nada aleatorio sin semilla.** El mismo lead recompuesto tiene que dar el
  mismo texto. `hash()` de Python está prohibido: está aleatorizado por proceso
  (`PYTHONHASHSEED`) y da distinto en cada corrida. Se usa `sha1`.
- Toda etapa es idempotente y reanudable. Si tu cambio hace que reanudar
  duplique trabajo o vuelva a gastar en IA, está mal aunque pasen los tests.

## El ciclo con Codex

Un cambio de comportamiento se escribe primero como test que falla, en
`tests/`. Ese test es el contrato: es lo que va en la spec y es lo único que
hay que leer para saber si Codex terminó.

```bash
pytest tests/ -x -q          # el veredicto
py -m prospector status      # el embudo no se rompió
py -m prospector lint        # la redacción no empeoró
```

No revises el diff antes de que el test pase.

## La escalera antes de escribir (ponytail)

Antes de escribir una línea, bajá la escalera y parate en el primer escalón que
alcance:

1. ¿Hace falta que exista? La mayoría de las veces, no.
2. ¿Ya está en el repo? `rg` antes que teclado.
3. ¿Lo hace la librería estándar?
4. ¿Lo hace algo ya instalado? (Playwright, Scrapling, Pillow ya están)
5. Una línea.
6. El mínimo que pase el test.

Borrar gana a agregar. Aburrido gana a ingenioso. Nada de abstracciones,
scaffolding ni capas de configuración que nadie pidió. Una dependencia nueva se
justifica por escrito o no entra.

Cuando simplifiques a propósito algo que alguien esperaría más grande, dejalo
marcado en el código:

```python
# ponytail: un dict alcanza; cuando haya un segundo canal, acá va la clase
```

### Dónde NO aplica

**Los docstrings del porqué se quedan.** Esto no es verbosidad: es lo que evita
que el próximo agente "simplifique" una decisión deliberada. El comentario que
explica que `hash()` de Python está aleatorizado por proceso es exactamente lo
que impide que alguien lo reintroduzca el mes que viene. La escalera recorta
código, no razones.

La regla práctica: si al borrarlo se pierde una decisión y su motivo, no es
verbosidad. Si al borrarlo solo se pierde una paráfrasis del nombre de la
función, sobraba.
