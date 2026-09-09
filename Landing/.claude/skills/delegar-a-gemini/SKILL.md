---
name: delegar-a-gemini
description: Delegar trabajo mecánico y verificable de este repo a Gemini CLI para ahorrar contexto. Usar cuando una tarea exija leer o recorrer mockups completos y devuelva un resultado chequeable — auditorías (overflow a 375px, contraste, alt faltantes, tokens huérfanos), extracción de copy o de campos CONFIG, variantes de texto, portar un molde a otro nicho cambiando sólo contenido, o digerir referencias externas largas. NO usar para decisiones de diseño, paleta, tipografía, microinteracciones ni para crear un molde nuevo.
---

# Delegar a Gemini CLI

## Por qué existe

Un mockup de este repo son ~78 KB (~22k tokens). Hay tareas que obligan a recorrer
el archivo entero varias veces y cuyo resultado, en cambio, es corto y objetivo.
Ese es el único caso donde delegar afuera gana: **Gemini lee y escribe los archivos
por su cuenta, y a vos te devuelve un informe corto.** Si el contenido del archivo
tiene que pasar por tu contexto para ir o para volver, no hay ahorro — hacelo vos.

## Cuándo delegar

Delegá sólo si la tarea cumple **las tres** condiciones:

1. **Lee mucho, devuelve poco.** El insumo son cientos de líneas; la salida es una
   lista, un diff acotado o un archivo nuevo.
2. **El resultado es verificable con un comando.** Podés confirmar si está bien con
   `grep`, un script corto o abriendo la página — sin releer todo el HTML.
3. **No decide diseño.** Aplica una regla, no elige.

Ejemplos que califican:

- Auditar un mockup buscando overflow horizontal a 375px, `img` sin `alt`, custom
  properties declaradas y nunca usadas, o anclas rotas.
- Extraer todos los strings de copy visible a un `.md` para revisión.
- Generar N variantes de headline o de CTA a partir de una consigna (vos elegís
  cuál entra).
- Portar un mockup a otro nicho cambiando **sólo** contenido de `CONFIG`, con el
  marcado y los tokens intactos.
- Resumir referencias externas largas (varios competidores, documentación) y
  devolver una síntesis de una página.

## Cuándo NO delegar

- Decisiones de diseño: paleta, escala tipográfica, espaciado, jerarquía visual.
- Verificación final de contraste WCAG y de accesibilidad (Gemini la reporta; la
  decisión y el fix quedan acá).
- Crear un molde nuevo o reestructurar uno existente.
- Copy final de conversión.
- Cualquier cosa donde no sepas de antemano cómo vas a chequear el resultado.

Si dudás, no delegues: el ida y vuelta más la revisión cuesta más que hacerlo bien
de una.

## Cómo invocar

Gemini CLI corre en la máquina del usuario. La primera vez en el proyecto,
confirmá que está disponible y con qué flags:

```bash
gemini --version && gemini --help | head -40
```

Si el comando no existe, decíselo al usuario en una línea (se instala con
`npm install -g @google/gemini-cli` y requiere autenticarse una vez) y seguí con el
plan normal sin delegar. No intentes instalarlo por tu cuenta.

El patrón de invocación es **no interactivo, con el brief en un archivo**, para no
pelear con el escapeo ni inflar la línea de comando:

```bash
# 1. Escribí el brief (ver contrato abajo) en un archivo temporal
#    .gemini/task.md  — está gitignoreado
# 2. Ejecutá desde la raíz del repo, para que Gemini vea las rutas relativas
gemini -p "$(cat .gemini/task.md)" > .gemini/out.md 2>&1
# 3. Leé SOLO el informe
head -60 .gemini/out.md
```

Notas de operación:

- Ejecutá siempre desde la raíz del proyecto: el brief usa rutas relativas.
- Trabajá sobre una copia o con el árbol limpio en git, así `git diff` te muestra
  exactamente qué tocó y podés revertir con `git checkout -- <archivo>`.
- Si la corrida pasa de un par de minutos, cortala y hacelo vos.

## Contrato del brief

El brief que le escribís a Gemini debe tener siempre estas seis partes. Sin ellas,
vuelve trabajo genérico y perdés el ahorro revisando.

1. **Contexto en dos líneas.** Qué es el repo: landing pages en un único HTML
   autocontenido, CSS y JS inline, sin build, sin frameworks.
2. **Rutas exactas** de los archivos a leer y a escribir. Nunca pegues el contenido.
3. **La tarea, como regla mecánica.** Qué buscar o qué transformar, con el criterio
   explícito. Nada de "mejorá" ni "hacelo más lindo".
4. **Restricciones duras.** Copiá estas tal cual:
   - No cambies el marcado, las clases, ni los nombres de custom properties.
   - No agregues dependencias, ni CDN, ni frameworks.
   - No reformatees ni reindentes lo que no era parte de la tarea.
   - No toques nada fuera de las rutas indicadas.
   - No inventes datos de contacto, precios, ni reseñas: dejá el placeholder.
5. **Formato de salida, corto y fijo.** Por ejemplo: "devolvé una tabla markdown con
   columnas archivo | línea | problema | fix sugerido, máximo 40 filas, y nada más".
   Prohibí explícitamente devolver el HTML.
6. **Cómo se verifica.** Decile con qué comando vas a chequear su trabajo. Saber que
   hay un check objetivo mejora bastante lo que entrega.

## Verificación (no es opcional)

Antes de dar por buena la delegación:

```bash
git diff --stat            # ¿tocó sólo lo que debía?
git diff -- <archivo>      # ¿el cambio es el esperado?
```

Y corré el check objetivo que corresponda a la tarea (el grep, el script, o abrir
la página en el navegador). Si el diff toca archivos o líneas fuera de alcance,
revertí entero con `git checkout --` y rehacelo vos: no vale la pena rescatar una
corrida sucia a mano.

**Regla de corte:** si una misma delegación falla la verificación dos veces,
dejá de delegar esa tarea y resolvela acá. El presupuesto de contexto que ahorrás
delegando se evapora en el tercer intento.

## Alternativa más barata

Antes de salir del ecosistema, evaluá un subagente de Claude: quema su propio
contexto y te devuelve sólo la conclusión, sin fricción de integración, sin
re-explicar las convenciones del repo y con el mismo criterio de diseño. Para casi
todas las auditorías internas alcanza. Gemini gana cuando el insumo es enorme y
externo (muchas referencias, documentación larga) o cuando el volumen mecánico es
grande y repetitivo.
