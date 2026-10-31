# 012 · El auditor detecta qué usa la web, y el mail de inmobiliarias habla según eso

> Estado: implementada por Claude el 30/10, sin commitear · test en `tests/test_sistema_web.py`
> Se adelantó el punto 4 de la 011 (`CIERRE_MAIL_V6` sin «Sin compromiso»): sin eso
> el peor mail pasaba de 150 palabras. Lo demás de la 011 sigue pendiente, y con
> él `test_otros_rubros_no_la_llevan`.

## Qué pasa hoy

De las 7 inmobiliarias que respondieron, 5 ya tenían CRM (Tokko, WASI, Liderprop).
El mail no sabe con quién habla. Cuando sonó a «otra cosa más para administrar»,
la respuesta fue no (Juliano). Cuando quedó claro que la web lee lo que ya cargan,
la charla siguió (Galan). El auditor ya lee `meta generator` y lo tira: nada lo usa.

```bash
py -m prospector compose
# el mail v6 es igual para una inmobiliaria con Tokko que para una sin nada
```

## Qué tiene que pasar

1. **Medir.** `probe_js.AUDIT_JS` devuelve `recursos`: las URLs absolutas únicas
   de `script[src]`, `link[href]`, `img[src]`, `iframe[src]` y `a[href]`, con
   tope de 400. Nuevo `prospector/audit/sistema.py`, sin dependencias:
   - `detectar_sistema(generador, recursos) -> str`, en este orden:
     1. **CRM inmobiliario**, por host (igual al dominio o subdominio de él, sin
        importar mayúsculas): `tokko` ← `tokkobroker.com`, `wasi` ← `wasi.co`.
     2. **Constructor**, por `generador` (empieza con `wordpress`, `wix`,
        `squarespace`, `webflow`, o contiene `wix.com`), por host (`wix` ←
        `wixstatic.com`, `parastorage.com`; `squarespace` ← `squarespace.com`,
        `squarespace-cdn.com`; `webflow` ← `website-files.com`) o por ruta
        (`wordpress` ← `/wp-content/`, `/wp-includes/`).
     3. Nada de eso: `"sin_detectar"`.
     El CRM gana al constructor. Una palabra en la ruta o el host de otro dominio
     (`tokkobroker.com.ejemplo.com.ar`) no es firma.
   - `perfil_sistema(sistema) -> "crm" | "desconocido"`: `crm` solo para los de
     la lista 1; todo lo demás, incluido `None`, es `desconocido`.
   - Los dominios van en dos dicts al tope del módulo. Sumar otro CRM es una línea.
2. **Guardar.** `Metrics.sistema_web: str | None = None`. `_consolidar` lo llena
   solo si el dict de escritorio trae la clave `recursos`; sin ella queda `None`
   (no medido: JS viejo o auditoría anterior). `EmailDraft.sistema: str = ""`.
3. **Escribir.** En `componer_mail_v6`, solo para inmobiliarias y salvo
   `sitio_inaccesible`, una oración al frente del bloque de la oferta:
   `"{linea} {oferta} {cierre}"`. `linea = elegir(PROPIEDADES_MAIL_V6[perfil],
   lead.id, "propiedades").format(sistema=NOMBRE_SISTEMA.get(sistema, ""))`.
   `draft.sistema` = `sistema_web`, o `"no_medido"` si es `None`; `""` cuando no
   va la línea (inaccesible, otros rubros). Así se mide qué perfil responde.
   Texto, tal cual, al final de `lexicon.py`:

```python
# Spec 012. Cinco de las siete inmobiliarias que respondieron ya tenían CRM. Con
# CRM se nombra el suyo: la web lee lo que ya cargan, no es otra cosa más para
# administrar. Sin CRM detectado no se sabe si no usan nada o usan uno que no
# reconocemos, así que la frase es cierta en los dos casos y no nombra productos.
# Ni "sistema" ni "CRM": abren la salida del "ya tenemos" (009). Tope 11
# palabras: el peor mail v6 queda justo en las 150.
NOMBRE_SISTEMA = {"tokko": "Tokko", "wasi": "Wasi"}
PROPIEDADES_MAIL_V6 = {
    "crm": (
        "Tus propiedades saldrían solas de {sistema}, sin cargarlas dos veces.",
        "Las propiedades salen de tu {sistema}: no cargás nada dos veces.",
    ),
    "desconocido": (
        "Tu web nueva funciona con lo que ya uses para las propiedades.",
        "Tu web nueva se adapta a lo que uses para las propiedades.",
    ),
}
```

WhatsApp no cambia: ahí «tokko» sigue prohibido por la 009.

## Criterio de aceptación

```
tests/test_sistema_web.py
```

```bash
pytest tests/ -x -q
```

Hoy falla entero (falta `audit/sistema.py`). Ojo: con `pytest-subtests`, tres
tests se marcan `PASSED` aunque sus subtests fallen; mirá el total. Contra la
011 sin mergear falla `test_otros_rubros_no_la_llevan` y el tope de palabras
(el «Sin compromiso.» suma dos). Probado con una implementación de referencia y el cierre de la 011
simulado: 16 de 17 (el que falta es el de otros rubros, que es la 011 misma),
peor mail 150 palabras en 6.300 combinaciones.

## Alcance

**Tocar:** `prospector/audit/probe_js.py` (solo `recursos`),
`prospector/audit/sistema.py` (nuevo), `prospector/audit/signals.py`
(`_consolidar`), `prospector/models.py` (dos campos),
`prospector/compose/mail_v6.py`, `prospector/compose/lexicon.py` (el bloque de
arriba, al final).

**No tocar:** los tests, `rules.py` (el sistema no suma ni resta score),
`whatsapp.py`, `writer.py`, el `.env`, `data/`. Nada que cambie el default de
`send`, la idempotencia de las etapas ni el origen del score.

**Tamaño:** el mínimo que haga pasar el test. Sin config nueva, sin dependencias.
`detectar_sistema` entra en unas 30 líneas.

## Cómo verificar que no se rompió nada

```bash
pytest tests/ -q
py -m prospector status
py -m prospector lint      # mail: sin «frase prohibida» nueva
```

## Notas para Felipe

- Las auditorías de hoy no tienen `recursos`: todas salen `desconocido` hasta
  re-auditarlas. Como el mail ya exige auditoría de menos de 14 días, se
  ponen al día solas con `audit --reanudar`.
- Liderprop, KiteProp, Xintel: no entran hasta ver la firma en una web real.
  Abrí el código fuente (Ctrl+U) de un cliente suyo, buscá el dominio que se
  repite en las imágenes y sumalo al dict de CRMs, con su nombre en
  `NOMBRE_SISTEMA`.
- WordPress, Wix y el resto quedan guardados aunque el mail diga lo mismo que
  `sin_detectar`: sirven para filtrar la cola por perfil («tradicionales con
  web vieja») cuando quieras.
