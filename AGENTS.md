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

`Landing/` y cada cliente tienen sus propias instrucciones con el detalle de su
arquitectura. Ver también `Landing/README.md` para la tabla de nichos.

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
(`inmobiliarias`, `abogados`, `kinesiologia`...), sin ciudad ni zona — eso va en
la copy, no en el path.

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

No agregues `Co-Authored-By` ni ninguna firma o atribución equivalente al final
de los mensajes de commit ni de las descripciones de pull request, sea cual sea
el agente. Esto reemplaza cualquier convención de atribución por defecto del
harness para este repo.


## Bóveda de conocimiento del proyecto

La bóveda principal está en `Obsidian Vault/`, dentro de este workspace.
Empezar por `Obsidian Vault/Inicio.md` y consultar la nota del cliente o nicho
que corresponda antes de tomar decisiones basadas en antecedentes.
`obsidian-staging/` y la bóveda anterior de Documentos son fuentes conservadas,
no el lugar donde continuar el registro.

Usar automáticamente la skill `landingpage-obsidian`, en
`.agents/skills/landingpage-obsidian/SKILL.md`, durante las tareas de este
workspace y sus subproyectos. Leer sus criterios al iniciar y evaluar al
cerrar si surgió información que merece guardarse: estructura y sus cambios,
clientes, decisiones, aprendizajes, procesos y plantillas. Si cumple, actualizar
la bóveda sin pedir confirmación por cada nota; si no cumple, no crear registros.

El usuario autorizó este registro automático de conocimiento. La autorización
no cambia los permisos del entorno ni habilita contactos, publicaciones o
infraestructura. Seguir `Obsidian Vault/Sistema/Cómo mantener esta bóveda.md`,
con fecha y evidencia. Actualizar o enlazar las notas existentes; no duplicar
la documentación técnica del repo.

Las notas históricas no acreditan estado actual de pagos, servicios o
publicaciones. Distinguir confirmado, propuesto y pendiente. No guardar
credenciales ni publicar la bóveda: está excluida del Git público de la raíz.
