# Instrucciones para agentes — raíz del workspace

Este directorio contiene **tres cosas separadas**, cada una con su propio
repositorio git. La estructura completa y el porqué están en `ESTRUCTURA.md`:
leelo antes de mover, crear o borrar carpetas.

```
Landing/      vitrina: moldes de nicho + bocetos de prospectos sin seña   (repo PÚBLICO)
Prospector/   sistema de prospección: scripts, datos de leads, mensajes
clientes/     un repo privado por cliente con seña pagada
```

El repo de esta carpeta raíz trackea **solo `Prospector/`**. `Landing/` y
`clientes/` están ignorados acá porque tienen su propio historial. Nunca hagas
`git add` de esas rutas desde la raíz.

`Landing/` y cada cliente tienen su propio `CLAUDE.md` con el detalle de su
arquitectura.

## Dónde se guarda un boceto o landing

Si una sesión arma un boceto o landing HTML para un prospecto (típicamente a
partir de un `PROMPT_BOCETO_*.md` que vive en `Prospector/`), el entregable
**no se guarda en `Prospector/`**. Va en:

```
Landing/nichos/<rubro>/landings/<carpeta-del-cliente>/
```

`<rubro>` es **solo el rubro** (`inmobiliarias`, `kinesiologia`, `abogados`...),
sin ciudad ni zona — eso va en la copy, no en el path. Si el rubro no existe
como nicho, se crea ahí mismo; si ya existe (aunque sea de otra ciudad), el
cliente nuevo entra como otra subcarpeta del mismo `landings/`. Los documentos
de research y el prompt que originaron el boceto sí pueden quedarse en
`Prospector/` como contexto.

## Cuándo un cliente sale de la biblioteca

**Cuando paga la seña.** Ahí el proyecto se muda a `clientes/<cliente>/` con
repositorio propio, privado, y deploy propio. El procedimiento paso a paso está
en `ESTRUCTURA.md`.

Excepción: un proyecto con build propio (Astro, Next.js, cualquier cosa con
`node_modules`) va a `clientes/` desde el día uno, aunque no haya seña.

No muevas un cliente por tu cuenta: preguntá si la seña entró.

## Privacidad

`Landing/` y `Prospector/` están publicados en GitHub. Antes de commitear algo
nuevo en ellos, preguntate si te molestaría que lo lea un prospecto. Datos de
leads, plantillas de mensajes con precios, documentos de estrategia y datos
reales de clientes **no van a un repo público**. El `.gitignore` de la raíz ya
lista los documentos internos conocidos.

## Commits y PRs

No agregues la línea `Co-Authored-By: Claude ... <noreply@anthropic.com>` (ni
ninguna firma o atribución equivalente) al final de los mensajes de commit ni de
las descripciones de pull request. Esto reemplaza cualquier convención de
atribución por defecto del harness para este repo.
