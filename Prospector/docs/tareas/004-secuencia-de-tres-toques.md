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

## Criterio de aceptación

```
tests/test_secuencia.py::test_lead_respondido_nunca_entra_en_la_cola
tests/test_secuencia.py::test_toque_2_enhebra_con_message_id_del_1
tests/test_secuencia.py::test_sin_segundo_argumento_no_repite_el_toque_1
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
