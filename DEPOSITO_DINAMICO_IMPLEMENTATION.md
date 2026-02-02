# SISTEMA DE DEPÓSITO DINÁMICO POR TIPO DE TARJETA

## IMPLEMENTACIÓN COMPLETADA

### FASE 1 ✓ COMPLETADA
**Extender modelo de tarifas con campos de depósito**

Cambios realizados:
- Modelo `vehicle_pricing_rule`: Añadidos campos `deposit_debit` y `deposit_credit` (Monetary)
- Cada tarifa ahora puede tener depósito específico para débito y crédito
- Archivo: `models/vehicle_pricing_rule.py`

### FASE 2 ✓ COMPLETADA
**Modelo de Depósitos Dinámicos**

Nuevo archivo creado: `models/vehicle_deposit_rule.py`

Características:
- Modelo `vehicle.deposit.rule` para gestionar depósitos por:
  - Categoría de vehículo
  - Tipo de tarjeta (débito/crédito)
  - Precio del alquiler
  
- Métodos principales:
  - `calculate_deposit(rental_price)`: Calcula depósito con soporte para:
    - Depósito fijo
    - Porcentaje sobre el alquiler
    - Límite mínimo y máximo
    - Opción de aplicar ambos (fijo + porcentaje)
  
  - `find_deposit_rule(category_id, card_type, date)`: Busca regla vigente
  - `get_deposit_amount(category_id, card_type, rental_price)`: Obtiene monto final

- Vista XML creada con:
  - Tree view (listado)
  - Form view (edición)
  - Search view (búsqueda y filtros)
  - Menu en Configuración

- Permisos añadidos:
  - Usuarios: lectura
  - Administradores: lectura, escritura, creación, eliminación

Commit: "FASE 1: Extender tarifas con campos de depósito + modelo vehicle.deposit.rule"

### FASE 3 ✓ COMPLETADA
**Integración de cálculo dinámico en pago**

Cambios en `controllers/rental_payment_fixed.py`:
- Captura de `card_type` del formulario web ('debit' o 'credit')
- Captura de `card_bin` (primeros 6 dígitos de tarjeta)
- Cálculo automático: `deposit_amount = vehicle.deposit.rule.get_deposit_amount()`
- Total a pagar: `total_with_deposit = rental_price + deposit_amount`
- Envío a Redsys del monto total (alquiler + depósito)
- Almacenamiento de todos los datos en `booking_data` para le sesión

Datos guardados en sesión:
```python
booking_data = {
    'total_price': precio_alquiler,
    'deposit_amount': deposito_calculado,
    'total_with_deposit': total_con_deposito,
    'card_type': tipo_tarjeta,  # 'debit' o 'credit'
    'card_bin': primeros_6_digitos,
    ...
}
```

Commit: "FASE 2: Integrar calculo de deposito dinamico en rental_payment_fixed.py"

### FASE 4 ✓ COMPLETADA
**Validación de tarjeta con Freebinchecker**

Nuevo archivo: `static/src/js/card_validation.js`

Características:
- Captura automática del número de tarjeta (primeros 6 dígitos = BIN)
- Llamada a API Freebinchecker: `https://lookup.binlist.net/{BIN}`
- Detección automática de tipo de tarjeta (debit/credit)
- Actualización dinámica del selector de tipo de tarjeta
- Manejo de errores si Freebinchecker no está disponible
- Logging para debugging

Commit: "FASE 3: Añadir validacion de tarjeta con Freebinchecker (assets + JS)"

---

## SIGUIENTES PASOS PENDIENTES

### FASE 5: ACTUALIZAR FORMULARIO WEB (SIGUIENTE)
**Añadir campos de tarjeta al formulario de reserva**

Archivo a modificar: `controllers/web_contract_booking_fixed.py` (línea ~1320)

