# 002 · Archivo de contexto de producto

> Estado: pendiente · Rama: `002-contexto` · Fase 0 del plan de outreach

## Qué pasa hoy

`SENDER_PROOF` es un string suelto en `.env`. No hay ningún lugar donde estén
el ICP, la oferta, lo que NO hacés y las objeciones frecuentes, así que el
redactor con IA no tiene con qué responder a una objeción ni con qué evitar
prometer algo que no ofrecés.

## Qué tiene que pasar

Existe `.agents/product-marketing.md` con ICP, problema en el lenguaje del
dueño, oferta, pruebas verificables, objeciones y tono. `writer.py` lo carga con
una función análoga a `cargar_plantilla()` y lo inyecta en el `PROMPT` dentro de
un bloque `<contexto>` **con tope de ~1.500 caracteres**.

`config.py` gana `CONTEXT_FILE = BASE_DIR / ".agents" / "product-marketing.md"`.

`cfg.sender_proof` sigue siendo la fuente de la línea de prueba concreta; el
contexto aporta el marco.

## Criterio de aceptación

```
tests/test_salida.py::test_contexto_se_inyecta_acotado
tests/test_salida.py::test_sin_contexto_funciona_igual
```

El segundo es el que importa: **sin el archivo, todo sigue exactamente como
hoy** — degradación elegante, igual que sin `GEMINI_API_KEY`.

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `prospector/compose/writer.py`, `prospector/config.py`,
`.agents/product-marketing.md`, `tests/test_salida.py`

**No tocar:** el motor de plantillas (escribe el 97,5 % y no usa el prompt).

**Tamaño:** el mínimo que haga pasar el test.

## Cuidados

`.agents/product-marketing.md` lleva pruebas reales con nombres de clientes.
Este repo es público: que entre al `.gitignore` o que las pruebas vayan sin
nombre ("un estudio contable en La Plata").
