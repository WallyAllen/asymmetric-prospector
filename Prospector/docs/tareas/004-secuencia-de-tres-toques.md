# 004 · Secuencia de tres toques

> Estado: pendiente · Rama: `004-secuencia` · Fase 2 · **depende de 003**
> El cambio de mayor retorno del plan.

Hoy `Lead.estado` va `crudo → auditado → listo → enviado` y ahí muere:
`mailer.enviar()` manda una vez y el lead sale de la cola para siempre. El
primer correo captura ~58 % de las respuestas; el resto viene de los toques 2 y
3. Es casi la mitad del retorno de un trabajo ya hecho y ya pagado.

Criterio completo en el vault: `Tres toques, no siete`.

## Qué tiene que pasar

```
Toque 1 · día 0           · el hallazgo
Toque 2 · +3 días hábiles · la captura (si el 1 fue sin) o audit.argumentables[1]
Toque 3 · +7 días hábiles · cierre por permiso, una línea, sin adjunto
```

**Si el toque 2 no aporta información nueva, no se manda:** el lead salta al 3.

### Modelo

```python
@dataclass
class Touch(_Serializable):
    n: int
    asunto: str
    cuerpo: str
    adjunto: str | None = None
    generado_por: str = "plantilla"
    programado_para: str | None = None
    enviado_el: str | None = None
    message_id: str | None = None
```

`Lead.secuencia: list[Touch]`. `email_draft` queda como propiedad de
compatibilidad que devuelve `secuencia[0]`, y `migrate.py` convierte lo
existente — el repo ya tiene ese precedente y ya salvó datos una vez.

### Enhebrado y cola

Toques 2 y 3 en el mismo hilo: `In-Reply-To` y `References` al `message_id`
anterior, asunto intacto. **Nunca un `Re:` falso.**

`cola_pendiente()` pasa a devolver `(lead, toque)` y aplica, en orden:
excluir `respondido`/`baja`/`rebotado`/suprimidos → **seguimientos vencidos
primero** → cuota diaria global (30, con `MAIL_FOLLOWUP_MAX` configurable) →
días hábiles reales, reusando `quota.en_ventana()`.

### WhatsApp

Un solo seguimiento, no dos: en un chat con un desconocido el tercer mensaje ya
es insistencia. Va a los **3 días hábiles** del toque 1, solo si no contestó, y
es el cierre por permiso: no repite el hallazgo ni trae uno nuevo.

```python
TOQUE2_WHATSAPP = (
    "Hola, te vuelvo a escribir por lo de la web de {d}. Si no es momento, decime y no te escribo más. Si te sirve, te mando el boceto y lo ves cuando puedas.",
    "Hola de nuevo. Te había escrito por {d}: si no te interesa, decime y no te molesto más. Si sí, te paso el boceto y lo mirás con calma.",
    "Retomo lo de {d} por si se te pasó. Si no es para vos ahora, avisame y no insisto. Si querés, te mando el boceto igual.",
)
```

Elegido con `elegir(TOQUE2_WHATSAPP, lead.id, "toque2_wa")`, pasado por
`estilo_felipe` (spec 009) y `generado_por = "plantilla-whatsapp-toque2"`. Tres
variantes y no una: el mismo texto a cientos de números es lo que detecta el
filtro de spam. "Decime y no te escribo más" se cumple: si contesta que no, va a
`py -m prospector respondio <clave> --baja`.

## Criterio de aceptación

```
tests/test_secuencia.py::test_lead_respondido_nunca_entra_en_la_cola
tests/test_secuencia.py::test_toque_2_enhebra_con_message_id_del_1
tests/test_secuencia.py::test_sin_segundo_argumento_no_repite_el_toque_1
tests/test_secuencia.py::test_whatsapp_un_solo_seguimiento_a_los_3_dias_habiles
```

**El primero es el que no puede fallar nunca.** Un lead que respondió y recibe
el toque 2 es un bug de severidad máxima.

```bash
pytest tests/ -x -q
py -m prospector send        # simulación: muestra los tres toques de un lead
```

## Alcance

**Tocar:** `models.py`, `storage.py`, `pipeline.py`, `deliver/mailer.py`,
`migrate.py`, `cli.py`, `tests/test_secuencia.py`

**No tocar:** `audit/`, el score, el default de `send` (simula).

**Tamaño:** el mínimo que haga pasar los tests.
