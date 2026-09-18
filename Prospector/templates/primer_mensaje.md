# Plantilla base: primer mensaje

Esta plantilla **no** la usa el motor determinista (que arma el texto desde los
fragmentos de `audit/rules.py` + `compose/lexicon.py`). Sirve solo como
referencia de estilo para el motor de IA, que se inyecta en el `PROMPT` de
`compose/writer.py`. Mantenerla alineada con lo que el script realmente
escribe: si describe otra cosa, empuja a la IA hacia un estilo que el resto del
sistema ya descartó.

## Directrices

1. **Segunda persona del singular, de punta a punta.** Voseo rioplatense. Nunca
   abrir en plural ("hola, equipo de X") y seguir en singular ("tu web", "te
   sirve"): mezclar las dos personas se lee como plantilla mal rellenada.
2. **La primera línea es el hallazgo medido**, concreto y verificable. Si la
   frase sirve igual para otro prospecto de la lista, es spam.
3. **La consecuencia se dice una sola vez.** No repetir la misma idea con otras
   palabras tres líneas más abajo.
4. **El puente hacia la oferta sale del hallazgo**, no de una frase fija. Si el
   problema era la velocidad de carga, no se cierra hablando del botón de
   contacto.
5. **Vocabulario del rubro**: "sacar un turno" para una veterinaria, "pedir un
   presupuesto" para un taller, "consultar por una propiedad" para una
   inmobiliaria. Nunca "reservar" genérico.
6. **Sin credenciales académicas.** La autoridad la da el hallazgo medido.
7. **Un solo pedido**, de bajo compromiso, con plazo concreto.

---

## Correo · web con hallazgos

> Los dos ejemplos de abajo son ficticios: el negocio, el dominio y los números
> están inventados. Sirven para mostrar el registro y la estructura, no para
> copiarlos tal cual — si la primera línea sirve igual para otro prospecto de la
> lista, es spam.

**Asunto:** el botón de contacto

**Cuerpo:**
Hola, Estudio Aguirre,

Llegué a estudioaguirre.example buscando estudios jurídicos en Buenos Aires. En Maps
tienen 4,8 con 154 reseñas: la demanda claramente está. Lo primero que vi fue
esto: al entrar no hay ningún botón que diga qué hacer, ni turno, ni llamar, ni
escribir.

Te adjunto la captura con la zona marcada.

El que entra tiene que ponerse a buscar cómo contactarte, y casi nadie busca.
Poner un botón visible arriba de todo es lo primero que suelo mover, y se nota
enseguida. Me toma un par de horas armar un boceto de cómo quedaría esa portada.

¿Te sirve si te lo paso para que lo veas? Sin compromiso.

Felipe
Diseño y CRO de landing pages

---

## WhatsApp · negocio sin web

Sin asunto, sin firma y sin ningún enlace: el nombre y el número ya están en el
encabezado del chat, y un link en el primer mensaje de un número no agendado es
la señal de spam más cara del canal. Menos de 95 palabras.

> Hola, ¿qué tal? Soy Felipe, armo páginas web.
>
> Te encontré en Maps buscando centros de fisioterapia en Mendoza: 3,0 con 219
> reseñas y sin web enlazada. El que sale del traumatólogo con una orden ve la
> ficha, no encuentra cómo pedir un turno y termina en la del de al lado.
>
> Te armo un boceto de una página de una sola pantalla para que lo veas. ¿Te lo
> paso?
