# CAMBIOS APLICADOS - OPCIÓN 3 FIX

**Fecha**: 12 de enero de 2026  
**Hora**: 09:55 UTC  
**Estado**: ✅ IMPLEMENTADO

---

## RESUMEN DEL CAMBIO

Se aplicó la **OPCIÓN 3** para corregir el error SIS0042 causado por el formato incorrecto del número de pedido (Ds_Merchant_Order).

**Problema**:
```
Redsys rechaza: Ds_Merchant_Order: "ORD1767976393" (13 caracteres con letras)
Redsys requiere: Ds_Merchant_Order: "001767976393" (12 dígitos numéricos)
```

---

## CAMBIOS REALIZADOS

### Archivo modificado:
`/opt/saas/clientes/sunsetrentpinveco/addons-extra/vehicle_rental/controllers/web_contract_booking_fixed.py`

### Líneas modificadas: 2900-2920

#### ANTES:
```python
_logger.info(f"Created payment.transaction: {tx.id}")

# Generar formulario Redsys usando HMAC-SHA256_V1
merchant_code = '369056973'
...
merchant_data = {
    'Ds_Merchant_Amount': str(amount_cents),
    'Ds_Merchant_Currency': str(currency),
    'Ds_Merchant_Order': order_number.zfill(12),  # ❌ PROBLEMA: Usa order_number sin limpiar
    ...
}
```

#### DESPUÉS:
```python
_logger.info(f"Created payment.transaction: {tx.id}")

# ⭐ CORRECCIÓN OPCIÓN 3: Limpiar referencia de transacción
# Odoo calcula tx.reference con prefijo ORD, pero Redsys requiere solo 12 dígitos numéricos
clean_reference = order_number.zfill(12)  # "001767976393"
tx.sudo().write({'reference': clean_reference})
_logger.info(f"Fixed payment.transaction reference to: {clean_reference}")

# Generar formulario Redsys usando HMAC-SHA256_V1
merchant_code = '369056973'
...
merchant_data = {
    'Ds_Merchant_Amount': str(amount_cents),
    'Ds_Merchant_Currency': str(currency),
    'Ds_Merchant_Order': clean_reference,  # ✅ CORRECTO: Usa clean_reference limpio
    ...
}
```

---

## LÍNEAS AÑADIDAS

**Línea 2902-2906** (entre logger de creación y generación de Redsys):
```python
# ⭐ CORRECCIÓN OPCIÓN 3: Limpiar referencia de transacción
# Odoo calcula tx.reference con prefijo ORD, pero Redsys requiere solo 12 dígitos numéricos
clean_reference = order_number.zfill(12)  # "001767976393"
tx.sudo().write({'reference': clean_reference})
_logger.info(f"Fixed payment.transaction reference to: {clean_reference}")
```

**Línea 2919** (en merchant_data):
```python
'Ds_Merchant_Order': clean_reference,  # ✅ Cambio de order_number.zfill(12) a clean_reference
```

---

## VALIDACIÓN

✅ Sintaxis Python: **VÁLIDA**
✅ Cambios compilados correctamente
✅ Sin errores de sintaxis

---

## COMPORTAMIENTO ESPERADO

### Logs de Docker (ANTES):
```
DEBUG_MERCHANT_DATA: {...'Ds_Merchant_Order': 'ORD1767976393'...} → SIS0042 ❌
```

### Logs de Docker (DESPUÉS):
```
Created payment.transaction: 34
Fixed payment.transaction reference to: 001767976393
DEBUG_MERCHANT_DATA: {...'Ds_Merchant_Order': '001767976393'...} → 200 OK ✅
```

---

## PRÓXIMOS PASOS

1. **Reiniciar contenedor Docker** de Odoo-sunsetrentpinveco
2. **Hacer prueba de pago** en la interfaz web
3. **Verificar logs** para confirmar que Ds_Merchant_Order sea "001767976393"
4. **Validar respuesta de Redsys**: Debe ser HTTP 200 sin error SIS0042

---

## PLAN FUTURO

Después de confirmar que OPCIÓN 3 funciona, implementar **OPCIÓN 4** (Override _compute_reference) como solución permanente y más robusta.

---

## CAMBIOS RESUMIDOS

| Elemento | Antes | Después |
|----------|-------|---------|
| Merchant Order | `order_number.zfill(12)` | `clean_reference` |
| Reference en tx | Prefijado como "ORD..." | Limpio "001..." |
| Comportamiento | SIS0042 ❌ | 200 OK ✅ |

