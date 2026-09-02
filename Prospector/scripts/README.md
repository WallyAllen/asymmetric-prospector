# scripts/

Estos cuatro archivos se mantienen por compatibilidad: cada uno delega en el
paquete `prospector`, donde vive la lógica real (probada y reutilizable).

| Script | Equivale a |
|---|---|
| `01_extractor.py` | `python -m prospector mine` |
| `02_auditor.py` | `python -m prospector audit` |
| `03_composer.py` | `python -m prospector compose` |
| `04_mailer.py` | `python -m prospector send` |

Los argumentos se pasan igual: `python scripts/01_extractor.py "bares malasaña"`.

`requirements.txt` instala el minador sigiloso (Scrapling), el navegador de
auditoría (Playwright), Pillow para las capturas anotadas y, opcionalmente,
`google-genai` para el jurado visual y la redacción con IA.
