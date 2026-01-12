# Investigación Profunda - Error SIS0042 con Importe 0,00 EUR

## PROBLEMAS IDENTIFICADOS

### 1. PROBLEMA CRÍTICO: Importe Se Envía Como 0,00 EUR

**Síntoma en Redsys:**
```
Importe: 0,00 Euros
Número pedido: (vacío)
Código Comercio: (SPAIN)
Terminal: 369056973-1
Error: SIS0042 - Error en datos enviados
```

**Causa Raíz:**

El flujo de pago tiene dos problemas separados que se combinan:

#### PROBLEMA 1.1: Campo `selected_price` NO se rellena correctamente

**Archivo:** `/opt/saas/clientes/sunsetrentpinveco/addons-extra/vehicle_rental/controllers/web_contract_booking_fixed.py`

**Línea 1281:** El formulario HTML define:
```html
<input type="hidden" name="selected_price" id="selected_price" value=""/>
```

El campo comienza **VACÍO** (`value=""`)

**Líneas 1496 y 1556:** El JavaScript SOLO rellena este campo cuando:
- El usuario selecciona una tarifa fija (línea 1496)
- El usuario selecciona una tarifa dinámica (línea 1556)

**FLUJO ACTUAL DEL CLIENTE:**
1. Usuario entra a `/web/booking-enquiry`
2. Selecciona duración, fechas, KM
3. **DEBERÍA seleccionar una tarifa** → rellenaría `selected_price`
4. Envía formulario POST a `/rental/payment`

**FLUJO PROBLEMÁTICO:**
1. Usuario entra a `/web/booking-enquiry`
2. Selecciona duración, fechas, KM
3. **NO selecciona tarifa** (UI incompleta o confusa)
4. Envía formulario POST con `selected_price=""` (VACÍO)
5. Endpoint recibe `selected_price=""`, lo convierte a 0
6. **Fallback de línea 2816:** `if selected_price <= 0: selected_price = 135.00`
7. ... PERO ESPERA ...

#### PROBLEMA 1.2: El Fallback (135.00) No Se Usa Para Redsys

**Archivo:** `web_contract_booking_fixed.py`

**Línea 2812-2825 en `/rental/payment`:**
```python
selected_price_str = kw.get('selected_price', '').strip()
selected_price = float(selected_price_str) if selected_price_str else 0

# Recalcular a 135 EUR si está vacío
if selected_price <= 0:
    selected_price = 135.00
```

Aquí establece `selected_price = 135.00` ✓

**Línea 2880 (creación de payment.transaction):**
```python
tx = request.env['payment.transaction'].sudo().create({
    'provider_id': provider_id,
    'amount': selected_price,  # Aquí DEBERÍA ser 135.00
    ...
})
```

**PERO LUEGO** en el código que obtuve mi investigación:

**Línea ~2894:**
```python
'amount': selected_price,  # selected_price = 135.00
```

**Línea ~2907:**
```python
amount_cents = int(selected_price * 100)  # 135.00 * 100 = 13500
```

El código parece correcto aquí. PERO...

### 2. PROBLEMA CRÍTICO: Duplicación de Rutas HTTP

**Hay TRES archivos que definen `/rental/payment`:**

1. **payment_controller.py (línea 12)**
   - `@http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)`
   - Define `PaymentGatewayController.rental_payment()`
   - Crea `payment.transaction` con provider_id de Redsys

2. **payment_gateway.py (línea 9)**
   - `@http.route('/web/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)`
   - Define `RentalPaymentGateway.rental_payment_gateway()`
   - **NOTA: Ruta diferente `/web/rental/payment` NO `/rental/payment`**

3. **web_contract_booking_fixed.py (línea 2795)**
   - `@http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)`
   - Define `WebsiteContractBookingFixed.rental_payment()`
   - Este es el que genera el formulario Redsys

