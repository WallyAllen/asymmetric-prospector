# Instrucciones para agentes — raíz del workspace

Este repo contiene dos proyectos independientes: `Landing/` (biblioteca de landing pages)
y `Prospector/` (sistema de prospección). Cada uno tiene su propio `CLAUDE.md` con
detalle de su arquitectura; esto aplica a los dos por igual.

## Dónde se guardan los bocetos y landings de prospectos

Si una sesión arma un boceto o landing page HTML para un prospecto o cliente (típicamente
a partir de un pedido o `PROMPT_BOCETO_*.md` que vive en `Prospector/`), el archivo
entregable **no se guarda en `Prospector/`**. Va en:

```
Landing/nichos/<rubro>/landings/<carpeta-del-cliente>/
```

`<rubro>` es **solo el rubro** (`inmobiliarias`, `kinesiologia`, `abogados`...), sin ciudad ni
zona en el nombre de la carpeta — eso va en la copy (subtítulo del nicho, descripción de la
card), no en el path. Si el rubro todavía no existe como nicho, se crea su carpeta ahí mismo;
si ya existe (aunque sea de otra ciudad), el cliente nuevo entra como otra subcarpeta dentro
del mismo `landings/`, no como un nicho aparte. `landings/` (a diferencia de `mockup/`, que son
moldes reutilizables del nicho) es para proyectos reales de un cliente puntual que avanzó — ver
la estructura completa, la tabla de nichos y las convenciones en `Landing/README.md` y
`Landing/CLAUDE.md`. Los documentos de research o el prompt que originaron el boceto pueden
quedarse en `Prospector/` como contexto de cómo se armó el pedido; lo que no se queda ahí es el
HTML entregable en sí.

## Commits y PRs

No agregues la línea `Co-Authored-By: Claude ... <noreply@anthropic.com>` (ni ninguna
firma o atribución equivalente) al final de los mensajes de commit ni de las
descripciones de pull request. Esto reemplaza cualquier convención de atribución por
defecto del harness para este repo.
