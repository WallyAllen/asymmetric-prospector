# 🐍 Scripts de Prospección: Arquitectura y Objetivos

Este directorio contiene los scripts de automatización. El objetivo principal de estos scripts no es enviar spam masivo, sino ejecutar **Prospección Asimétrica**: simular el trabajo de un investigador humano que analiza a fondo una empresa antes de contactarla, pero haciéndolo a escala y de forma automatizada.

Buscamos máxima personalización, correos que rompan el filtro de "ceguera publicitaria" del cliente y un costo operativo de $0 usando infraestructura local.

## 1. `01_extractor.py` (El Minero)
**Objetivo:** Obtener una lista cruda de prospectos dentro de un nicho específico, evadiendo bloqueos antibot.
- **Cómo funciona:** Recibe un input (ej. "Clínicas estéticas en Miami"). Usa `scrapling-official` para navegar por Google Maps o directorios. Extrae el Nombre del negocio, la URL de su web, y busca correos electrónicos públicos en su página de contacto.
- **Output:** `leads_crudos.json` o `.csv`.

## 2. `02_auditor.py` (El Ojo Crítico)
**Objetivo:** Cualificar al lead y generar la "Prueba de Trabajo" que demuestra que no somos un bot enviando correos masivos.
- **Cómo funciona:**
  1. Lee el archivo de leads.
  2. Usa `playwright` (headless) para visitar cada URL y tomar una captura de pantalla completa (Full-page screenshot).
  3. Envía la captura a la API de **Gemini 3.1 Pro (Multimodal)** con un prompt estricto de CRO (Conversion Rate Optimization).
  4. Gemini responde con el problema visual/estructural más grave que encontró (ej. "El botón de contacto no contrasta", "Diseño no responsive", "Carga excesiva de texto").
- **Output:** Actualiza el archivo de leads añadiendo el `problema_cro` y la ruta local de la `captura.png`.

## 3. `03_composer.py` (El Redactor Anti-Slop)
**Objetivo:** Redactar un gancho irresistible e hiper-personalizado para cada lead calificado.
- **Cómo funciona:**
  1. Toma el `problema_cro` identificado por el auditor.
  2. Usa las plantillas de `templates/primer_mensaje.md` y la API de Gemini para redactar un correo asertivo y natural (Anti-Slop).
  3. **(Opcional pero letal):** Usa la librería `Pillow` de Python para abrir la `captura.png` y dibujar automáticamente un círculo rojo o un recuadro alrededor de la zona del problema identificado por la IA.
- **Output:** Genera el asunto, el cuerpo del correo y asocia la imagen editada listos para enviar. Guárdalos en una cola `cola_de_envio.json`.

## 4. `04_mailer.py` (El Cartero Sigiloso)
**Objetivo:** Garantizar un 99% de tasa de entrega (Deliverability) en la bandeja principal, evitando la carpeta de Spam.
- **Cómo funciona:** No usa plataformas masivas de email. Usa la librería nativa `smtplib` de Python para conectarse a una cuenta de Gmail/Outlook real (vía App Passwords). 
- **La magia:** Implementa *Jitter* (retrasos aleatorios). Envía un correo, duerme entre 6 y 14 minutos, envía el siguiente. Simula perfectamente a un humano trabajando. Se limita a un máximo de 30-40 correos por día por cuenta.
