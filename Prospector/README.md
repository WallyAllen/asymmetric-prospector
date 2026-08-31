# 🎯 Prospector - Sistema de Captación Automatizada

El objetivo de este proyecto es escalar la adquisición de clientes de 0 a un flujo predecible, operando asincrónicamente y sin gastos fijos en plataformas SaaS de automatización de terceros.

## 📂 Estructura de Directorios

- `agent_skills/`: Skills de Antigravity dedicadas a la investigación, scraping y redacción de correos en frío (aquí se utilizarán intensamente `scrapling-official` y `playwright-cli`).
- `scripts/`: Código fuente en Python para orquestar la automatización (scraping -> análisis -> generación de copy -> envío SMTP).
- `templates/`: Plantillas maestras de copys, enfoques "Anti-Slop" y flujos conversacionales iniciales.
- `AUTOMATION_PLAN.md`: El documento arquitectónico maestro que detalla CÓMO se orquesta la prospección técnica y lógicamente.