Campos a añadir después de "Fecha de Expiración del DNI":
```html
<hr class="my-4">
<h5 class="mb-3">Información de Pago</h5>
<div class="row">
    <div class="col-md-6 mb-3">
        <label for="card_type" class="form-label">Tipo de Tarjeta <span class="text-danger">*</span></label>
        <select class="form-select" id="card_type" name="card_type" required>
            <option value="">Selecciona tipo...</option>
            <option value="debit">Tarjeta de Débito</option>
            <option value="credit">Tarjeta de Crédito</option>
        </select>
        <small class="text-muted">Se detectará automáticamente al ingresar el número</small>
    </div>
    <div class="col-md-6 mb-3">
        <label for="card_number" class="form-label">Número de Tarjeta <span class="text-danger">*</span></label>
        <input type="text" class="form-control" id="card_number" name="card_number" 
               placeholder="Solo se validarán los 6 primeros dígitos" 
               inputmode="numeric" required/>
        <input type="hidden" id="card_bin" name="card_bin" />
        <small class="text-muted">Se validará con Freebinchecker</small>
    </div>
</div>

<!-- Sección de Depósito Dinámico -->
<div class="row">
    <div class="col-md-6 mb-3">
        <div class="alert alert-info">
            <strong>Depósito Calculado:</strong>
            <div id="deposit_display">Selecciona tipo de tarjeta para ver depósito</div>
        </div>
    </div>
    <div class="col-md-6 mb-3">
        <div class="alert alert-warning">
            <strong>Total a Pagar:</strong>
            <div id="total_display">0€</div>
        </div>
    </div>
</div>
```

### FASE 6: VALIDACIÓN EN FRONTEND (SIGUIENTE DESPUÉS DE 5)
**Validar que el formulario envíe campos de tarjeta**

Actualizar JavaScript del formulario para:
- Incluir `card_type` y `card_bin` en la validación
- Asegurar que se envíen al servidor en POST

### FASE 7: TEST Y AJUSTES (FINAL)
**Probar el flujo completo**

1. Acceder a formulario de reserva
2. Ingresar número de tarjeta (6+ dígitos)
3. Verificar detección automática con Freebinchecker
4. Verificar cálculo de depósito
5. Proceder al pago con Redsys
6. Verificar que el monto total incluye alquiler + depósito

---

## CONFIGURACIÓN REQUERIDA EN ODOO

Antes de usar, crear reglas de depósito en:
**Menú: Configuración → Reglas de Depósitos**

Ejemplo de reglas:
- Categoría: Tipo A
- Tarjeta Débito: Depósito 50€
- Tarjeta Crédito: Depósito 25€

O con porcentaje:
- Depósito Fijo: 0€
- Porcentaje sobre Alquiler: 15%
- Aplicar Ambos: No (toma el máximo)

---

## ESTADO ACTUAL DE COMMITS

```
83eed17 FASE 1: Extender tarifas con campos de depósito + modelo vehicle.deposit.rule
97d148f FASE 2: Integrar calculo de deposito dinamico en rental_payment_fixed.py
36fc28e FASE 3: Añadir validacion de tarjeta con Freebinchecker (assets + JS)
```

---

## FLUJO FINAL DE PAGO

1. Usuario selecciona tipo de tarjeta
2. Usuario ingresa número de tarjeta (6 dígitos)
3. JavaScript valida con Freebinchecker y actualiza tipo automáticamente
4. Se muestra depósito calculado dinámicamente
5. Usuario ve total = alquiler + depósito
6. Usuario envía formulario con `card_type` y `card_bin`
7. Servidor calcula depósito final y suma al precio
8. Redsys recibe: total_alquiler + deposito
9. Pago exitoso → Se crea el lead con datos completos

---

## ARCHIVOS MODIFICADOS/CREADOS

Nuevos:
- `models/vehicle_deposit_rule.py` ✓
- `views/vehicle_deposit_rule_views.xml` ✓
- `static/src/js/card_validation.js` ✓

Modificados:
- `models/__init__.py` ✓
- `models/vehicle_pricing_rule.py` ✓
- `controllers/rental_payment_fixed.py` ✓
- `__manifest__.py` ✓
- `security/ir.model.access.csv` ✓

Próximos a modificar:
- `controllers/web_contract_booking_fixed.py` (Fase 5)

---
