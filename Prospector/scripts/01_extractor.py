import sys
import os
import json
import asyncio
import re
from urllib.parse import urljoin
from scrapling.fetchers import AsyncStealthySession, Fetcher

async def main(query):
    print(f"[*] Iniciando El Minero...")
    print(f"[*] Buscando prospectos para la consulta: '{query}'")
    
    # Expresión regular básica para emails
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    
    leads = []
    
    # 1. Búsqueda Inicial (DuckDuckGo Lite) usando Fetcher regular (es súper rápido)
    print(f"[*] Consultando buscador: DuckDuckGo Lite")
    search_page = Fetcher.post('https://lite.duckduckgo.com/lite/', data={'q': query})
    
    # Extraer todos los enlaces de la página de resultados
    links = search_page.css('a::attr(href)').getall()
    business_urls = set()
    
    for link in links:
        if link.startswith('http') and not any(x in link for x in ['duckduckgo.com', 'youtube.com', 'facebook.com', 'instagram.com']):
            # Limpiar parámetros de seguimiento para obtener la URL limpia
            clean_url = link.split('?')[0]
            business_urls.add(clean_url)
            
    # Limitamos a 5-10 para pruebas rápidas
    business_urls = list(business_urls)[:7]
    print(f"[*] Encontradas {len(business_urls)} webs de negocios potenciales.")
    
    # Usamos AsyncStealthySession para abrir un navegador headless que esquiva protecciones antibot
    # Esto es crítico para visitar la web de los clientes sin ser bloqueados.
    async with AsyncStealthySession(headless=True) as session:
                
        # Limitamos a 5-10 para pruebas rápidas
        business_urls = list(business_urls)[:7]
        print(f"[*] Encontradas {len(business_urls)} webs de negocios potenciales.")
        
        # 2. Auditoría de cada web para extraer correo
        for url in business_urls:
            print(f"\n[*] Analizando {url}...")
            try:
                # Visitamos la web del negocio
                b_page = await session.fetch(url)
                
                # Extraemos todo el texto visible del body para buscar el correo
                body_text_blocks = b_page.css('body *::text').getall()
                body_text = " ".join(body_text_blocks)
                
                emails = set(email_pattern.findall(body_text))
                
                # Si no está en la página principal, buscamos un link hacia la página de "Contacto"
                if not emails:
                    contact_links = b_page.xpath('//a[contains(translate(text(), "CONTACTO", "contacto"), "contacto")]/@href').getall()
                    
                    if contact_links:
                        # Asegurarnos de que el link de contacto sea absoluto
                        contact_url = urljoin(url, contact_links[0])
                        print(f"    -> Buscando en página de contacto: {contact_url}")
                        c_page = await session.fetch(contact_url)
                        
                        c_text_blocks = c_page.css('body *::text').getall()
                        c_text = " ".join(c_text_blocks)
                        emails.update(email_pattern.findall(c_text))
                
                # Filtrar posibles falsos positivos que la regex atrapa por error (imágenes, etc.)
                valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))]
                
                if valid_emails:
                    email_encontrado = valid_emails[0].lower()
                    print(f"    [+] ¡Éxito! Email encontrado: {email_encontrado}")
                    leads.append({
                        "url": url,
                        "email": email_encontrado
                    })
                else:
                    print(f"    [-] No se encontró un correo público en la web.")
                    leads.append({
                        "url": url,
                        "email": None
                    })
                    
            except Exception as e:
                print(f"    [!] Error al acceder a {url} (puede tener protección severa): {e}")
                
    # Guardar resultados en la nueva carpeta de datos estructurada
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'data', '01_raw')
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'leads_crudos.json')
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(leads, f, indent=4)
        
    print(f"\n[*] Proceso finalizado. Se extrajeron {len(leads)} prospectos y se guardaron en 'data/01_raw/leads_crudos.json'.")

if __name__ == "__main__":
    # Permite pasar la búsqueda como argumento por consola o usa un valor por defecto.
    query_busqueda = "clinicas dentales madrid"
    if len(sys.argv) > 1:
        query_busqueda = " ".join(sys.argv[1:])
        
    asyncio.run(main(query_busqueda))
