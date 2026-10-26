# 008 · Maps toma la web de la ficha cuando la tarjeta no la trae

> Estado: pendiente · Rama: `008-web-desde-la-ficha`

## Qué pasa hoy

`_parse_card()` (sources/google_maps.py:92) busca la web solo entre los
enlaces de la tarjeta del listado. En rubros de servicios (inmobiliarias,
abogados) Maps pone ahí el botón "Sitio web"; en comercios (tiendas de ropa)
no lo pone. Resultado: la tanda "tiendas de ropa La Plata" del 05/10 dejó
**20 de 20** leads con `url=None` y `tiene_web=False`.

Comprobado el 15/10 en Maps: la tarjeta de Tienda Ejemplo no tiene ningún
enlace externo; su ficha sí, en `a[data-item-id="authority"]`
→ `https://tiendaejemplo.com.ar/`.

```bash
py -m prospector mine "tiendas de ropa La Plata" --max 20
# Maps: 20 negocios (20 sin web propia)
```

## Qué tiene que pasar

1. Función nueva `_web_de_ficha(pagina) -> str | None` en google_maps.py:
   devuelve el `href` de `a[data-item-id="authority"]` de una ficha de Maps,
   o `None` si no está. No normaliza ni filtra: eso sigue en `_parse_card`.
2. `mine_google_maps()`, dentro del mismo `AsyncStealthySession` (hoy se
   cierra apenas se carga el listado), abre la ficha (`href` del ancla
   `/maps/place/`) de cada lead que quedó sin `url`, aplica `_web_de_ficha`
   y pasa el resultado por `normalize_url` + `is_directory`, igual que hoy.
   Una ficha que falla o expira deja el lead como está y se loguea; no corta
   la tanda.
3. Solo se abren fichas de leads sin web, y como mucho `cfg.max_leads`.

## Criterio de aceptación

```
tests/test_maps_ficha.py::test_web_de_ficha_lee_authority
tests/test_maps_ficha.py::test_web_de_ficha_sin_web
tests/test_maps_ficha.py::test_tarjeta_de_tienda_no_trae_web
```

```bash
pytest tests/ -x -q
```

Verificación manual (no reemplaza al test): minar de nuevo
"tiendas de ropa La Plata" y que Tienda Ejemplo salga con
`tiendaejemplo.com.ar`.

## Alcance

**Tocar:** `prospector/sources/google_maps.py`, `tests/test_maps_ficha.py`

**No tocar:** todo lo demás. En particular, `is_directory` (un Instagram
como "web" sigue contando como sin web propia), el default de `send`, la
idempotencia de las etapas y el origen del score.

**Tamaño:** el mínimo que haga pasar el test. Sin config nueva ni
dependencias nuevas.

## Caso relacionado: linktree que lleva a la tienda

Comprobado el 15/10: la ficha de Soho La Plata enlaza `https://linktr.ee/SohoDenim`,
que lleva a `sohodenim.com.ar`. `is_directory` trata linktr.ee como "sin web
propia" y el borrador le dijo "sin web enlazada", que es falso. Fuera de esta
tarea, pero hay que decidirlo: o se sigue el linktree buscando un dominio propio,
o esos leads se excluyen de la plantilla "sin web".

## Para después (fuera de esta tarea)

`_parse_card` pisa `lead.direccion` y `lead.categoria` con `None`
(google_maps.py:181-183) aunque el texto de la tarjeta los trae
("Tienda de ropa para jóvenes · C. 2 200"). Por eso los leads de ropa
también quedaron sin dirección ni categoría.

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector status
```
