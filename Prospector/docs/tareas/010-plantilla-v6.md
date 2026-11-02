# 010 · Plantilla v6: el mail formal vuelve para inmobiliarias, y WhatsApp prueba la identidad

> Estado: aplicada el 26/10 (Claude, a pedido de Felipe) · Rama: `010-plantilla-v6` · tests en `tests/test_plantilla_v6.py`
> Depende de 009 (ya en `master`): reutiliza `regla_toque1`, `OBSERVACION`,
> `CONSECUENCIA_INMOBILIARIA`, `OFERTA`, `estilo_felipe` y el corte de 14 días.

## Qué pasa hoy

Los mails anteriores usaban razon social cruda, firma academica y trato inconsistente. Esta spec introduce el formato formal v6 y una variante de identidad para WhatsApp. Los antecedentes comerciales se conservan en la documentacion interna.

## Qué tiene que pasar

### A · Mail v6 para inmobiliarias (`compose/mail_v6.py`, nuevo)

1. `redactar_mail_v6(leads, cfg, forzar=False, hoy=None)` redacta los leads con
   `rubro_de(nicho).plural == "inmobiliarias"`, `contactable`, `url`, y estado
   `auditado` o `listo` cuyo `generado_por` no sea `plantilla-mail-v6` (o `forzar`).
   Nunca toca `enviado`, `enviado_whatsapp`, `rebotado`, `respondido`, `baja`, ni un
   `auditado` que ya tiene borrador: es una retención a mano («No soy bot», afirmaciones
   de riesgo) y se libera pasándolo a `listo`.
2. Mismas puertas que la 009, con los mismos estados y `motivo_descarte`:
   auditoría de más de `MAX_DIAS_AUDITORIA` → `auditado`; HTTP ≥ 400 → `revisar_web`;
   sin `regla_toque1` → `descartado` ("sin falla verificable para toque 1").
3. Cuatro bloques y firma (tres si `sitio_inaccesible`: no hay bloque 3 ni boceto,
   cierra con `CIERRE_INACCESIBLE`):
   1. `SALUDOS_MAIL_V6` + `PRESENTACIONES_MAIL_V6` con el **primer nombre** de
      `sender_name`. Sin razón social en el saludo.
   2. reputación (solo si `resenas >= 30` y `rating >= 4.5`, con `REPUTACION_MAIL_V6`)
      + `OBSERVACION[regla]` + `CONSECUENCIA_INMOBILIARIA[regla]`.
   3. `QUE_HAGO_MAIL_V6`: la prueba social verificada de un cliente, sin nombrarla.
   4. `OFERTA[regla]` + `CIERRE_MAIL_V6`.
   5. `firma_v6(cfg)`: `sender_name` / `Webs para inmobiliarias` / `sender_site` /
      `sender_phone`. **No usa `sender_role`**: así sale sin `· UNLP` sin tocar el `.env`.
4. Asunto: `asunto_para(lead, principal)` (ya cumple ≤ 5 palabras, en minúscula).
5. Sin adjunto: las capturas anotadas traen dibujado el hallazgo viejo.
6. `estilo_felipe` sobre asunto y cuerpo (firma incluida). Pasa `validar(canal="email")`.
7. `EmailDraft(generado_por="plantilla-mail-v6", regla=..., variante="formal")`.
8. `pipeline.redactar_correos` llama a `redactar_mail_v6` **antes** de `redactar_todos`,
   y `redactar_todos` deja afuera a las inmobiliarias (si no, `compose --forzar` las
   pisaría con la plantilla de septiembre).

### B · WhatsApp v6 (`compose/whatsapp.py`)

9. `VERSION = "plantilla-whatsapp-v6"`. Todo lo de la 009 sigue igual.
10. Inmobiliarias con web y `sender_site` configurado: `variante` por
    `elegir(("corta", "identidad"), lead.id, "variante_v6")`.
    - `corta`: el mensaje v5 sin cambios.
    - `identidad`: el primer bloque suma una frase de `IDENTIDAD_V6` con
      `enlace_corto(sender_site)` (`linkedin.com/in/felipeborrazas`, sin `https://`,
      sin `www.`, sin `/` final). Sigue habiendo 3 bloques; tope 95 palabras.
    - Cualquier otro caso: `variante = "corta"`.
11. `validar(..., enlace_propio="")`: un enlace que esté contenido en `enlace_propio`
    no cuenta como "enlace ajeno". Cualquier otro enlace sigue rechazado.

### C · Lo que se mide