**CONFLICTO:**
- Ambos `payment_controller.py` y `web_contract_booking_fixed.py` definen la **MISMA RUTA**
- En Python, cuando hay conflicto de rutas, **la última cargada gana** (o causa override)
- El `__init__.py` carga en este orden:
  ```python
  from . import payment_controller      # Línea 11
  from . import payment_gateway         # Línea 12 - DESPUÉS
  ```
  Espera, reviso el `__init__.py` nuevamente...

**CORRECCIÓN:** El orden en `__init__.py` es:
```python
from . import payment_controller     # PRIMERO
from . import payment_gateway        # SEGUNDO
from . import web_contract_booking_fixed  # TERCERO - GANA
```

Por lo que **web_contract_booking_fixed.py GANA** y es el que se ejecuta cuando llama a `/rental/payment`.

### 3. PROBLEMA: El Error JavaScript `Cannot read properties of null (reading 'body')`

**Error reportado:**
```
TypeError: Cannot read properties of null (reading 'body')
    at WebsiteBuilderClientAction.onIframeLoad
```

**Causa probable:**
- El servidor `/rental/payment` está retornando HTML vacío o malformado
- El JavaScript intenta procesar el HTML pero no encuentra elementos esperados
- Específicamente, intenta acceder a `.body` de un elemento null

**Archivos involucrados:**
- `redsys_payment_handler.js` (JavaScript del lado cliente que maneja pagos Redsys)
- `redsys_payment_form.xml` (Template que muestra el formulario)
- El iframe que carga `/rental/payment` recibe una respuesta malformada

### 4. PROBLEMA: Logs Registran 0.00 EUR

**En Odoo logs debería verse algo como:**
```
[WARN] REDSYS_PARAMS: merchant_params={base64}...
[INFO] Signature generated (3DES-CBC): ...
[WARN] REDSYS_SIG: signature_b64=...
```

**Si ves 0.00 EUR en Redsys UI**, significa:
- El formulario Redsys recibió `Ds_Merchant_Amount=0` (en centavos)
- Esto ocurre cuando `amount_cents = int(selected_price * 100)` da 0
- `selected_price` debe ser 0 o muy pequeño cuando se calcula

### 5. PROBLEMA: Flujo de Pago Incompleto

El flujo actual es:

```
Usuario POST a /rental/payment
       ↓
   (2795) web_contract_booking_fixed.rental_payment()
       ↓
   Procesa selected_price (fallback a 135.00)
       ↓
   Crea payment.transaction
       ↓
   Genera firma 3DES-CBC ✓
       ↓
   Genera HTML con formulario auto-submit
       ↓
   Retorna HTML → Navegador
       ↓
   JavaScript intenta procesar → ERROR
```

**El problema está entre "Genera HTML" y "Retorna HTML"**

---

## ANÁLISIS DEL CÓDIGO ESPECÍFICO

### Código en `web_contract_booking_fixed.py` línea 2812-2970:

```python
# RECEPCIÓN DEL POST
selected_price_str = kw.get('selected_price', '').strip()
selected_price = float(selected_price_str) if selected_price_str else 0

# FALLBACK si está vacío
if selected_price <= 0:
    selected_price = 135.00  # ✓ Debería funcionar

# CREACIÓN DE TRANSACTION
tx = request.env['payment.transaction'].sudo().create({
    'provider_id': provider_id,
    'amount': selected_price,  # ✓ Debería ser 135.00
    'currency_id': request.env.company.currency_id.id,
    'partner_id': partner_id,
    'reference': order_number,
    'state': 'draft',
})

# CÁLCULO DE AMOUNT EN CENTAVOS
amount_cents = int(selected_price * 100)  # ✓ Debería ser 13500

# PARÁMETROS PARA REDSYS
merchant_data = {
    'Ds_Merchant_Amount': str(amount_cents),  # ✓ Debería ser "13500"
    ...
}

# GENERACIÓN DE FIRMA
derived_key = self._derive_key_3des_cbc(secret_key, order_number)
signature = hmac.new(derived_key, merchant_params.encode(), hashlib.sha256).digest()
signature_b64 = base64.b64encode(signature).decode()

# FORMULARIO HTML
html_form = f'''<!DOCTYPE html>
...
<input type="hidden" name="Ds_Signature" value="{signature_b64}"/>
...
'''

# RETORNO
return Response(html_form, mimetype='text/html')
```

