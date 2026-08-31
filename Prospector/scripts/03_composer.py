import os
import json
import asyncio
from google import genai
from google.genai import types

# Configuración de carpetas
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
AUDITED_FILE = os.path.join(BASE_DIR, 'data', '02_audited', 'leads_auditados.json')
COMPOSED_DIR = os.path.join(BASE_DIR, 'data', '03_composed')
COMPOSED_FILE = os.path.join(COMPOSED_DIR, 'leads_listos.json')
TEMPLATE_FILE = os.path.join(BASE_DIR, 'templates', 'primer_mensaje.md')

async def main():
    print("[*] Iniciando El Redactor Anti-Slop (Composer)...")
    
    os.makedirs(COMPOSED_DIR, exist_ok=True)
    
    # Validar archivos y claves
    if not os.path.exists(AUDITED_FILE):
        print(f"[!] No se encontró el archivo: {AUDITED_FILE}")
        print("    Debes ejecutar 02_auditor.py primero.")
        return
        
    if not os.path.exists(TEMPLATE_FILE):
        print(f"[!] No se encontró la plantilla de correo en {TEMPLATE_FILE}")
        return
        
    if "GEMINI_API_KEY" not in os.environ:
        print("\n[!] ADVERTENCIA: La variable de entorno GEMINI_API_KEY no está configurada.")
        print("    En Windows (Powershell): $env:GEMINI_API_KEY=\"tu_api_key\"")
        return

    # Cargar datos
    with open(AUDITED_FILE, 'r', encoding='utf-8') as f:
        leads = json.load(f)
        
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    client = genai.Client()
    leads_listos = []
    
    for lead in leads:
        # Solo redactar si el lead pasó por la auditoría y tiene un problema detectado
        if 'cro_audit' not in lead:
            continue
            
        url = lead.get('url')
        email = lead.get('email')
        problema = lead['cro_audit'].get('problema_cro', 'Problema visual no especificado')
        
        print(f"\n[*] Redactando correo hiper-personalizado para: {url} ({email})")
        
        # Inyectar el contexto en el prompt
        prompt = f"""
        Eres un experto en ventas B2B y redacción persuasiva (cold emailing) de alto nivel.
        Tu objetivo es escribir un correo directo, corto y asertivo ("Anti-Slop") a un prospecto.
        
        Aquí tienes las directrices de la agencia y ejemplos de cómo debes sonar:
        <plantilla_referencia>
        {template}
        </plantilla_referencia>
        
        Datos del prospecto actual:
        - URL: {url}
        - Problema detectado por nuestra auditoría IA: "{problema}"
        
        Instrucciones estrictas:
        1. No uses saludos largos ni formales (nada de "Espero que este correo te encuentre bien").
        2. Ve directo al grano en la primera línea.
        3. El ángulo principal de venta es: "Actualmente tienes una web corporativa genérica/folleto, no una Landing Page optimizada para vender". Usa el problema detectado para justificar esto.
        4. Menciona que adjuntas una captura de pantalla de lo primero que ven sus clientes marcando el error.
        5. Ofrece armar un prototipo/mockup de una Landing Page real, de alto impacto visual, sin compromiso.
        
        Devuelve ÚNICAMENTE un JSON válido con:
        {{
            "asunto": "un asunto persuasivo y asimétrico",
            "cuerpo": "el cuerpo del correo en texto plano, listo para enviarse"
        }}
        """
        
        try:
            # Usamos gemini-3.6-flash
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7 # Un poco de creatividad para el asunto y el copy
                )
            )
            
            correo = json.loads(response.text)
            
            print(f"    [+] Asunto generado: {correo.get('asunto')}")
            print(f"    [+] Cuerpo listo ({len(correo.get('cuerpo', ''))} caracteres).")
            
            # Agregamos la información del correo al prospecto
            lead['email_content'] = correo
            leads_listos.append(lead)
            
            import time
            time.sleep(2)
            
        except Exception as e:
            print(f"    [!] Error al redactar para {url}: {e}")
            
    # Guardar la cola de correos listos para el último script (el enviador)
    with open(COMPOSED_FILE, 'w', encoding='utf-8') as f:
        json.dump(leads_listos, f, indent=4)
        
    print(f"\n[*] Proceso finalizado. Se redactaron con éxito {len(leads_listos)} correos.")
    print(f"[*] Los correos están listos para ser enviados en: {COMPOSED_FILE}")

if __name__ == '__main__':
    asyncio.run(main())
