# ⚙️ Plan de Automatización de Prospectos

Este documento define el flujo de trabajo asíncrono para captar clientes sin usar SaaS de pago mensual. Todo corre de manera programática usando Python, Playwright/Scrapling y Gemini 3.1 Pro (Multimodal).

## 1. Arquitectura del Flujo de Automatización

La automatización consta de 4 etapas principales ejecutadas secuencialmente por un **Script Orquestador en Python**:

### Etapa 1: Extracción de Leads (Minería)
- **Tecnología:** `scrapling-official` o scripts en `playwright` invocados desde Python.
- **Acción:** Buscar en bases de datos públicas, Google Maps o directorios por nichos (ej. "clínicas de fisioterapia en Madrid").
- **Output:** Un archivo de datos (`leads_crudos.csv` o SQLite) con Nombre del negocio, URL del sitio web, Email (raspeado de la web) y Teléfono.

### Etapa 2: Auditoría Visual y Calificación
- **Tecnología:** `playwright` (para tomar capturas) + Gemini 3.1 Pro (Vision/Multimodal).
- **Acción:**
  1. El script visita la URL del lead en background.
  2. Toma una captura de pantalla completa de la página de inicio (desktop y mobile).
  3. Envía la captura a la API de Gemini con un prompt estricto: *"Analiza este sitio web como experto en CRO. Identifica 1 problema crítico de UX, diseño o performance visual. Responde en JSON con el problema exacto y una puntuación de urgencia (1 a 10)."*
- **Filtro:** Si el sitio ya es excelente (urgencia baja), se descarta para ahorrar recursos. Si es pobre (urgencia alta), avanza.

### Etapa 3: Generación del Primer Mensaje ("Anti-Slop")
- **Tecnología:** API de Gemini + Directrices de la skill `humanizer`.
- **Acción:** El script toma el problema identificado y redacta un correo altamente personalizado usando las plantillas de `templates/primer_mensaje.md`.
- **Diferenciador (Prueba Visual):** El script en Python puede marcar la captura de pantalla obtenida en la Etapa 2 (ej. dibujando un recuadro rojo alrededor del menú roto con la librería `Pillow`) y adjuntarla o linkearla en el correo para probar que el análisis fue manual y real.

### Etapa 4: Envío Asíncrono
- **Tecnología:** Librería nativa de Python (`smtplib` y `email.mime`) conectada vía contraseñas de aplicación (Gmail/Outlook).
- **Acción:** Enviar los correos de manera programada a lo largo del día.
- **Seguridad:** Implementar retrasos aleatorios (jitter) entre envíos (ej. de 7 a 20 minutos) y limitar el volumen (max 30-50 correos/día por cuenta) para asegurar un 99% de deliverability y evitar caer en Spam.

## 2. El Disparador Asimétrico (La Respuesta del Cliente)

El trabajo pesado de desarrollo web y creación de mockups avanzados **NUNCA** se ejecuta por adelantado.

- **Trigger:** El prospecto lee el correo, ve la prueba visual y responde: *"Me interesa, quiero ver cómo lo mejorarían".*
- **Acción del Agente:** El Orquestador Antigravity instancia un subagente utilizando las skills de la carpeta `Landing`. Este agente tomará el mockup pre-diseñado para el nicho (en `Landing/nichos/*nichos/mockup`), lo adaptará con los datos del prospecto y generará un enlace (MVP desplegado en Vercel) en minutos.
- **Cierre:** Se envía el link del MVP para deslumbrar al cliente y llevarlo a una llamada de cierre para el Setup Fee y el MRR.

## 3. Hoja de Ruta de Desarrollo (Scripts a Crear)
1. `01_extractor.py`: Modulo de minería con Scrapling.
2. `02_auditor.py`: Módulo de captura de pantalla (Playwright) y consulta Multimodal a Gemini.
3. `03_composer.py`: Ensamblaje del correo "Anti-Slop" y manipulación de imagen.
4. `04_mailer.py`: Gestor de cola de correos y envío SMTP seguro.
