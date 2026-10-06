---
name: landingpage-obsidian
description: >-
  Registrar automáticamente el conocimiento duradero de LandingPage en su bóveda de Obsidian
  al trabajar en Landing, Prospector o clientes: estructura y sus cambios, contexto de clientes,
  decisiones, aprendizajes, procesos y plantillas. Usar al cerrar trabajo relevante o recibir
  información confirmada del proyecto; omitir intercambios triviales y registros técnicos sin valor para retomar.
---

# Conocimiento del proyecto en Obsidian

## Ubicación y alcance

- Workspace: `F:\.Proyectos\.LandingPage`.
- Única bóveda principal: `F:\.Proyectos\.LandingPage\Obsidian Vault`.
- Esta skill: `F:\.Proyectos\.LandingPage\.agents\skills\landingpage-obsidian`.

Aplicar durante las tareas de este workspace y sus subproyectos. El usuario
autorizó guardar automáticamente lo que cumpla los criterios de abajo; no
pedir confirmación para cada nota. Respetar permisos de escritura del entorno
y cualquier pedido posterior de no guardar un contenido. Esta autorización
no habilita contactos, publicaciones, cambios de infraestructura ni escritura
en las memorias globales de Codex.

La skill funciona como parte del trabajo del agente; no instala un observador,
plugin de Obsidian ni tarea en segundo plano. Obsidian puede estar cerrado:
los archivos Markdown son suficientes y el CLI es opcional.

## Qué merece guardarse

Guardar si el contenido pertenece al proyecto, tiene evidencia identificable
y cambia lo que otro agente o el usuario necesita saber para continuar:

| Información | Destino principal |
|---|---|
| Estructura real, carpetas, repositorios, responsabilidades o cambios de ubicación | `Mapa del proyecto.md`; conservar el motivo/antecedente si cambia una regla |
| Material recibido, acuerdos, etapa, preferencias, contexto, pendientes y siguiente paso de un cliente/prospecto | `Clientes/<nombre>.md` o subnota de ese cliente |
| Elección entre alternativas, nueva regla o cambio de criterio con motivo | `Decisiones/` y `Decisiones/00 Decisiones.md` |
| Hallazgo o fallo con una enseñanza aplicable de nuevo | `Aprendizajes/` y su índice; si es específico del nicho, `Nichos/<nicho>/` |
| Método repetible, pasos operativos o cambio de un proceso existente | `Procesos/` y `Procesos/00 Procesos.md`; usar `Cierre/`, `Prospección/` o `Redacción/` si ahí ya vive el tema |
| Formato reutilizable aprobado para futuras notas o entregables | `Plantillas/`; conservar instrucciones de uso donde corresponda |

No guardar saludos, preguntas aisladas sin conclusión, cambios cosméticos sin
criterio nuevo, logs completos, diffs, HTML, conversaciones enteras, errores
transitorios ya resueltos sin enseñanza, hipótesis sueltas ni contenido ya
registrado. No crear una nota diaria o un aprendizaje para justificar cada
cambio. Usar `Diario/` sólo si aporta contexto entre varias notas.

Una propuesta relevante puede registrarse como **propuesta**, y una
incertidumbre que bloquee el trabajo como **pendiente**. No presentarlas como
decisiones, acuerdos o implementaciones confirmadas.

## Cómo registrar

1. **Identificar el hecho y su fuente.** Usar la instrucción del usuario,
   respuesta real del cliente, archivo local, resultado de prueba o servicio
   efectivamente comprobado. No convertir una tarea planificada en realizada.
   Fecha según el contexto del usuario, en `America/Buenos_Aires`.
2. **Ubicar la nota existente.** Consultar `Inicio.md`, el índice pertinente
   y buscar títulos o términos del caso con `rg`. Leer sólo las notas y rangos
   necesarios. No recorrer la bóveda ni mockups completos para documentar.
3. **Actualizar antes que duplicar.** Editar puntualmente la nota que ya
   contiene el tema. Para un hecho nuevo, añadir una entrada con fecha. Si
   cambia una decisión, registrar qué cambió y por qué; conservar su
   antecedente. No modificar `Historial/` ni snapshots recuperados para hacerlos
   parecer actuales: actualizar la entrada vigente o crear una continuación
   enlazada. Si el usuario pide rectificar un antecedente, conservar trazabilidad.
4. **Crear sólo cuando haga falta.** Usar la plantilla correspondiente de
   `Plantillas/`, completar campos con información real y quitar instrucciones
   o marcadores sin completar. Agregar frontmatter con título, tipo, fecha o
   actualizado, estado y tag `landingpage`, siguiendo la nota/plantilla existente.
   No cambiar la estructura completa de notas previas sólo para uniformarlas.
   Si falta una plantilla específica, seguir el estilo de las notas existentes;
   crear otra plantilla sólo cuando se haya definido un formato reutilizable.
5. **Escribir lo mínimo útil.** Qué pasó/cambió, motivo o consecuencia, fecha,
   evidencia, límite de verificación y próximo paso/responsable si aplica.
   Mantener separado **confirmado / propuesto / pendiente**. Un build o push no
   acredita producción, y una nota antigua no acredita pagos ni servicios vigentes.
6. **Conectar.** Enlazar la nueva nota desde el índice pertinente y el caso de
   origen. Usar wikilinks con ruta relativa a la bóveda, sin `.md`, para evitar
   ambigüedad; apuntar a destinos reales. Actualizar `Inicio.md` sólo si cambia
   la navegación principal. No repetir el mismo texto en varias categorías.
7. **Comprobar y cerrar.** Verificar el cambio guardado, los enlaces agregados
   y ausencia de duplicados. Si se pidió un cambio de estructura, contrastar
   el mapa con las carpetas reales; no moverlas como parte de esta skill.
   En la respuesta final mencionar brevemente qué se registró y enlazar la
   nota, sin volcar su contenido ni afirmar éxito sin escritura verificada.

Si no hay información que califique, terminar la tarea sin crear registros
vacíos ni anunciar que se omitió el guardado. Si falta evidencia crítica,
guardar sólo el pendiente útil y continuar lo que no dependa de resolverlo.

## Límites de contenido y permisos

La bóveda es privada y está excluida del Git público de la raíz. No guardar
contraseñas, tokens, códigos de acceso, `.env`, bases de leads, documentos
personales completos ni datos personales innecesarios. Una nota comercial
puede conservar el contexto confirmado que requiere continuar el trato;
no copiar registros masivos ni llevarlos a repositorios públicos.

Si falta la bóveda, no usar `obsidian-staging` ni crear otra en Documentos.
Informar la ubicación esperada y comprobar la carpeta antes de reconstruirla.
Si el entorno exige autorización para escribir, preparar el cambio y pedir
el permiso de escritura correspondiente. Conservarlo pendiente y explicar
la limitación si se deniega. No cambiar de destino para eludirla.

Para casos de clasificación dudosos, consultar
[references/criterios.md](references/criterios.md). Las instrucciones actuales
del usuario y del subproyecto prevalecen sobre criterios históricos de la bóveda.
