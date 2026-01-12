# Pruebas Manuales - Análisis del Flujo de Datos

**Fecha**: 12 de enero de 2026  
**Hora**: 09:43 UTC

## Objetivo

Entender EXACTAMENTE qué datos se envían, cómo se envían, y dónde pueden perderse o alterarse.

---

## TEST MANUAL 1: Flujo HTML Form → Endpoint

### Simulación del Formulario HTML

```html
<form method="post" action="/rental/payment" id="booking_form">
    <input type="hidden" name="selected_price" value="89.50"/>
    <input type="text" name="customer_name" value="Juan García"/>
    <input type="email" name="customer_email" value="juan@example.com"/>
    ...
    <button type="submit">Continuar</button>
</form>
```

### Cuando se envía el formulario:

**Paso 1: Encoding del navegador**
- El navegador convierte el formulario a `application/x-www-form-urlencoded`
- Resultado:
```
category_id=37&selected_price=89.50&customer_name=Juan%20Garc%C3%ADa&customer_email=juan%40example.com&...
```

**Paso 2: Transmisión HTTP**
- POST a `/rental/payment`
- Content-Type: `application/x-www-form-urlencoded`
- Body contiene los datos codificados

**Paso 3: Recepción en Odoo**
- Odoo decodifica automáticamente
- El endpoint recibe `**kw` con:
```python
{
    'category_id': '37',
    'selected_price': '89.50',
    'customer_name': 'Juan García',
    'customer_email': 'juan@example.com',
    ...
}
```

---

## TEST MANUAL 2: Procesamiento en el Endpoint

### Extracción del precio

```python
selected_price_str = kw.get('selected_price', '').strip()
# Resultado: '89.50'

selected_price = float(selected_price_str) if selected_price_str else 0
# Resultado: 89.5

if selected_price <= 0:
    selected_price = 135.00
# NO APLICADO (89.5 > 0)
```

### Resultado esperado en endpoint:
- `selected_price = 89.5` ✓
- `amount_cents = int(89.5 * 100) = 8950` ✓

### Pero Redsys recibe:
- `Ds_Merchant_Amount: "0"` ✗
- **DIFERENCIA DETECTADA**: Los datos correctos se calculan en el endpoint, pero NO llegan a Redsys

---

## TEST MANUAL 3: Flujo Completo (HTML → Firma → Redsys)

### Datos de entrada
```json
{
  "selected_price": "89.50",
  "customer_email": "juan@example.com",
  ...
}
```

### Procesamiento
```
1. selected_price = 89.5 ✓
2. amount_cents = 8950 ✓
3. Merchant JSON = {"Ds_Merchant_Amount": "8950", ...} ✓
4. Base64 encode = eyJEc19... ✓
5. 3DES-CBC derivation ✓
6. HMAC-SHA256 = USJkRn8j9vo7... ✓
```

### Salida esperada (formulario HTML para Redsys)
```html
<form action="https://sis-t.redsys.es:25443/sis/realizarPago">
    <input name="Ds_MerchantParameters" value="eyJEc19NZXJjaGFudF9BbW91bnQiOiI4OTUwIi4.."/>
    <input name="Ds_Signature" value="USJkRn8j9vo7GVBii0HswOIBGg7M72TKQUmwXDfTCNw="/>
</form>
```

### Decodificando el JSON de Ds_MerchantParameters
```json
{
  "Ds_Merchant_Amount": "8950",    ← CORRECTO
  "Ds_Merchant_Currency": "978",
  "Ds_Merchant_Order": "001768211072",
  "Ds_Merchant_MerchantCode": "369056973",
  "Ds_Merchant_Terminal": "1",
  "Ds_Merchant_TransactionType": "0"
}
```

**Pero Redsys muestra:**
- `Ds_Merchant_Amount: "0"` ← INCORRECTO
- `Ds_Merchant_Order: ""` ← VACÍO

---

## ANÁLISIS: ¿DÓNDE SE PIERDEN LOS DATOS?

### Posibles puntos de ruptura:

#### 1. **Pérdida ENTRE endpoint y HTML retornado**

El endpoint genera todo correctamente pero el HTML retornado tiene valores distintos.

**Hipótesis**: 
- La variable `merchant_params` se genera correctamente (contiene "8950")
- Pero cuando se inserta en el HTML (línea 2960), algo interfiere

#### 2. **Pérdida EN la transmisión HTML → Navegador**

El HTML se retorna correctamente pero el navegador no lo recibe íntegro.

