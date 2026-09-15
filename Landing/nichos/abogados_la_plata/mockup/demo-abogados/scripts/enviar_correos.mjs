import nodemailer from 'nodemailer';
import dotenv from 'dotenv';

// Cargar variables de entorno desde el archivo .env
dotenv.config();

// Configuración del transporter de Nodemailer usando Gmail
const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.EMAIL_USUARIO,     // Tu correo de Gmail
    pass: process.env.EMAIL_PASSWORD     // La contraseña de aplicación de 16 caracteres
  }
});

// Lista de prospectos que SÍ tienen correo electrónico detectado
const prospectos = [
  {
    nombre: "Estudio Lombardo",
    email: "Guillermotlombardo@gmail.com",
    asunto: "Auditoría técnica: Desgaste de marca e imagen digital - Estudio Lombardo",
    cuerpo: `Equipo del Estudio Lombardo, buenas tardes. Somos un equipo técnico local.

Auditando la infraestructura digital de las firmas con mayor trayectoria en La Plata, detectamos un fallo grave de posicionamiento en su canal de captación.

Su estudio cuenta con más de 25 años de experiencia, lo cual es un activo invaluable. Sin embargo, su infraestructura actual opera sobre un formato de blog gratuito (.wordpress.com). Cuando un prospecto busca un estudio consolidado y aterriza en una plantilla básica, la percepción de esos 25 años de prestigio se licúa en segundos, forzando a prospectos calificados a dudar de su vigencia en el mercado.

Desarrollamos una nueva arquitectura de captación exclusiva para firmas legales. Podemos reemplazar su sistema actual por una infraestructura premium con dominio propio (.com.ar), diseñada para proyectar verdaderamente sus 25 años de autoridad y derivar las consultas sin fricción hacia su WhatsApp.

Indíquenme a qué hora tienen 5 minutos mañana para mostrarles la arquitectura exacta que le devuelve el peso institucional a su presencia online.`
  }
];

async function enviarCorreos() {
  console.log("Iniciando envío de correos automatizado...");

  if (!process.env.EMAIL_USUARIO || !process.env.EMAIL_PASSWORD) {
    console.error("❌ ERROR: Faltan las credenciales en el archivo .env");
    console.log("Asegúrate de haber creado el archivo .env con EMAIL_USUARIO y EMAIL_PASSWORD");
    return;
  }

  let enviados = 0;
  let errores = 0;

  for (const prospecto of prospectos) {
    console.log(`⏳ Enviando correo a: ${prospecto.nombre} (${prospecto.email})...`);
    
    try {
      const info = await transporter.sendMail({
        from: `"Equipo Técnico" <${process.env.EMAIL_USUARIO}>`,
        to: prospecto.email,
        subject: prospecto.asunto,
        text: prospecto.cuerpo
      });
      console.log(`✅ Correo enviado con éxito a ${prospecto.nombre} - Message ID: ${info.messageId}`);
      enviados++;
      
      // Pausa de 3 segundos
      await new Promise(resolve => setTimeout(resolve, 3000));
      
    } catch (error) {
      console.error(`❌ Error enviando a ${prospecto.nombre}:`, error.message);
      errores++;
    }
  }

  console.log("\n--- RESUMEN ---");
  console.log(`Total enviados: ${enviados}`);
  console.log(`Total errores: ${errores}`);
}

enviarCorreos();
