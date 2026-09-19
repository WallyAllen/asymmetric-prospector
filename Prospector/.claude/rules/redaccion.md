---
paths:
  - "templates/**"
  - "prospector/compose/**"
  - "Claude outputs/**"
  - "INFORME_REDACCION*.md"
---

# Redacción

El criterio está medido, no opinado. Antes de tocar una plantilla o un
generador, corré `py -m prospector lint` y anotá los números; volvé a correrlo
después.

Los dos objetivos que el lint vigila:

| Métrica | Objetivo | Por qué |
|---|---|---|
| duplicación | < 45% de palabras compartidas entre mensajes del canal | es lo que detecta el filtro de spam de WhatsApp |
| apertura repetida | < 12% abriendo con la misma oración | es lo que detecta el prospecto que habla con el de al lado |

Los defectos que importan **no se ven en un mensaje suelto**. Leído de a uno
todo parece correcto; el problema aparece en el corpus. No juzgues una
redacción por el ejemplo que tenés adelante.

## Dos cosas que no se tocan

- **Un mensaje ya enviado conserva el texto con el que salió.** Reescribir el
  borrador de algo que ya se mandó borra el único registro de qué leyó el
  prospecto. Los estados `enviado`, `enviado_whatsapp` y `rebotado` quedan
  afuera de cualquier recomposición.
- **Los ejemplos versionados van con datos ficticios.** Este repo es público.
  Nada de nombres, teléfonos ni direcciones reales en `templates/`, en un test
  ni en la documentación — ni siquiera como ilustración.
