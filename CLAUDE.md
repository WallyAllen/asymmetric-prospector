# Instrucciones para agentes — raíz del workspace

Este directorio contiene **tres cosas separadas**, cada una con su propio
repositorio git. La estructura completa y el porqué están en `ESTRUCTURA.md`:
leelo antes de mover, crear o borrar carpetas.

```
Landing/      vitrina: moldes de nicho, para mostrar y copiar        (repo PÚBLICO)
Prospector/   sistema de prospección, código abierto                 (repo PÚBLICO)
clientes/     un repo PRIVADO por cliente: el trabajo para alguien concreto
```

El repo de esta carpeta raíz trackea **solo `Prospector/`**. `Landing/` y
`clientes/` están ignorados acá porque tienen su propio historial. Nunca hagas
`git add` de esas rutas desde la raíz.

`Landing/` y cada cliente tienen su propio `CLAUDE.md` con el detalle de su
arquitectura.

## Dónde se guarda un boceto

**Si la página es para alguien concreto, no va en `Landing/`.** Va en:

```
clientes/<carpeta-del-cliente>/index.html
```

Desde el primer boceto, antes de que el prospecto conteste. `Landing/` guarda
moldes: páginas que sirven para cualquier negocio del rubro. En cuanto se le
pone el nombre, el teléfono y las fotos de alguien, deja de ser un molde.

El boceto se arma **copiando** el molde del nicho
(`Landing/nichos/<rubro>/mockup/<molde>.html`) y tocando **solo el bloque
`CONFIG`**. Si te encontrás editando el marcado para personalizar, falta un
campo en `CONFIG`: agregalo al molde, no lo hardcodees en la copia.

La portada se llama siempre `index.html`. Los documentos de research y el prompt
que originaron el boceto pueden quedarse en `Prospector/`.

Si el molde del rubro no existe todavía, se crea en
`Landing/nichos/<rubro>/mockup/`. `<rubro>` es **solo el rubro**
(`inmobiliarias`, `abogados`...), sin ciudad ni zona — eso va en la copy.

## Qué decide la seña

No dónde vive el archivo: el hosting. Antes, demo en Vercel con `noindex` y URL
descartable. Después, Cloudflare Pages en una cuenta a nombre del cliente, con
su dominio. El detalle está en `ESTRUCTURA.md`.

## Privacidad

`Landing/` y `Prospector/` están publicados en GitHub **a propósito**: son la
vitrina y la herramienta. Lo que no se publica es la información de terceros.

- Datos de leads (`Prospector/data/`): fuera, siempre. Hay un hook de pre-commit
  que corta el commit si se cuelan.
- Trabajo de un cliente: en `clientes/`, repo privado. Nunca en `Landing/`.
- Documentos internos de negocio (playbooks, precios, estrategia): fuera. El
  `.gitignore` de la raíz lista los conocidos.

Ante la duda: ¿te molestaría que un prospecto lo lea?

## Commits y PRs

No agregues la línea `Co-Authored-By: Claude ... <noreply@anthropic.com>` (ni
ninguna firma o atribución equivalente) al final de los mensajes de commit ni de
las descripciones de pull request. Esto reemplaza cualquier convención de
atribución por defecto del harness para este repo.