12. `EmailDraft.variante: str = ""` (los JSON viejos cargan con `""`).
13. `deliver.traza_borrador(lead) -> dict` con `generado_por`, `variante` y `regla`
    del borrador (`{}`-safe si no hay borrador). `deliver/mailer.py` y
    `deliver/whatsapp.registrar_envio` agregan esas tres claves a cada fila del
    registro. Sin esto la comparación corta/identidad y mail/WhatsApp no se puede hacer.
14. `lint`, en mail, saltea la firma (el último bloque) al calcular la oración más
    repetida. Objetivo mail v6: **< 35 %**.

### Textos

Van en `compose/lexicon.py` con tildes; `estilo_felipe` las saca al final.

```python
SALUDOS_MAIL_V6 = ("Hola, ¿qué tal?", "Hola, ¿cómo va?", "Buenas, ¿cómo estás?")
PRESENTACIONES_MAIL_V6 = (
    "Soy {nombre}, de La Plata, y hago webs para inmobiliarias.",
    "Me llamo {nombre} y me dedico a hacer webs para inmobiliarias.",
    "Te escribo por algo puntual de tu web. Soy {nombre} y hago webs para inmobiliarias.",
)
REPUTACION_MAIL_V6 = (
    "En Maps tenés {rep}: gente que te busca hay.",
    "Vi que tenés {rep} en Maps, así que demanda hay.",
)
# Prueba social verificada, sin identificar al cliente.
QUE_HAGO_MAIL_V6 = (
    "Ahora estoy armando la web de una inmobiliaria de Zona Norte, orientada a tasaciones.",
    "Hoy estoy terminando la web de una inmobiliaria de Zona Norte que la pidió pensada para captar propiedades.",
    "Es lo que estoy haciendo para una inmobiliaria de Zona Norte: una web pensada para que el que quiere vender pida la tasación.",
)
CIERRE_MAIL_V6 = (
    "Me lleva un par de horas armarlo. ¿Te lo paso para que lo veas? Sin compromiso.",
    "No tiene costo. ¿Querés que te lo mande?",
    "Lo armo en un par de horas. ¿Te lo mando y lo ves con calma?",
    "No te cobro el boceto. ¿Te lo paso y me decís qué te parece?",
)
IDENTIDAD_V6 = (
    "Te dejo mi LinkedIn por si querés ver quién soy: {enlace}",
    "Por si querés saber quién te escribe: {enlace}",
)
```

Ejemplo ficticio (`carga_lenta`):

```
Asunto: lo que tarda la web

Hola, que tal? Me llamo Felipe y me dedico a hacer webs para inmobiliarias.

Vi que tenes 4,8 con 120 reseñas en Maps, asi que demanda hay. Abri ejemplo.com.ar
y la portada tardo 4,6 segundos en aparecer, con una conexion normal. El que busca
casa tiene diez pestañas abiertas y cierra la que tarda.

Hoy estoy terminando la web de una inmobiliaria de Zona Norte que la pidio pensada
para captar propiedades.

Te armo un boceto de esa misma portada cargando rapido. Lo armo en un par de horas.
Te lo mando y lo ves con calma?

Felipe Joaquin Borrazas
Webs para inmobiliarias
https://www.linkedin.com/in/felipeborrazas/
+54 9 221 314 1648
```

## Criterio de aceptación

```
tests/test_plantilla_v6.py
```

```bash
py -m unittest tests.test_plantilla_v6 tests.test_whatsapp_v5 -v
```

En `test_whatsapp_v5.py`, tres asserts esperan `generado_por == "plantilla-whatsapp-v5"`
(`test_guarda_regla_y_version`, `test_recompone_v4_y_no_toca_enviados`,
`test_recompone_v4_aunque_tenga_email`): pasan a `plantilla-whatsapp-v6`. Es el único
cambio permitido en ese archivo.

Verificado con un prototipo descartable: los 18 tests nuevos fallan sobre `master` y
pasan junto con los 20 de la 009.

## Alcance

**Tocar:** `prospector/compose/mail_v6.py` (nuevo), `compose/lexicon.py`,
`compose/whatsapp.py`, `compose/writer.py` (`validar`, `redactar_todos`),
`models.py` (`EmailDraft.variante`), `deliver/__init__.py`, `deliver/mailer.py`,
`deliver/whatsapp.py`, `pipeline.py`, `lint.py`, los dos tests.

**No tocar:** el default de `send` (simula), `audit/`, el score, `.env`, ni los
borradores de leads ya enviados o respondidos.

**Tamaño:** el mínimo que haga pasar los tests. Sin config nueva.

## Cómo verificar que no se rompió nada

```bash
py -m unittest discover tests -q
py -m prospector compose --nicho inmobiliaria
py -m prospector lint
py -m prospector send --nicho inmobiliaria --limite 5    # simula: mirá 5 a ojo
```
