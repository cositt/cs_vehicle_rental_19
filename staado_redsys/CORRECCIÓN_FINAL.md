# Corrección Final - Redsys SIS0008 Resuelto

## Problema Identificado y Corregido

**Error**: SIS0008 ("Error en datos enviados") al enviar parámetros de pago a Redsys

**Causa real**: El código de generación de firma estaba en `web_contract_booking_fixed.py` línea 2605-2609, usando el algoritmo incorrecto.

El código original hacía:
```python
secret_key_bytes = base64.b64decode(secret_key)
signature_bytes = hmac.new(secret_key_bytes, merchant_params.encode('utf-8'), hashlib.sha256).digest()
```

Pero Redsys **requiere derivación 3DES-CBC** de la clave según su especificación v3.0.1.

## Solución Aplicada

### Archivo modificado:
- `controllers/web_contract_booking_fixed.py` línea 2605-2639

### Nuevo código (correcto):
```python
# Generar firma HMAC_SHA256 con derivación 3DES-CBC
# Derivar clave según especificación Redsys
secret_decoded = base64.b64decode(secret_key)
order_bytes = order_number.encode('utf-8')
pad = (-len(order_bytes)) % 8
order_padded = order_bytes + b'\x00' * pad

with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f_order:
    f_order.write(order_padded)
    order_path = f_order.name

try:
    derived_path = tempfile.mktemp()
    key_hex = secret_decoded.hex()
    subprocess.check_call([
        'openssl', 'enc', '-des-ede3-cbc',
        '-K', key_hex,
        '-iv', '0000000000000000',
        '-nopad',
        '-in', order_path,
        '-out', derived_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    with open(derived_path, 'rb') as f:
        derived_key = f.read()
    os.unlink(derived_path)
finally:
    os.unlink(order_path)

signature_bytes = hmac.new(derived_key, merchant_params.encode('utf-8'), hashlib.sha256).digest()
signature = base64.b64encode(signature_bytes).decode('utf-8')
```

## Verificación

**Parámetros de prueba**:
- Merchant Code: 369056973
- Terminal: 1
- Order: 001767945100
- Amount: 123.45 EUR

**Firma generada**: `i0RqmnrS/FvDi+jAhqvHuSR+bBuy7zVz9u26IF6azFY=`

**Respuesta Redsys sis-t**: ✅ **200 OK** (sin SIS0008)

## Proceso

1. ✅ Identificado que el error estaba en `web_contract_booking_fixed.py`
2. ✅ Aplicada derivación 3DES-CBC correcta
3. ✅ Validado con Redsys sis-t (sin errores)
4. ✅ Reiniciado contenedor Odoo

## Flujo Afectado

El endpoint `/web/booking-confirmation` (POST) ahora:
1. Genera parámetros merchant con datos de la reserva
2. **CORRECTAMENTE** deriva la clave HMAC usando 3DES-CBC
3. Genera firma HMAC-SHA256 con clave derivada
4. Envía formulario auto-submit a Redsys con parámetros válidos

## Próximos Pasos

1. **Prueba en interfaz de usuario**: Acceder a página de reserva → completar datos → confirmar → validar que Redsys acepta el pago
2. **Webhook**: Implementar `/web/redsys-webhook` para procesar respuesta de Redsys
3. **Externalizar credenciales**: Mover `merchant_code`, `terminal`, `secret_key` a variables de entorno
4. **Pruebas en producción**: Cambiar URLs de `sis-t.redsys.es` a `sis.redsys.es`

---

**Estado**: ✅ **CORREGIDO - Pruebas exitosas**
**Fecha**: 2026-01-09 08:05 UTC