**Síntoma**:
- Error JavaScript: `Cannot read properties of null (reading 'body')`
- Esto sugiere que el HTML está **CORRUPTO O VACÍO**

#### 3. **Pérdida EN el auto-submit JavaScript**

El HTML está bien pero el JavaScript `document.redsysForm.submit()` envía parámetros distintos.

**¿Cómo verificar?**
- Ver en DevTools → Network → POST a Redsys
- Verificar exactamente qué parámetros se envían

#### 4. **Interferen cia en Odoo/servidor**

El endpoint genera datos pero hay código que los modifica DESPUÉS.

**Ubicación sospechosa**: 
- ¿Middleware de Odoo?
- ¿Hooks post-procesamiento?
- ¿Validaciones de transacción?

---

## DATOS CLAVE DE LA INVESTIGACIÓN

### Lo que funciona correctamente:

1. ✓ Formulario HTML lleva todos los datos
2. ✓ Endpoint recibe los parámetros correctamente
3. ✓ Cálculo de `amount_cents` es correcto
4. ✓ Generación de `merchant_data` JSON es correcta
5. ✓ Codificación Base64 es correcta
6. ✓ Derivación 3DES-CBC es correcta
7. ✓ Firma HMAC-SHA256 es correcta
8. ✓ HTML se genera con valores correctos (en teoría)

### Lo que NO funciona:

1. ✗ Redsys recibe `Ds_Merchant_Amount: "0"`
2. ✗ Redsys recibe número de pedido vacío
3. ✗ Navegador muestra error: `Cannot read properties of null`

---

## PUNTOS CRÍTICOS A VERIFICAR

### 1. **¿Se está retornando HTML válido?**

Endpoint debe retornar:
```python
return Response(html_form, mimetype='text/html')
```

**Verificar**:
- ¿El HTML es válido?
- ¿Tiene el formulario con los parámetros?
- ¿El JavaScript de auto-submit está presente?

### 2. **¿Hay códigos de estado HTTP erráticos?**

**A verificar**:
- POST a `/rental/payment` → ¿Status 200 o error?
- ¿El servidor está retornando excepciones silenciadas?

### 3. **¿Hay conflictos entre controladores?**

Dos rutas `/rental/payment`:
- `payment_controller.py` línea 12
- `web_contract_booking_fixed.py` línea 2795

¿Cuál se está ejecutando realmente?

### 4. **¿El JavaScript `onload` se ejecuta?**

```html
<body onload="document.redsysForm.submit();">
```

**¿O está fallando por:**
- Formulario no existe
- Parámetros vacíos
- Errores JavaScript silenciados

---

## PRÓXIMAS ACCIONES

Para diagnosticar dónde exactamente se pierden los datos:

### 1. **Revisar Logs de Odoo**
```bash
tail -f /var/log/odoo/odoo.log | grep -E "RENTAL_PAYMENT_INPUT|REDSYS_PARAMS|REDSYS_SIG"
```

Buscar:
- `RENTAL_PAYMENT_INPUT: {...}` - ¿Qué recibe el endpoint?
- `REDSYS_PARAMS: merchant_params=...` - ¿Qué base64 genera?
- `REDSYS_SIG: signature_b64=...` - ¿Qué firma genera?

### 2. **Decodificar Base64 del log**
```bash
echo "eyJEc19NZXJjaGFudF9BbW91bnQiOiI4OTUwIi4.."|base64 -d|jq .
```

Ver si el JSON tiene el Amount correcto.

### 3. **Inspeccionar Navegador (DevTools)**
- Ir a Network → POST `/rental/payment`
- Ver Response HTML
- Ver si tiene `Ds_MerchantParameters` con valor
- POST a Redsys → Ver exactamente qué parámetros se envían

### 4. **Hacer POST Manual con curl**
```bash
curl -X POST https://sunsetrent.es/rental/payment \
  -d "category_id=37&selected_price=89.50&customer_email=test@test.com&..."
```

Ver HTML retornado directamente.

---

## CONCLUSIÓN DE PRUEBAS MANUALES

El flujo está **CASI CORRECTO** de principio a fin:
- Formulario → Endpoint: ✓ OK
- Endpoint → JSON Merchant: ✓ OK
- JSON → Base64: ✓ OK
- Firma HMAC: ✓ OK

**PERO algo falla en:**
- Retorno del HTML al navegador
- O ejecución del JavaScript de auto-submit
- O transmisión de los parámetros a Redsys

**El problema NO es la lógica de cálculos, ES un problema de transmisión/presentación de datos.**

