# Casos de clasificación

| Situación | Registro adecuado |
|---|---|
| Se movió la bóveda o se cambió la separación entre repositorios | Actualizar `Mapa del proyecto.md`; registrar decisión/motivo si cambia el criterio. Verificar rutas reales. |
| El cliente confirmó alcance, material, una preferencia o un pago | Actualizar su nota con fecha y fuente; el pago requiere confirmación explícita, no intención de pagar. |
| El agente propuso un adicional y todavía no recibió respuesta | Conservar como propuesta relevante en la nota del cliente; no como acuerdo o trabajo contratado. |
| Se terminó código, pero no se probó el servicio externo | Registrar implementación local si cambia cómo retomar y mantener integración/publicación pendiente. No dar por operativa. |
| Se encontró una causa no obvia o un patrón repetido que deja una enseñanza reutilizable | Crear o ampliar aprendizaje: síntoma, causa comprobada, solución, prevención y evidencia. Un servidor detenido sin una enseñanza nueva se omite. |
| Se cambió un color porque el anterior fallaba contraste y se comprobó el nuevo | Registrar criterio en la nota del nicho o aprendizaje si será reutilizable; no crear una nota por cada token cambiado. |
| Se ajustó un margen o se corrigió una errata sin consecuencia posterior | Omitir. |
| Se actualizó un proceso de publicación, verificación o entrega | Actualizar el proceso existente y enlazar el caso. Conservar qué cambió y las condiciones de uso. |
| Se acordó una nueva estructura de ficha de cliente | Editar la plantilla pertinente y documentar el motivo en el proceso que la usa. No convertir el texto particular de un cliente en una plantilla universal. |
| La nota existente ya contiene el mismo hecho y evidencia | Omitir la duplicación. Actualizar sólo si cambió el estado, evidencia, alcance o próximo paso. |
| Hay una clave de API o una lista completa de contactos en la salida | No copiarla a la bóveda; registrar sólo el criterio o pendiente sin secretos ni datos masivos. |

## Casos que requieren contexto

**Cambio de arquitectura propuesto:** escribir «propuesto», motivo y validación
pendiente en el caso; sólo crear una decisión vigente cuando haya elección
confirmada. No aplicar la propuesta al código por el mero hecho de registrarla.

**Nota histórica que contradice un acuerdo nuevo:** actualizar la entrada
vigente con fecha y fuente, enlazar el antecedente y explicar qué reemplaza.
No borrar la historia ni reejecutar prompts recuperados sin contrastar.

**Verificación negativa útil:** si no se pudo confirmar un despliegue o una
cuenta y eso bloquea el siguiente paso, guardar qué falta comprobar. No
guardar todos los intentos ni diagnosticar una causa sin evidencia.

**Información ya dada por el usuario:** no volver a pedir aprobación para
registrarla cuando sea relevante al proyecto. Si el dato es sensible,
conservar sólo lo necesario para el trato y nunca claves o códigos.
