# PLAN DE SOLUCIÓN - Arreglar Ds_Merchant_Order

**Fecha**: 12 de enero de 2026  
**Hora**: 09:53 UTC

---

## OPCIÓN 1: Usar tx.reference DESPUÉS de que Odoo lo recalcule

**Idea**: Leer `tx.reference` después de que se guarde y se recalcule automáticamente.

**Código**:
```python
# Crear transacción
tx = request.env['payment.transaction'].sudo().create({
    'reference': order_number,
    ...
})

# AQUÍ Odoo ya ha recalculado tx.reference a "ORD1767976393"
actual_reference = tx.reference  # "ORD1767976393"

# Usar este valor en merchant_data
merchant_data = {
    'Ds_Merchant_Order': actual_reference.zfill(12),
    ...
}
```

**Problema**: `"ORD1767976393"` NO se puede rellenar con `zfill(12)` porque:
- Ya tiene 13 caracteres
- Contiene letras (ORD)
- Redsys lo rechaza igual

**Veredicto**: ❌ NO FUNCIONA

---

## OPCIÓN 2: NO crear transacción manualmente, dejar que Odoo la cree

**Idea**: Redirigir a `/payment/process/{tx_id}` y dejar que Odoo's payment_redsys maneje todo.

**Cambio necesario**:
```python
# En lugar de generar HTML manualmente:
# return Response(html_form, mimetype='text/html')

# Hacer esto:
return request.redirect(f'/payment/process/{tx.id}')
```

**Ventaja**: Odoo manejaría el formato correcto automáticamente.

**Problema**: 
- Odoo's payment_redsys TAMBIÉN genera un `_compute_reference()` con prefijo ORD
- El problema seguiría existiendo en el módulo estándar de Odoo

**Veredicto**: ❌ NO FUNCIONA (el problema está en Odoo, no en nuestro código)

---

## OPCIÓN 3: Modificar tx.reference DESPUÉS de crearlo para que sea solo números

**Idea**: Crear la transacción, pero LUEGO modificar manualmente el reference.

**Código**:
```python
# Crear transacción
tx = request.env['payment.transaction'].sudo().create({
    'reference': order_number,
    ...
})

# MODIFICAR el reference a solo 12 dígitos DESPUÉS de la creación
clean_reference = order_number.zfill(12)  # "001767976393"
tx.sudo().write({'reference': clean_reference})

# Usar el reference limpio
merchant_data = {
    'Ds_Merchant_Order': clean_reference,
    ...
}
```

**Ventaja**: 
- Fuerza el reference a ser exactamente 12 dígitos numéricos
- Redsys lo acepta
- Simple de implementar

**Problema**:
- Odoo espera referencias con prefijo ORD para Redsys
- Pueden haber conflictos si Odoo recomputa la referencia más adelante
- Webhook de Redsys puede no encontrar la transacción si busca por reference prefijado

**Veredicto**: ⚠️ PODRÍA FUNCIONAR pero tiene riesgo

---

## OPCIÓN 4: Override _compute_reference en nuestro módulo

**Idea**: Crear un modelo que extienda `payment.transaction` y OVERRIDE `_compute_reference()` para Redsys.

**Ubicación**: Crear archivo `/models/payment_transaction.py` en vehicle_rental

**Código**:
```python
from odoo import models, fields

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """Override para Redsys: usar solo números sin prefijo ORD"""
        
        if provider_code != 'redsys':
            return super()._compute_reference(provider_code, prefix=prefix, separator=separator, **kwargs)
        
        # Para Redsys: mantener referencia como 12 dígitos numéricos
        # SIN prefijo ORD
        if not prefix:
            prefix = str(int(fields.Datetime.now().timestamp()))[-10:]
        
        # Usar solo los dígitos, sin prefijo automático
        reference = prefix.zfill(12)[:12]  # Máximo 12 caracteres, solo números
        
        return reference
```

**Ventaja**:
- Soluciona el problema en la raíz (donde lo genera Odoo)
- Compatible con todo el sistema de pagos de Odoo
- Redsys recibe exactamente lo que espera

**Problema**:
- Requiere crear un modelo heredado (más código)
- Puede tener efectos secundarios en otras partes del sistema de pagos

**Veredicto**: ✅ FUNCIONA BIEN (solución completa)

---

## RECOMENDACIÓN

**OPCIÓN 3 + OPCIÓN 4 (COMBINADAS)**:

1. **Corto plazo (OPCIÓN 3)**: Usar `tx.reference = clean_reference` después de crearlo
   - Arregla el problema inmediatamente
   - Simple de implementar
   - Riesgo bajo

2. **Largo plazo (OPCIÓN 4)**: Implementar override de `_compute_reference()`
   - Solución definitiva
   - Compatible con futuras actualizaciones de Odoo

---

## IMPLEMENTACIÓN RÁPIDA (OPCIÓN 3)

**Cambios en**: `/controllers/web_contract_booking_fixed.py` línea 2890

**De**:
```python
# Crear payment.transaction
tx = request.env['payment.transaction'].sudo().create({
    'provider_id': provider.id,
    'payment_method_id': payment_method.id,
    'amount': selected_price,
    'currency_id': request.env.company.currency_id.id,
    'partner_id': partner.id,
    'reference': order_number,
})

# LUEGO se usa order_number para merchant_data
merchant_data = {
    'Ds_Merchant_Order': order_number.zfill(12),  # "001767976393"
    ...
}
```

**A**:
```python
# Crear payment.transaction
tx = request.env['payment.transaction'].sudo().create({
    'provider_id': provider.id,
    'payment_method_id': payment_method.id,
    'amount': selected_price,
    'currency_id': request.env.company.currency_id.id,
    'partner_id': partner.id,
    'reference': order_number,
})

# ⭐ NUEVA LÍNEA: Limpiar la referencia después de crearla
# Odoo calcula tx.reference con prefijo ORD, pero nosotros lo reemplazamos
# con solo los 12 dígitos numéricos que Redsys requiere
clean_reference = order_number.zfill(12)  # "001767976393"
tx.sudo().write({'reference': clean_reference})

_logger.info(f"Created payment.transaction: {tx.id} with reference: {clean_reference}")

# AHORA usamos el reference limpio
merchant_data = {
    'Ds_Merchant_Order': clean_reference,  # ✅ "001767976393" (sin prefijo ORD)
    ...
}
```

---

## VERIFICACIÓN DE LA SOLUCIÓN

**Antes** (actual):
```
docker logs show: Ds_Merchant_Order: "ORD1767976393" → SIS0042 ❌
```

**Después** (con solución):
```
docker logs debería mostrar: Ds_Merchant_Order: "001767976393" → 200 OK ✅
```

