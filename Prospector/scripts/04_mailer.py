import os
import json
import time
import random
import smtplib
from email.message import EmailMessage
import mimetypes

# Configuración de carpetas
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
COMPOSED_FILE = os.path.join(BASE_DIR, 'data', '03_composed', 'leads_listos.json')
SENT_DIR = os.path.join(BASE_DIR, 'data', '04_sent')
SENT_FILE = os.path.join(SENT_DIR, 'registro_envios.json')

def main():
    print("[*] Iniciando El Cartero Sigiloso (Mailer Async)...")
    
    os.makedirs(SENT_DIR, exist_ok=True)
    
    if not os.path.exists(COMPOSED_FILE):
        print(f"[!] No se encontró el archivo: {COMPOSED_FILE}")
        print("    Debes ejecutar 03_composer.py primero.")
        return
        
    # Validar credenciales
    # Se recomiendan Contraseñas de Aplicación (App Passwords) para Gmail/Outlook
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_pass:
        print("\n[!] ADVERTENCIA: Faltan credenciales SMTP.")
        print("    Configura las variables de entorno SMTP_USER y SMTP_PASSWORD.")
        print("    Ejemplo Powershell: $env:SMTP_USER=\"tu@gmail.com\"; $env:SMTP_PASSWORD=\"abcd efgh ijkl mnop\"")
        return

    # Cargar correos redactados
    with open(COMPOSED_FILE, 'r', encoding='utf-8') as f:
        leads = json.load(f)
        
    # Cargar registro histórico de envíos para evitar enviar duplicados (Idempotencia)
    sent_log = []
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, 'r', encoding='utf-8') as f:
            sent_log = json.load(f)
            
    # Crear un set con los emails ya contactados
    sent_emails = {log.get('email') for log in sent_log if log.get('email')}
    
    # Filtrar solo los leads que tienen contenido redactado y a los que NO se les ha enviado aún
    leads_a_enviar = [l for l in leads if 'email_content' in l and l.get('email') not in sent_emails]
    
    if not leads_a_enviar:
        print("[-] No hay correos nuevos pendientes de envío en la bandeja de salida.")
        return
        
    print(f"[*] Hay {len(leads_a_enviar)} correos en cola.")
    print(f"[*] Conectando al servidor SMTP ({smtp_server}:{smtp_port})...")
    
    try:
        # Iniciar la conexión TLS segura con el servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
    except Exception as e:
        print(f"[!] Error crítico al conectar con el servidor de correo: {e}")
        return

    for i, lead in enumerate(leads_a_enviar):
        destino = lead['email']
        contenido = lead['email_content']
        asunto = contenido.get('asunto', 'Una idea para tu negocio')
        cuerpo = contenido.get('cuerpo', '')
        captura_path = lead.get('screenshot_path') # Evidencia guardada en el paso 02
        
        print(f"\n[*] Preparando envío para: {destino}")
        
        # Construir el mensaje MIME
        msg = EmailMessage()
        msg['Subject'] = asunto
        msg['From'] = smtp_user
        msg['To'] = destino
        msg.set_content(cuerpo)
        
        # EL GANCHO ASIMÉTRICO: Adjuntar la captura de pantalla de su propia web
        if captura_path and os.path.exists(captura_path):
            print(f"    -> Adjuntando evidencia visual: {os.path.basename(captura_path)}")
            mime_type, _ = mimetypes.guess_type(captura_path)
            mime_type = mime_type or 'application/octet-stream'
            maintype, subtype = mime_type.split('/', 1)
            
            with open(captura_path, 'rb') as img_f:
                msg.add_attachment(
                    img_f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=f"analisis_visual_{os.path.basename(captura_path)}"
                )
        else:
            print("    [?] No se encontró captura de pantalla para adjuntar.")
        
        try:
            # Enviar mensaje
            server.send_message(msg)
            print(f"    [+] ¡Correo enviado con éxito a {destino}!")
            
            # Registrar envío permanentemente
            lead['enviado_el'] = time.strftime("%Y-%m-%d %H:%M:%S")
            sent_log.append(lead)
            with open(SENT_FILE, 'w', encoding='utf-8') as f:
                json.dump(sent_log, f, indent=4)
                
        except Exception as e:
            print(f"    [!] Fallo al enviar a {destino}: {e}")
            continue # Si un envío falla, intentamos con el siguiente
            
        # --- PREVENCIÓN ANTISPAM (JITTER) ---
        # Si no es el último correo de la lista, hacemos una pausa humana
        if i < len(leads_a_enviar) - 1:
            # Esperar un tiempo aleatorio entre 6 y 14 minutos (360 a 840 segundos)
            # NOTA: Para hacer pruebas rápidas en local, cambia estos valores a 10, 30.
            retraso = random.randint(360, 840)
            minutos = retraso // 60
            segundos = retraso % 60
            print(f"    [zZz] Durmiendo {minutos}m {segundos}s para simular comportamiento humano y evitar filtros Anti-Spam...")
            time.sleep(retraso)

    # Cerrar conexión de forma segura
    server.quit()
    print(f"\n[*] Bandeja de salida procesada por completo. ¡Sistema inactivo!")

if __name__ == '__main__':
    main()
