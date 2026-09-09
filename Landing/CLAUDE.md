# Landing — instrucciones para agentes

Biblioteca de landing pages autocontenidas: un `.html` por página, CSS y JS inline,
sin build ni dependencias. La estructura de carpetas, el funcionamiento del bloque
`CONFIG` y los estándares de diseño están en `README.md` — leelo antes de tocar un
mockup por primera vez en la sesión.

## Economía de contexto (regla dura)

Cada mockup pesa ~1300 líneas / ~78 KB ≈ **~22k tokens**. Leerlo entero o
reescribirlo es, por lejos, la operación más cara del repo. Por lo tanto:

1. **Nunca reescribas un mockup completo.** Toda modificación va con ediciones
   puntuales (`Edit` / `str_replace`), aunque toques varias secciones. Un `Write`
   del archivo entero se justifica sólo al crear un mockup nuevo desde cero.
2. **No leas el archivo entero para un cambio local.** Ubicá primero con
   `grep -n` la sección, el token o el campo que vas a tocar, y leé sólo ese rango
   (`Read` con `offset`/`limit`, o `sed -n 'A,Bp'`). Leer completo se justifica
   sólo en una auditoría de diseño de la página entera.
3. **Personalizar para un prospecto = tocar sólo `CONFIG`.** Copiá el molde del
   nicho, localizá el bloque con `grep -n "CONFIG"`, leé ese rango y editá ahí.
   Si te encontrás editando el marcado para personalizar, es señal de que falta un
   campo en `CONFIG`: agregalo al molde, no hardcodees en la copia del cliente.
4. **No vuelques HTML en el chat.** Ni el archivo ni secciones largas. Reportá qué
   cambiaste y en qué líneas; el resultado se mira en el navegador.
5. **Verificá con comandos, no releyendo.** Overflow, contraste, tokens huérfanos,
   `alt` faltantes, links rotos: resolvelo con `grep` o un script corto.

## Elección de modelo

- **Opus** — decisiones de diseño del molde, arquitectura de `CONFIG`, dirección de
  arte, revisión final.
- **Sonnet** — implementación, ediciones de `CONFIG`, ajustes de CSS,
  personalizaciones por cliente. Es el default para trabajo de ejecución.
- **Subagentes** — toda tarea que lea mucho y devuelva poco (auditorías, búsquedas,
  extracción de copy) va a un subagente, así el contexto principal no carga los
  archivos.
- **Gemini CLI** — trabajo mecánico y verificable, cuando conviene. El
  procedimiento está en la skill `delegar-a-gemini`; consultala antes de invocarlo.

## Qué no se delega a un modelo externo

El producto de este repo es el diseño. Jerarquía tipográfica, paleta y tokens de
color, verificación de contraste WCAG, microinteracciones, copy de conversión y la
estructura de un molde nuevo se hacen acá, con Claude. Un modelo externo puede
preparar insumos y auditar, no decidir el diseño.

## Integridad del contenido

Las reseñas y testimonios de las plantillas son de ejemplo y están marcados como
tales. Al personalizar se reemplazan por reseñas reales de Google. Nunca se
presentan testimonios inventados como genuinos, ni se publican datos de contacto,
precios o credenciales que no haya provisto el cliente.
