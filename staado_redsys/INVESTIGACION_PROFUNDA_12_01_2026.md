# Investigación Profunda - Pérdida de Datos en Flujo de Pago Redsys

**Fecha**: 12 de enero de 2026  
**Hora**: 09:40 UTC

## Corrección de Hipótesis Anteriores

**Punto 1 Corregido**: El usuario SIEMPRE rellena `selected_price` porque el botón de continuar NO se activa si no lo hace.

**Punto 2 Corregido**: Los datos están presentes en el JSON (según confirmación).

**Punto 3 - FOCO**: Debemos identificar EXACTAMENTE dónde se pierden los datos entre:
- ✓ El cliente genera/envía datos (JSON completo)
- ✗ El endpoint recibe datos incompletos (0.00 EUR, pedido vacío, etc.)

---

## Flujo de Datos - Análisis Detallado

### ETAPA 1: Cliente HTML → POST Form (línea 1275)

```python
<form method="post" action="/rental/payment" id="booking_form">
    <input type="hidden" name="category_id" value="{category_id}"/>
    <input type="hidden" name="selected_pricing_type" id="selected_pricing_type" value=""/>
    <input type="hidden" name="selected_duration" id="selected_duration" value=""/>
    <input type="hidden" name="selected_km" id="selected_km" value=""/>
    <input type="hidden" name="selected_price" id="selected_price" value=""/>  <!-- RELLENO POR JS -->
    <input type="hidden" name="selected_km_included" id="selected_km_included" value=""/>
    <input type="hidden" name="selected_package_days" id="selected_package_days" value=""/>
    <input type="hidden" name="selected_vehicle_id" id="selected_vehicle_id" value=""/>
    <input type="hidden" name="min_duration_days" id="min_duration_days" value=""/>
    <input type="hidden" name="max_duration_days" id="max_duration_days" value=""/>
    
    <input type="text" name="customer_name" required/>
    <input type="email" name="customer_email" required/>
    <input type="tel" name="customer_phone" required/>
    <input type="date" name="start_date"/>
    <input type="date" name="end_date"/>
    <input type="time" name="start_time"/>
    <input type="time" name="end_time"/>
    
    <button type="submit" id="submit_btn">Continuar con la reserva</button>
</form>
```

**JavaScript que rellena datos** (líneas 1496, 1556):
- Cuando selecciona tarifa fija: `document.getElementById('selected_price').value = price;`
- Cuando selecciona tarifa dinámica: `document.getElementById('selected_price').value = data.price;`

**Validación** (línea 1621-1700):
- El botón SOLO se habilita si:
  - Todos los campos de contacto están completos
  - Se ha seleccionado una tarifa (selected_price > 0)
  - Se ha seleccionado un vehículo
  - Las fechas son válidas

**PREGUNTA CRÍTICA**: ¿Qué datos exactos se envían en el POST?

---

### ETAPA 2: POST HTML → Endpoint `/rental/payment` (línea 2795)

**Endpoint recibe:**
```python
@http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
def rental_payment(self, **kw):
    _logger.error(f"RENTAL_PAYMENT_INPUT: {kw}")  # LINE 2808 - LOG ENTRADA
    
    # Extrae los parámetros
    selected_price_str = kw.get('selected_price', '').strip()
    selected_price = float(selected_price_str) if selected_price_str else 0
    
    # Fallback (línea 2816)
    if selected_price <= 0:
        selected_price = 135.00
```

**ANÁLISIS DE PUNTO DE RUPTURA**:
- Si `selected_price` llega como `""` → se convierte a 0 → fallback a 135.00
- Si `selected_price` llega con valor (ej "75.00") → se usa ese valor
- El log 2808 debería revelar EXACTAMENTE qué recibe

---

### ETAPA 3: Construcción de `merchant_data` (líneas 2910-2919)

