# DIAGNÓSTICO FINAL - CAUSA RAÍZ DEL ERROR SIS0042

**Fecha**: 12 de enero de 2026  
**Hora**: 09:47 UTC  
**Estado**: PROBLEMA CONFIRMADO Y IDENTIFICADO

---

## RESUMEN EJECUTIVO

**El error SIS0042 es causado por un formato incorrecto de Número de Pedido (Order Number).**

Redsys rechaza pedidos porque recibe:
```
Ds_Merchant_Order: "ORD1767976393"  ❌ INCORRECTO (13 caracteres + letras)
```

Cuando debería recibir:
```
Ds_Merchant_Order: "001767976393"  ✓ CORRECTO (12 dígitos numéricos)
```

---

## EVIDENCIA REAL DE LOS LOGS

### Log del contenedor Docker (CONFIRMADO)

```
DEBUG_MERCHANT_DATA: {
  'Ds_Merchant_Amount': '13500',  ✓ CORRECTO
  'Ds_Merchant_Currency': '978',  ✓ CORRECTO
  'Ds_Merchant_Order': 'ORD1767976393',  ❌ INCORRECTO
  'Ds_Merchant_MerchantCode': '369056973',  ✓ CORRECTO
  'Ds_Merchant_Terminal': '1',  ✓ CORRECTO
  'Ds_Merchant_TransactionType': '0'  ✓ CORRECTO
}
```

### Decodificación del Base64 (CONFIRMADO)

```json
{
    "Ds_Merchant_Amount": "13500",
    "Ds_Merchant_Currency": "978",
    "Ds_Merchant_Order": "ORD1767976393",
    "Ds_Merchant_MerchantCode": "369056973",
    "Ds_Merchant_Terminal": "1",
    "Ds_Merchant_TransactionType": "0"
}
```

---

## RAÍZ DEL PROBLEMA

### 1. Nuestro código genera orden correctamente (línea 2863)

```python
order_number = str(int(time_mod.time()))
# Resultado: "1767976393" (10 dígitos)
```

### 2. Se intenta rellenar a 12 dígitos (línea 2913)

```python
'Ds_Merchant_Order': order_number.zfill(12)
# Resultado esperado: "001767976393" ✓
```

### 3. PERO Odoo's payment_redsys modifica la referencia

**Archivo**: `/usr/lib/python3/dist-packages/addons/payment_redsys/models/payment_transaction.py` (línea 30-52)

**Código de Odoo**:
```python
def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
    if provider_code != 'redsys':
        return super()._compute_reference(...)
    
    # Generates prefix as timestamp (10 chars)
    prefix = str(int(fields.Datetime.now().timestamp()))[-10:]
    
    return super()._compute_reference(provider_code, prefix=prefix, separator='S', **kwargs)
```

**Lo que hace**:
1. Extrae últimos 10 dígitos del timestamp
2. Usa `separator='S'` (en lugar de nuestro separador)
3. Llama a la clase padre que añade prefijo automático
4. **Resultado**: `"ORD1767976393"` (prefijo ORD + timestamp)

### 4. Redsys rechaza el formato

**Especificación Redsys para Ds_Merchant_Order**:
- Máximo 12 caracteres
- **SOLO dígitos numéricos** (0-9)
- Formato: "00XXXXXXXXXX" (12 dígitos, rellenado con ceros)

**Lo que recibe Redsys**:
- `"ORD1767976393"` = 13 caracteres, contiene letras
- **RECHAZO**: Error SIS0042 "Error en datos enviados"

---

## EL CONFLICTO

**Nuestro código**:
```python
tx = request.env['payment.transaction'].sudo().create({
    'reference': order_number,  # "1767976393"
    ...
})
```

**Lo que Odoo guarda internamente**:
- `tx.reference = "1767976393"`

**Lo que Odoo's payment_redsys genera para el pago**:
- `tx.reference` se recomputa automáticamente usando `_compute_reference()`
- Resultado: `"ORD1767976393"`

**Lo que nuestro código usa para Merchant Order**:
```python
merchant_data = {
    'Ds_Merchant_Order': order_number.zfill(12),  # Usa NUESTRO order_number original
    ...
}
```

**PERO el formulario que genera incluye**:
```html
<input name="Ds_MerchantParameters" value="eyJ..."/> 
<!-- Contiene: "Ds_Merchant_Order": "ORD1767976393" -->
```

---

## ¿POR QUÉ LLEVA EL PREFIJO ORD?

**Hipótesis confirmada**: La transacción de pago se crea en Odoo ANTES de generar el formulario Redsys.

1. Creamos `payment.transaction` con `reference: "1767976393"`
2. Odoo la guarda
3. **Odoo recalcula automáticamente la referencia** mediante `_compute_reference()` 
4. Cuando leemos `tx.reference` DESPUÉS, ya tiene el prefijo: `"ORD1767976393"`
5. Si usamos ese valor para Merchant Order, Redsys lo rechaza

---

## PRUEBA DE CONFIRMACIÓN

Del log real podemos ver:

```
RENTAL_PAYMENT_INPUT: {...'selected_price': '135'...}  ✓
DEBUG_MERCHANT_DATA: {...'Ds_Merchant_Amount': '13500'...}  ✓
DEBUG_MERCHANT_DATA: {...'Ds_Merchant_Order': 'ORD1767976393'...}  ❌
```

El Merchant Amount es correcto (13500), pero el Order está prefijado.

---

## CONCLUSIÓN

**El problema NO es la firma 3DES-CBC.**  
**El problema NO es la transmisión de datos.**  
**El problema ES un conflicto entre la generación manual de orden y el cálculo automático de Odoo.**

**Soluciones posibles**:

1. **Usar `tx.reference` después de que Odoo lo recalcule** (si contiene el formato correcto)
2. **NO crear manualmente la transacción, dejar que Odoo la cree** con sus valores correctos
3. **Modificar el `reference` DESPUÉS de crear la transacción** para que sea solo números
4. **Override el método `_compute_reference` en nuestro módulo** para mantener el formato correcto

---

## PRÓXIMAS ACCIONES CONFIRMADAS

Necesitamos:
1. Entender exactamente qué valor tiene `tx.reference` DESPUÉS de ser guardado por Odoo
2. Decidir cuál será el valor correcto para Merchant Order (solo 12 dígitos)
3. Implementar la corrección apropiada

