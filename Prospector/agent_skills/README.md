# 🤖 Agent Skills de prospección

Skills globales que usa el proyecto:

- `scrapling-official` — minado sigiloso de Google Maps y extracción de contactos.
- `playwright-cli` — auditoría técnica y capturas multi-viewport.
- `humanizer` — criterio anti-slop; sus patrones están implementados en
  `prospector/compose/writer.py` (`FRASES_PROHIBIDAS`, `limpiar()`).
- `page-cro` — vocabulario de conversión que alimenta los argumentos de `rules.py`.

## Pendientes útiles

- `nicho_researcher.md` — dado un nicho, proponer las consultas de Maps que mejor
  rinden (ciudad + servicio + modificadores) y los umbrales de score adecuados.
- `respondedor.md` — qué hacer cuando el prospecto contesta: calificar la respuesta
  y disparar el mockup del nicho.
