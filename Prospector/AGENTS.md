# Prospector — mapa para agentes

Prospección asimétrica: encuentra negocios cuya web pierde clientes, lo demuestra
con datos medidos y una captura señalada, y les escribe un mensaje que parece
escrito a mano. Todo local, sin SaaS de pago.

**Leé esto antes de explorar.** Si la respuesta está acá, no abras el repo.

```
minar ──▶ auditar ──▶ redactar ──▶ enviar
Maps      señales     anti-slop    SMTP con
+ web     + reglas    + captura    cuota y jitter
          + jurado IA anotada
```

## Comandos

```bash
py -m prospector mine "clinicas dentales valencia"   # 1 · minar
py -m prospector audit [--limite N] [--reanudar]     # 2 · auditar
py -m prospector compose [--forzar] [--sin-ia]       # 3 · redactar
py -m prospector send [--enviar-de-verdad --limite N]# 4 · enviar (simula por defecto)
py -m prospector run "fisioterapia sevilla"          # todo seguido
py -m prospector status                              # estado del embudo
py -m prospector lint                                # calidad de la redacción
py -m prospector report                              # informe HTML
py -m prospector respondio <clave> [--baja]          # contestó: fuera de la cola
pytest tests/                                        # la suite
```

`--sin-ia` apaga el jurado visual y la redacción con IA: el sistema funciona sin
`GEMINI_API_KEY`. `scripts/0X_*.py` son alias de compatibilidad, no lógica.

## Dónde vive cada cosa

| Ruta | Qué es |
|---|---|
| `prospector/cli.py` | único punto de entrada; argparse, sin lógica |
| `prospector/pipeline.py` | orquesta las cuatro etapas |
| `prospector/models.py` | `Lead`, `Audit` y los estados del embudo |
| `prospector/config.py` | settings + rutas de `data/`; todo lo configurable |
| `prospector/storage.py` | leer/escribir los JSON de `data/` |
| `prospector/sources/` | minado: `google_maps.py`, `search.py`, `contacts.py` |
| `prospector/audit/` | medición: `rules.py` (el score), `capture.py`, `signals.py`, `vision.py` |
| `prospector/compose/` | redacción: `writer.py`, `whatsapp.py`, `lexicon.py` |
| `prospector/deliver/` | envío: `mailer.py`, `whatsapp.py`, `quota.py` |
| `tests/` | `test_core.py`, `test_migracion.py`, `test_salida.py` |
| `data/0X_*/` | el embudo en JSON, por etapa |
| `templates/` | plantillas de mensaje |

Los dos archivos que concentran el criterio del sistema son
`audit/rules.py` (673 líneas: qué hace valioso a un lead) y
`compose/writer.py` (859 líneas: cómo se escribe). Casi todo cambio de
comportamiento real pasa por uno de esos dos.

## Invariantes

1. **Toda etapa es idempotente y reanudable.** Cortar con Ctrl+C y retomar no
   duplica trabajo ni vuelve a gastar en IA. Cualquier cambio que rompa esto
   está mal, aunque pasen los tests.
2. **El score no lo pone la IA.** Lo suman reglas sobre datos medidos en un
   navegador real. La IA es un jurado accesorio, nunca la fuente del número.
3. **El score mide una sola cosa**: si la web le está costando clientes al
   negocio, hoy, de forma demostrable. No mide calidad ni buenas prácticas.
   `killer` 18-38 · `moderado` 4-10 · `cosmético` 0-4. Toda la pila de
   cosméticos junta no cruza el umbral de contacto.
4. **`send` simula por defecto.** Enviar de verdad exige `--enviar-de-verdad`.
   No cambies ese default ni lo saltees en un test.

## Datos de terceros

`data/` tiene nombres, teléfonos y direcciones de negocios reales que nunca
pidieron aparecer, y **este repo es público**. El hook de pre-commit
(`scripts/hooks/pre-commit`) corta el commit si entra algo de `data/`, un `.env`
o algo que parezca una clave. Se activa una vez por clon:

```bash
git config core.hooksPath Prospector/scripts/hooks
```

Nunca pegues contenido de `data/` en un archivo versionado, en un ejemplo ni en
un test. Los ejemplos van con datos ficticios.

## Git

El repositorio **no está acá**: la raíz es `F:\.Proyectos\.LandingPage`, y
trackea `Prospector/`. Para cualquier `git`, subí un nivel. Las webs de clientes
viven en `clientes/<cliente>/`, repos privados aparte — nunca en este repo.

## Qué no abrir

`scripts/venv/` son 14.661 archivos de dependencias. `data/screenshots/` son
800 MB de PNG. Ninguno de los dos se lee para entender el proyecto.
