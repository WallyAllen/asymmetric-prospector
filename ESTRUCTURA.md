# Estructura del workspace

> Reorganizado el 18/09/2026. Este archivo es la referencia: si algo no encaja
> con lo que dice acá, lo que está mal es la carpeta, no el documento.

## El mapa

```
.LandingPage/
├── Landing/      repo: Landing-Page-Mockup   · PÚBLICO  · la vitrina
├── Prospector/   repo: asymmetric-prospector · la máquina de prospección
└── clientes/     una carpeta y un repo por cliente · PRIVADOS
    ├── monte-propiedades/
    └── libra-propiedades/
```

Tres cosas distintas que antes estaban mezcladas:

| Carpeta | Qué es | Quién la mira |
|---|---|---|
| `Landing/` | Moldes de nicho + bocetos de prospectos que todavía no pagaron | Vos, y prospectos a los que les mandás un link |
| `Prospector/` | Scripts, datos de leads, plantillas de mensajes | Solo vos |
| `clientes/` | Trabajo pago. Un repositorio por cliente | Vos y el cliente |

El repositorio de `.LandingPage/` (la raíz) trackea **solo `Prospector/`**.
`Landing/` y `clientes/` están en su `.gitignore`: cada uno maneja su historial.

## La regla de corte: la seña

**Antes de la seña**, un boceto vive en la biblioteca:

```
Landing/nichos/<rubro>/landings/<cliente>/
```

Es barato, descartable y no cuesta nada armarlo. De cada diez bocetos, la
mayoría no cierra: no tiene sentido montar repositorio y hosting para cada uno.

**Cuando entra la seña**, el proyecto se gradúa:

```
clientes/<cliente>/     ← repositorio propio, privado, deploy propio
```

### Por qué se muda (y no se queda todo en la biblioteca)

1. **La URL.** En la biblioteca, el cliente recibe
   `…/nichos/inmobiliarias/landings/monte-propiedades/monte-portada.html`:
   larga, con la taxonomía interna a la vista, y terminada en `.html`.
   Con repo propio es `monte-propiedades.pages.dev/`, y el día que se conecta
   el dominio del cliente no hay que mover nada — se apunta el dominio al mismo
   proyecto y la URL pasa a ser `montepropiedades.com.ar/`.

2. **Es un entregable.** Un repositorio propio se transfiere, se le da acceso
   al cliente, y el historial de commits se lee como el registro del trabajo
   hecho. Mezclado con 12 mockups de otros rubros, no.

3. **Privacidad.** `Landing/` es público. Los teléfonos, direcciones y
   propiedades reales de un cliente que paga no van ahí.

4. **El deploy no arrastra la galería.** Cada cliente publica solo lo suyo.

5. **Aísla el riesgo.** Romper la vitrina no rompe el sitio de un cliente que
   ya pagó, y al revés.

### Por qué no se hace repo propio desde el primer boceto

Porque el 80% de los bocetos no cierra, y cada repo nuevo son minutos de setup
más un proyecto de hosting más una URL que después hay que dar de baja. Y
porque la galería (`Landing/index.html`) **es el argumento de venta**: un
prospecto que ve seis nichos resueltos compra distinto que uno que ve un
archivo suelto.

### La excepción técnica

Un proyecto que **no sea un HTML autocontenido** — Astro, Next.js, cualquier
cosa con `node_modules` y build propio — va a `clientes/` desde el día uno,
aunque no haya seña. `Landing/` es una biblioteca de archivos únicos; meter un
`node_modules` adentro rompe el deploy estático y hace lento hasta un `find`.
Libra Propiedades está en `clientes/` por esto, no por la seña.

## Cómo graduar un cliente

Desde `.LandingPage/`, con `<cliente>` el nombre de la carpeta:

```bash
# 1. Mover (instantáneo: es el mismo disco)
mv Landing/nichos/<rubro>/landings/<cliente> clientes/<cliente>

# 2. La portada tiene que llamarse index.html, para que la URL no termine en .html
cd clientes/<cliente> && mv <lo-que-sea>.html index.html

# 3. Repositorio propio
git init -b main && git add -A && git commit -m "Sitio de <Cliente>"

# 4. Crear el repo PRIVADO en GitHub y publicar
#    gh repo create <cliente> --private --source=. --push

# 5. En Landing: registrar la baja y sacar la card si la tenía
cd ../../Landing && git add -A && git commit -m "refactor: <cliente> pasa a clientes/"
```

Y en `Landing/index.html`: la card del cliente vuelve **recién cuando el sitio
está publicado** y el cliente aceptó que se muestre, apuntando a su URL real.
Nunca a un archivo de este repositorio.

## Hosting

- **Boceto / demo:** Vercel, gratis, con `noindex` puesto. La URL es descartable.
- **Producción:** Cloudflare Pages en una cuenta a nombre del cliente,
  administrada por vos. El plan gratis permite uso comercial; Vercel Hobby no.
- **Dominio:** la cuenta va a nombre del cliente. Para un dominio sin `www` en
  Pages, los nameservers tienen que estar en Cloudflare.

## Convenciones que no cambian

- El nombre de la carpeta de nicho es **solo el rubro** (`inmobiliarias`,
  `abogados`), sin ciudad. La ciudad va en la copy.
- Un mockup de nicho es **un solo archivo HTML** autocontenido, salvo las
  excepciones Astro ya documentadas en `Landing/README.md`.
- Las imágenes van como archivos en una carpeta al lado, **nunca embebidas en
  base64**. Un HTML de 60 KB con doce JPG sueltos carga mejor y versiona mejor
  que un HTML de 3 MB.
- Fin de línea LF en los tres repos, fijado por `.gitattributes`.