**El código PARECE correcto, pero...**

---

## HIPÓTESIS DE ROOT CAUSE REAL

### Hipótesis 1: `selected_price` Se Envía Realmente Vacío

**Evidencia:**
- El error SIS0042 con "0,00 EUR" sugiere que Redsys recibe amount=0
- El fallback a 135.00 existe pero podría no aplicarse correctamente
- El valor vacío viene del formulario HTML porque el usuario NO selecciona tarifa

**Validación necesaria:**
- Ver los logs del servidor en `/var/log/odoo/odoo.log`
- Buscar líneas como: `[WARN] REDSYS_PARAMS:` y `[INFO] Signature generated`
- Si aparece `Ds_Merchant_Amount: 0`, entonces el problema es en el endpoint

### Hipótesis 2: El Formulario HTML No Se Retorna Correctamente

**Evidencia:**
- Error JavaScript: `Cannot read properties of null (reading 'body')`
- Esto sugiere que el HTML retornado es null o está corrupto
- El endpoint `/rental/payment` puede estar fallando silenciosamente

**Validación necesaria:**
- Hacer una llamada POST directa a `/rental/payment` con parámetros
- Ver si retorna HTML válido
- Ver si hay excepciones no capturadas

### Hipótesis 3: Falta Integración Con `payment_redsys` Estándar

**Evidencia:**
- El módulo espera que Odoo's `payment_redsys` maneje el formulario
- Pero el código customizado en `web_contract_booking_fixed.py` intenta hacer todo manualmente
- La ruta `/rental/payment` no delega a Odoo, genera el HTML manualmente
- Esto puede causar incompatibilidades con el flujo estándar

---

## FLUJO ESPERADO (ODOO ESTÁNDAR)

El flujo correcto en Odoo 19 sería:

1. Usuario POST a `/web/rental/payment` (custom endpoint)
2. Endpoint crea `payment.transaction` sin generar firma
3. Odoo automáticamente renderiza template `payment_form`
4. Template `payment_form` (del módulo `payment_redsys`) genera la firma
5. El módulo `payment_redsys` maneja validaciones y firma
6. Formulario se auto-submit a Redsys

**PERO EL CÓDIGO ACTUAL:**
1. Usuario POST a `/rental/payment`
2. Endpoint genera TODO manualmente (firma, HTML, formulario)
3. Retorna HTML directamente
4. JavaScript intenta procesarlo pero falla

---

## CONCLUSIÓN

El problema real parece ser una **COMBINACIÓN de:**

1. **Interfaz incompleta:** El usuario no entiende que debe seleccionar una tarifa
2. **Fallback insuficiente:** El fallback de 135.00 puede no aplicarse en todos los casos
3. **Generación manual de formulario:** El endpoint genera todo manualmente en lugar de delegar a Odoo
4. **Falta de validaciones:** No hay verificación clara de que `selected_price` sea válido antes de crear la transacción
5. **Conflicto de rutas:** Hay dos controladores con `/rental/payment` que pueden causar comportamiento impredecible

---

## ARCHIVOS A REVISAR

- `/opt/saas/clientes/sunsetrentpinveco/addons-extra/vehicle_rental/controllers/web_contract_booking_fixed.py` (línea 2795-2970)
- `/opt/saas/clientes/sunsetrentpinveco/addons-extra/vehicle_rental/controllers/payment_controller.py` (línea 12+)
- `/opt/saas/clientes/sunsetrentpinveco/addons-extra/vehicle_rental/controllers/payment_gateway.py` (línea 9+)
- `/opt/saas/clientes/sunsetrentpinveco/addons-extra/vehicle_rental/static/src/js/redsys_payment_handler.js`
- Logs de Odoo: `/var/log/odoo/odoo.log`