```python
amount_cents = int(selected_price * 100)  # Si selected_price=135 → 13500

merchant_data = {
    'Ds_Merchant_Amount': str(amount_cents),      # "13500" o "0" ??
    'Ds_Merchant_Currency': '978',
    'Ds_Merchant_Order': order_number.zfill(12),  # Padding a 12 dígitos
    'Ds_Merchant_MerchantCode': '369056973',
    'Ds_Merchant_Terminal': '1',
    'Ds_Merchant_TransactionType': '0',
    'Ds_Merchant_MerchantURL': f'https://sunsetrent.es/payment/webhook/{tx.id}',
    'Ds_Merchant_UrlOK': 'https://sunsetrent.es/rental/success',
    'Ds_Merchant_UrlKO': 'https://sunsetrent.es/rental/error',
}
```

**Conversión JSON y Base64** (líneas 2923-2924):
```python
merchant_json = json.dumps(merchant_data, separators=(",", ":"))
merchant_params = base64.b64encode(merchant_json.encode()).decode()
```

**LOGS REGISTRADOS** (líneas 2948-2950):
```python
_logger.warning(f'REDSYS_FORM_HTML: {html_form}')
_logger.warning(f'REDSYS_PARAMS: merchant_params={merchant_params}')  # BASE64
_logger.warning(f'REDSYS_SIG: signature_b64={signature_b64}')
```

---

### ETAPA 4: HTML Retornado al Navegador (líneas 2953-2966)

```html
<!DOCTYPE html>
<html>
<body onload="document.redsysForm.submit();">
    <form name="redsysForm" action="https://sis-t.redsys.es:25443/sis/realizarPago" method="POST">
        <input type="hidden" name="Ds_SignatureVersion" value="HMAC_SHA256_V1"/>
        <input type="hidden" name="Ds_MerchantParameters" value="{merchant_params}"/>
        <input type="hidden" name="Ds_Signature" value="{signature_b64}"/>
    </form>
</body>
</html>
```

**Auto-submit** (onload):
- JavaScript: `document.redsysForm.submit()`
- Envía 3 parámetros directamente a Redsys

---

## PUNTOS DE RUPTURA POTENCIALES

### 1. **¿Llega `selected_price` incompleto al endpoint?**

**Evidencia a revisar:**
- Log línea 2808: `RENTAL_PAYMENT_INPUT: {kw}`
- Si `selected_price` está vacío → fallback toma 135.00
- Pero Redsys recibe 0.00, lo que significa...
  - **HIPÓTESIS**: El fallback NO se aplica correctamente
  - **HIPÓTESIS**: O el fallback se aplica pero LUEGO algo lo resetea a 0

---

### 2. **¿Dónde se resetea `amount_cents` a 0?**

Posible ruta:
1. `selected_price = 135.00` (fallback, línea 2816)
2. `amount_cents = int(selected_price * 100)` → 13500 (línea 2907)
3. `merchant_data['Ds_Merchant_Amount'] = str(amount_cents)` → "13500" (línea 2911)
4. ...PERO Redsys recibe "0"

**¿Dónde se modifica?**
- ¿Entre línea 2911 y línea 2950 (logs)?
- ¿En la conversión JSON?
- ¿En el base64?
- ¿En el HTML?
- ¿En la firma?

---

### 3. **¿El `order_number` es válido?**

Línea 2873:
```python
order_number = str(int(time_mod.time()))
```

Problema: `int(time.time())` produce números ENORMES (ej: 1736608800)

**Cuando se llena a 12 dígitos:**
```python
'Ds_Merchant_Order': order_number.zfill(12)
```

Si `time.time()` = 1736608800, `zfill(12)` = "1736608800" (10 dígitos, NO se rellena)

**Redsys espera EXACTAMENTE 12 dígitos**, ejemplo: "001767945100"

---

### 4. **¿Hay conflicto de rutas que cause que otro endpoint se ejecute?**

Dos rutas definen `/rental/payment`:
- `payment_controller.py` línea 12
- `web_contract_booking_fixed.py` línea 2795 (GANA por orden de carga)

