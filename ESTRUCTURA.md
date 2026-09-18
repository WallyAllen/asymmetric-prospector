# Estructura del workspace

> Reorganizado el 18/09/2026. Este archivo es la referencia: si algo no encaja
> con lo que dice acá, lo que está mal es la carpeta, no el documento.

## El mapa

```
.LandingPage/
├── Landing/      repo Landing-Page-Mockup    · PÚBLICO  · la vitrina: moldes de nicho
├── Prospector/   repo asymmetric-prospector  · PÚBLICO  · la herramienta, código abierto
└── clientes/     un repo PRIVADO por cliente · el trabajo hecho para alguien concreto
    ├── monte-propiedades/
    ├── libra-propiedades/
    └── portillo-kus/
```

El repositorio de la raíz trackea **solo `Prospector/`**. `Landing/` y
`clientes/` están en su `.gitignore`: cada uno maneja su historial.

## La regla, en una línea

**Si la página es para alguien concreto, no vive en la vitrina.**

| | Qué hay | Quién lo ve |
|---|---|---|
| `Landing/` | Moldes de nicho: el `veterinaria-aurora.html` que sirve para cualquier veterinaria | Cualquiera. Es el catálogo |
| `clientes/<cliente>/` | Su sitio, con su nombre, sus teléfonos, sus propiedades | Vos y el cliente |
| `Prospector/` | El código del sistema de prospección | Cualquiera. Los **datos** no salen (ver abajo) |

Un boceto entra en `clientes/` **desde el primer día**, antes de que el
prospecto conteste siquiera. No hace falta esperar a la seña: `git init` es
gratis, y lo que cuesta caro es lo otro — que el nombre, el teléfono y la
dirección de alguien que todavía no es cliente queden publicados en un repo que
existe para ser mirado.

### Por qué la vitrina es pública y el trabajo no

`Landing/` es pública porque **ese es el punto**: un prospecto que ve seis
nichos resueltos compra distinto que uno que ve un archivo suelto. `Prospector/`
es público porque el código es más útil mirado que escondido, y porque lo que
separa una prospección de un spam no es el script, es el criterio.

Lo que no es tuyo para publicar es la información de terceros: los negocios de
`data/`, que nunca pidieron aparecer, y los clientes, que te dieron sus datos
para hacerles una web, no para tenerlos en un repositorio abierto.

### Qué decide entonces la seña

No dónde vive el archivo: **el hosting**.

| | Antes de la seña | Después |
|---|---|---|
| Dónde | Vercel, plan gratis | Cloudflare Pages, plan gratis |
| URL | `<algo>.vercel.app`, descartable | El dominio del cliente |
| Indexación | `noindex` siempre | Indexable |
| Cuenta | Tuya | A nombre del cliente, administrada por vos |

Vercel Hobby **no permite uso comercial**: sirve para mostrar un boceto, no para
producción. Para servir un dominio sin `www` en Pages, los nameservers tienen
que estar en Cloudflare.

## Armar un boceto nuevo

```bash
# 1. Copiar el molde del nicho
mkdir clientes/<cliente>
cp Landing/nichos/<rubro>/mockup/<molde>.html clientes/<cliente>/index.html

# 2. Personalizar: se toca SOLO el bloque CONFIG del archivo.
#    Si te encontrás editando el marcado, falta un campo en CONFIG:
#    agregalo al molde, no lo hardcodees en la copia.

# 3. Repositorio propio
cd clientes/<cliente>
git init -b main && git add -A && git commit -m "Boceto de <Cliente>"

# 4. Remoto PRIVADO
gh repo create <cliente> --private --source=. --push
```

La portada se llama **`index.html`**, siempre: así la URL termina en `/` y no en
un nombre de archivo.

## Cuándo aparece un cliente en la galería

Cuando su sitio **ya está publicado** y el cliente aceptó que se muestre. La
card apunta a su URL real, nunca a un archivo del repositorio. Un boceto en
curso no se linkea.

Los contadores de la galería (`Landing/index.html`) se calculan solos contando
las cards: no hay números que actualizar a mano.

## Convenciones que no cambian

- El nombre de la carpeta de nicho es **solo el rubro** (`inmobiliarias`,
  `abogados`), sin ciudad. La ciudad va en la copy.
- Un molde de nicho es **un solo archivo HTML** autocontenido, salvo las
  excepciones Astro documentadas en `Landing/README.md`. Un proyecto con build
  propio (Astro, Next.js, un generador en Python) nunca va a la vitrina.
- Las imágenes van como archivos en una carpeta al lado, **nunca embebidas en
  base64**. Un HTML de 60 KB con doce JPG sueltos carga mejor y versiona mejor
  que un HTML de 3 MB.
- Fin de línea LF en todos los repos, fijado por `.gitattributes`.
- En `Prospector/`, el hook de pre-commit corta cualquier commit que se lleve
  datos de leads o un `.env`. Se activa una vez por clon:
  `git config core.hooksPath Prospector/scripts/hooks`.
