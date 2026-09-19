El mapa del proyecto está en @AGENTS.md — es la fuente de verdad, compartida con
Codex. Lo de acá abajo es solo el reparto de trabajo.

# Reparto

Tres modelos, repartidos por **costo**, no por capacidad.

| Trabajo | Quién |
|---|---|
| Leer N archivos, ubicar dónde vive X, triaje de logs, resumir un doc largo | Gemini, vía `/delegar` |
| Implementar contra una spec, tests, refactor mecánico, boilerplate | Codex |
| Criterio, arquitectura, voz, todo texto que ve un cliente | vos (Claude) |

Dos reglas que resumen todo:

- **No leas un archivo entero para encontrar una cosa.** Delegá la búsqueda y
  después verificá con `Read` sobre las líneas que te citaron.
- **No escribas código que un test puede verificar.** Escribí el test y la spec;
  la implementación es de Codex.
- **Lo más chico que funcione.** Antes de escribir, preguntá si hace falta que
  exista; después buscá en el repo, en la stdlib y en lo ya instalado. Borrar
  gana a agregar. La escalera completa está en `.claude/rules/codigo.md`.

## Handoff

Lo que decide si esto ahorra o duplica es el formato de la devolución. Si tenés
que releer la salida para confiar en ella, pagaste dos veces.

- **De Gemini** volvés con viñetas y números de línea. Verificá dos líneas con
  `Read` offset/limit, no el archivo.
- **De Codex** volvés con un test que pasa o falla. Leé el resultado del test,
  no el diff. El diff se mira cuando el test ya pasó.
- Codex trabaja en rama propia. Nunca en `master`.

Si `agy` no está en el PATH, decilo y seguí sin delegar. No pruebes variantes a
ciegas: cada intento fallido cuesta una espera completa.

## Specs

Toda tarea que vaya a Codex se escribe en `docs/tareas/NNN-nombre.md` con la
plantilla de `docs/tareas/_PLANTILLA.md`. El criterio de aceptación es un test,
no una descripción. Sin eso no hay handoff: hay una conversación más.

# El conocimiento ya no está acá

Migrado al vault de Obsidian el 18/09 y borrado del repo el 18/09. Si buscás
alguno de estos, no está: lo que decían vive en notas atómicas, y lo que había
que construir está en `docs/tareas/`.

| Archivo que ya no existe acá | Dónde está ahora |
|---|---|
| `PLAYBOOK_CIERRE.md` | vault → `Cierre/` (14 notas) |
| `INFORME_REDACCION*.md` | vault → `Redacción/` (7 notas) |
| `PLAN_OUTREACH_V3.md` | vault → `Prospección/` + specs 002-006 |
| `tfy_skill.md`, `corey_skill.md` | destilado en las notas; no migrado tal cual |

Los `Claude outputs/PROMPT_*` son el prompt del boceto de un cliente puntual:
abrí el de un cliente solo si la tarea es de ese cliente.

# Tareas pendientes

`docs/tareas/` tiene seis specs listas para Codex, con el test como criterio de
aceptación. Orden: **003 → 004** es dependencia dura (no se manda un seguimiento
sin saber quién respondió). 001 y 002 son independientes.

# Sesiones

Una sesión, un dominio. La que abrió el playbook de cierre no toca
`audit/rules.py`; la que está arreglando el auditor no abre las propuestas. El
contexto mezclado se arrastra hasta el final de la conversación y se paga en
cada turno.

# Antes de escribirle a alguien

Todo texto que sale hacia un prospecto o un cliente pasa por `py -m prospector
lint`. Y todo ejemplo que quede versionado va con datos ficticios: este repo es
público.
