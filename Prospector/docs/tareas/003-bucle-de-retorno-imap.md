# 003 · Bucle de retorno: leer la bandeja

> Estado: pendiente · Rama: `003-inbox` · Fase 1 · **bloquea la 004**

Hoy nadie lee la bandeja. No se sabe quién respondió, quién rebotó de verdad
—más allá del rechazo SMTP sincrónico, que es una fracción— ni quién pidió la
baja. Sin esto no se puede medir nada y no se puede hacer seguimiento sin
arriesgarse a escribirle "por si no lo viste" a alguien que ya contestó.

Ver `El seguimiento se detiene con lo que dice la bandeja` en el vault.

## Prerrequisito

`mailer.py:70` genera el `Message-ID` y lo tira. Sin guardarlo no se pueden
enhebrar los seguimientos. Va al registro y al `Lead`:

```python
"message_id": mensaje["Message-ID"],
"toque": 1,
```

## Qué tiene que pasar

Nuevo `prospector/deliver/inbox.py` + comando `py -m prospector inbox`:

1. Conecta por IMAP a la misma cuenta, recorre lo no visto desde la última
   corrida (marca de agua en `data/04_sent/ultimo_barrido.json`).
2. Cruza por `In-Reply-To` / `References` → `message_id`, con respaldo por
   dirección del remitente.
3. **Clasifica con reglas, no con IA.** Determinista, gratis, auditable:
   - rebote: `Content-Type: message/delivery-status`, remitente
     `mailer-daemon`/`postmaster`. **Permanente (5.x.x) va a supresión;
     temporal (4.x.x) no.**
   - baja: "no me interesa", "no escriban", "baja", "eliminar", "unsubscribe"
   - ausencia: "fuera de la oficina", "vacaciones", `Auto-Submitted: auto-replied`
   - respuesta humana: todo lo demás
4. Actualiza `Lead.estado`: `respondido` · `baja` · `rebotado` · `ausente_hasta`.
5. `baja` y rebote permanente → `add_to_suppression()` automático.

`storage._PROGRESO` ya tiene `respondido` y `baja` en 9 (terminales). Sumar los
que falten con el mismo criterio.

## Criterio de aceptación

Test **sin red**, con mensajes MIME de fixture:

```
tests/test_inbox.py::test_dsn_permanente_va_a_supresion
tests/test_inbox.py::test_dsn_temporal_no_suprime
tests/test_inbox.py::test_respuesta_humana_marca_respondido
tests/test_inbox.py::test_autorespuesta_no_marca_respondido
```

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `prospector/deliver/inbox.py` (nuevo), `mailer.py` (guardar
`message_id`), `models.py`, `storage.py`, `cli.py`, `tests/test_inbox.py`

**No tocar:** el redactor, el score, el default de `send`.

## Cuidados

Las credenciales IMAP salen de `.env`, nunca del código. Y el barrido tiene que
ser idempotente: correrlo dos veces no puede marcar dos veces ni perder
mensajes.
