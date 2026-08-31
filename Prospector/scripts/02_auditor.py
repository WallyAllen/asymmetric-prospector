import os
import json
import asyncio
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

# Configuración de carpetas
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_FILE = os.path.join(BASE_DIR, 'data', '01_raw', 'leads_crudos.json')
AUDITED_FILE = os.path.join(BASE_DIR, 'data', '02_audited', 'leads_auditados.json')
SCREENSHOTS_DIR = os.path.join(BASE_DIR, 'data', 'screenshots')

async def main():
    print("[*] Iniciando El Ojo Crítico (Auditor IA Multimodal)...")
    
    if not os.path.exists(RAW_FILE):
        print(f"[!] No se encontró el archivo: {RAW_FILE}")
        print("    Ejecuta primero 01_extractor.py")
        return
        
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        leads = json.load(f)
        
    # Validar que exista la API Key
    if "GEMINI_API_KEY" not in os.environ:
        print("\n[!] ADVERTENCIA: La variable de entorno GEMINI_API_KEY no está configurada.")
        print("    Debes configurarla antes de ejecutar este script para que la IA visual funcione.")
        print("    En Windows (Powershell): $env:GEMINI_API_KEY=\"tu_api_key\"")
        print("    O añade un archivo .env si usas python-dotenv.")
        return

    client = genai.Client()
    leads_auditados = []
    
    async with async_playwright() as p:
        # Iniciamos el navegador (Playwright puro para control total de capturas)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        
        for lead in leads:
            url = lead.get('url')
            email = lead.get('email')
            
            # Estrategia de optimización: Solo gastamos tokens y cómputo en leads que tienen correo.
            # No tiene sentido auditar a alguien a quien no podemos contactar.
            if not email:
                continue
                
            print(f"\n[*] Auditando: {url}")
            domain = urlparse(url).netloc.replace('www.', '')
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{domain}.png")
            
            try:
                # 1. Tomar Captura de Pantalla (Solo Viewport / Above the Fold)
                print("    -> Navegando y tomando captura de pantalla (Viewport)...")
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=20000)
                # Quitamos full_page=True para sacar solo la zona de mayor impacto (lo primero que ve el usuario)
                await page.screenshot(path=screenshot_path)
                await page.close()
                
                # 2. Análisis Multimodal con Gemini
                print("    -> Analizando UI/UX con Gemini...")
                
                prompt = """
                Actúa como un experto mundial en CRO y embudos de venta.
                Analiza esta captura de pantalla que muestra EXCLUSIVAMENTE lo primero que ve un usuario al entrar a la web (Above the Fold).
                
                Tu objetivo es determinar si esto es una "Landing Page" optimizada para conversiones, o si es un sitio web corporativo genérico (brochure) que hace perder clientes.
                
                Identifica el error MÁS CRÍTICO en esta zona inicial. 
                Ejemplos de errores letales: "Es una web genérica sin un único llamado a la acción (CTA)", "El banner principal no explica qué venden", "Exceso de opciones en el menú que distraen de la venta".
                
                Responde ÚNICAMENTE con un JSON válido usando esta estructura exacta:
                {
                    "problema_cro": "descripción asertiva y directa del problema en esta zona",
                    "urgencia": 8
                }
                """
                
                # Subimos la captura directamente usando la File API o Inline (Inline es mejor para scripts rápidos)
                from PIL import Image
                img = Image.open(screenshot_path)
                
                # Usamos gemini-3.6-flash (el modelo actual permitido para nuevos usuarios)
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4
                    )
                )
                
                resultado = json.loads(response.text)
                urgencia = resultado.get('urgencia', 0)
                problema = resultado.get('problema_cro', 'Desconocido')
                
                print(f"    [+] Problema detectado (Urgencia {urgencia}/10): {problema}")
                
                lead['screenshot_path'] = screenshot_path
                lead['cro_audit'] = resultado
                leads_auditados.append(lead)
                
                # Pausa para evitar rate-limits de la capa gratuita (15 RPM)
                import time
                time.sleep(4)
                
            except Exception as e:
                print(f"    [!] Error al auditar {url}: {e}")
                
        await browser.close()
                
    # Guardar archivo con los prospectos listos para el redactor
    with open(AUDITED_FILE, 'w', encoding='utf-8') as f:
        json.dump(leads_auditados, f, indent=4)
        
    print(f"\n[*] Proceso finalizado. Se auditaron con éxito {len(leads_auditados)} prospectos.")
    print(f"[*] Resultados guardados en: {AUDITED_FILE}")

if __name__ == '__main__':
    asyncio.run(main())
