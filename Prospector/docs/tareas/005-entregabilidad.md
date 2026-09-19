# 005 · List-Unsubscribe e higiene de entrega

> Estado: pendiente · Rama: `005-entregabilidad` · Fase 4

## a · `List-Unsubscribe` (lo más importante)

Requisito de Google y Yahoo desde febrero de 2024 para quien les escribe.
`construir_mensaje()` no lo pone. Aplica a 30 envíos diarios igual que a 3.000.

```python
mensaje["List-Unsubscribe"] = f"<mailto:{cfg.user}?subject=baja>"
mensaje["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
```

Con `003` leyendo esa casilla, las bajas se procesan solas: el requisito deja de
ser un trámite y pasa a ser la lista de supresión.

## b · Validación previa, local y gratis

Sintaxis RFC básica, dominio con registro MX, lista de descartables, y descarte
de `noreply@` / `no-reply@`.

**`info@`, `contacto@` y `hola@` se quedan.** La advertencia de las skills
contra las role addresses es para B2B corporativo; en un negocio local esa suele
ser la única dirección que existe. Acá la regla está invertida.

## c · Freno automático por rebotes

Si la tasa de rebote de los últimos 100 envíos supera el **2 %**, `send` se
niega a salir. Un dominio quemado no se recupera: esto convierte esa advertencia
del README en código.

## Criterio de aceptación

```
tests/test_salida.py::test_mensaje_lleva_list_unsubscribe
tests/test_salida.py::test_rol_addresses_no_se_descartan
tests/test_salida.py::test_send_frena_con_rebotes_altos
```

```bash
pytest tests/ -x -q
```

## Alcance

**Tocar:** `deliver/mailer.py`, `deliver/validar.py` (nuevo o dentro de
`sources/contacts.py`), `tests/test_salida.py`

## Fuera del código, una vez

Verificar SPF, DKIM y DMARC del dominio remitente. Si salís por Google
Workspace, SPF y DKIM ya están; **DMARC en `p=none` con `rua` casi seguro que
falta** y son cinco minutos de DNS. No hace falta llegar a `p=reject`.