¿Pero qué si hay intermitencia en el orden de carga?

---

## DATOS A RECOPILAR DE LOS LOGS

Para diagnosticar correctamente, NECESITAMOS ver:

1. **Entrada al endpoint** (línea 2808):
   ```
   RENTAL_PAYMENT_INPUT: {'category_id': '123', 'selected_price': '75.00', 'customer_email': '...', ...}
   ```

2. **Parámetros Redsys** (línea 2949):
   ```
   REDSYS_PARAMS: merchant_params=eyJEc19NZXJjaGFudF9BbW91bnQiOiIwIi4...
   ```
   Decodificar este base64 para ver el JSON real:
   ```json
   {"Ds_Merchant_Amount": "0", "Ds_Merchant_Order": "xyz", ...}
   ```

3. **Orden generado** (línea 2873):
   ```
   order_number = str(int(time_mod.time())) → "1736608800"
   order_number.zfill(12) → "1736608800" ← SIN RELLENO (10 dígitos)
   ```

---

## HIPÓTESIS PRINCIPAL

**El `amount_cents` se calcula correctamente PERO:**

1. Si `selected_price` llega vacío → fallback a 135.00
2. `amount_cents = int(135.00 * 100)` = 13500
3. `Ds_Merchant_Amount = "13500"`
4. **PERO** el log muestra `"0"` → significa que:
   - **O bien:** `selected_price` se convierte a 0 DESPUÉS del fallback
   - **O bien:** El fallback nunca se ejecuta (porque `selected_price > 0` pero es inválido)
   - **O bien:** Hay una segunda asignación que resetea `selected_price = 0`

---

## PUNTO CRÍTICO: Line 2814

```python
selected_price = float(selected_price_str) if selected_price_str else 0

# Recalcular a 135 EUR si está vacío
if selected_price <= 0:
    selected_price = 135.00
```

**¿Qué pasa si `selected_price_str = "0.00"`?**
- `selected_price = float("0.00")` = 0.0
- `if 0.0 <= 0:` → TRUE → `selected_price = 135.00` ✓

**¿Qué pasa si `selected_price_str = ""`?**
- `selected_price = 0` (else clause)
- `if 0 <= 0:` → TRUE → `selected_price = 135.00` ✓

**Debería funcionar...**

**PERO ¿y si llega como None?**
```python
selected_price = float(None)  # ValueError!
```

---

## PRÓXIMOS PASOS DE INVESTIGACIÓN

1. **REVISAR LOGS** en `/var/log/odoo/odoo.log`:
   - Buscar "RENTAL_PAYMENT_INPUT"
   - Decodificar "REDSYS_PARAMS" base64
   - Ver si hay excepciones silenciadas

2. **REVISAR NETWORK** en navegador (DevTools):
   - POST a `/rental/payment` → ¿qué form data se envía?
   - Respuesta HTML → ¿qué parámetros tiene?

3. **VALIDAR `order_number`**:
   - ¿Cuántos dígitos tiene realmente?
   - ¿Se rellena correctamente a 12?

4. **AÑADIR LOGS INTERMEDIOS**:
   - Después de fallback (línea 2817)
   - Después de crear transaction (línea 2894)
   - Antes de enviar a Redsys (línea 2950)

5. **PROBAR MANUALMENTE**:
   - Hacer POST directo con curl con datos conocidos
   - Ver si el endpoint genera firma correctamente

---

## CONCLUSIÓN

El problema NO es la firma 3DES-CBC (eso está bien implementado).

El problema ES QUE:
- **Los datos llegan incompletos AL ENDPOINT**
- **O se pierden DENTRO del endpoint**
- **O se resetean antes de ser enviados a Redsys**

La evidencia clave es que Redsys recibe `Ds_Merchant_Amount: "0"` y número de pedido vacío.

**NECESITAMOS LOGS para determinar DÓNDE EXACTAMENTE ocurre la pérdida.**

