# Estado de Integración Redsys - Vehicle Rental Module

## Actualización: Redsys Funcionando ✅

**Fecha**: 2026-01-09  
**Estado**: Redsys correctamente integrado - Firmas válidas

### Resumen Ejecutivo

La integración Redsys ha sido **exitosamente corregida**. El problema raíz fue la generación incorrecta de la clave HMAC. Redsys requiere que la clave sea derivada usando 3DES-CBC con el número de orden como entrada, no simplemente decodificada en base64.

**Error anterior**: SIS0008 ("Error en datos enviados")  
**Causa**: Firma HMAC generada con clave incorrecta  
**Solución**: Implementar derivación 3DES-CBC según especificación Redsys  
**Resultado**: ✅ Firma válida - Redsys acepta los parámetros

### Cambios Realizados

#### 1. Redsys Payment Controller (`controllers/redsys_payment_controller.py`)

**Cambio principal**: Agregada función `derive_key_3des()` que implementa derivación correcta de clave

```python
def derive_key_3des(secret_b64: str, order: str) -> bytes:
    """
    Derivar clave HMAC a partir de secret base64 y número de orden usando 3DES-CBC
    Redsys requiere esta derivación para validar la firma correctamente
    """
    secret = base64.b64decode(secret_b64)
    order_bytes = order.encode('utf-8')
    pad = (-len(order_bytes)) % 8  # Padding a múltiplo de 8 (requerido 3DES)
    order_padded = order_bytes + b'\x00' * pad
    
    # Usar openssl para derivar: openssl enc -des-ede3-cbc -K <key_hex> -iv 0 -nopad
    # ... [resto de implementación con subprocess]
```

**Cambios en endpoints**:
- `/web/redsys/generate`: Ahora usa `type='http'` y retorna JSON valido con firma correcta
- `/web/booking-confirmation-redsys`: Usa la derivación 3DES para generar firma válida

**Verificación realizada**:
- Firma generada: `orBW98p6NuPw2HMZJhSoM3kABVc46mdGjI2vkz/+c0Q=`
- POST a Redsys sis-t: **200 OK con página de pago** (sin SIS0008)

### Validación de Corrección

#### Script manual (referencia anterior):
```
[OK] Firma: SCpUXIqEeXSWpTsE0C5TcXUJikNRFRgW8Vj0P+GjycA=
Respuesta Redsys: 200 OK - Pantalla de selección de pago
```

#### Controller actualizado (ahora):
```
[OK] Firma: orBW98p6NuPw2HMZJhSoM3kABVc46mdGjI2vkz/+c0Q=
Respuesta Redsys: 200 OK - HTML válido (sin SIS0008)
```

### Detalles Técnicos

**Algoritmo de derivación 3DES:**
- Input: Secret base64 (decodificado a 24 bytes) + Número de orden padded a 16 bytes (múltiplo de 8)
- Algoritmo: 3DES-CBC (des-ede3-cbc en OpenSSL)
- IV: 00000000 (8 bytes nulos)
- Padding: Nulo (0x00) hasta múltiplo de 8
- Output: 16 bytes (clave derivada)
- Uso: HMAC-SHA256 con merchant_params base64

**Cadena de derivación**:
```
secret_b64='sq7HjrUOBfKmC576ILgskD5srU870gJ7' (24 bytes decodificados)
      ↓ base64_decode
secret_bytes=b'\xb2\xae\xc7...' (24 bytes)
      ↓ 3DES-CBC con order padded
derived_key=b'\x1f\x9d\x61\xad...' (16 bytes)
      ↓ HMAC-SHA256
signature_bytes (32 bytes)
      ↓ base64_encode
Ds_Signature (43 bytes base64)
```

### Endpoints Disponibles

#### 1. `/web/redsys/generate` (GET/POST)
Genera parámetros y firma Redsys

**Request**:
```
GET http://sunsetrentpinveco.srv.cositt.net/web/redsys/generate?price=123.45
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "merchant_params": "eyJEU19NRVJDSEFOVF9BTU9VTlQiOi...",
  "signature": "orBW98p6NuPw2HMZJhSoM3kABVc46mdGjI2vkz/+c0Q=",
  "merchant_code": "369056973",
  "terminal": "1",
  "order_number": "001767944837"
}
```

#### 2. `/web/booking-confirmation-redsys` (POST)
Procesa confirmación de reserva y redirige a Redsys

**Integración completa**: El formulario auto-submit envia los parámetros a Redsys

### Siguientes Pasos

1. ✅ **COMPLETADO**: Corregir algoritmo de firma (derivación 3DES)
2. ✅ **COMPLETADO**: Validar que Redsys acepta los parámetros
3. **TODO**: Probar flujo completo desde interfaz de usuario
   - Acceder a página de reserva
   - Completar datos de cliente
   - Confirmar reserva
   - Validar que se abre formulario Redsys correctamente
4. **TODO**: Gestionar webhook de respuesta de Redsys (`/web/redsys-webhook`)
5. **TODO**: Externalizar credenciales Redsys (actualmente hardcoded)
6. **TODO**: Pruebas en ambiente de producción

### Archivos Modificados

- `controllers/redsys_payment_controller.py` - **Función de derivación 3DES agregada, firmas corregidas**
- `staado_redsys/tests_redsys.py` - Script de prueba manual (sin cambios)
- `staado_redsys/tests_redsys.sh` - Script bash de prueba manual (sin cambios)

### Credenciales Actuales (NOTA: Hardcoded - Externalizar)

```python
merchant_code = "369056973"
terminal = "1"
secret_key = "sq7HjrUOBfKmC576ILgskD5srU870gJ7"
```

### Referencias

- Especificación Redsys 3.0.1 - Apartado de Derivación de Clave
- Algoritmo: `openssl enc -des-ede3-cbc -K <hex> -iv 0000000000000000 -nopad`

---

**Estado actual**: ✅ Integración funcional  
**Última actualización**: 2026-01-09 07:45 UTC
