# Problema: selected_price llega vacío a /rental/payment

## Estado Actual
- El endpoint `/rental/payment` se llama correctamente
- El formulario se envía con `action="/rental/payment"`
- **Pero** el campo `selected_price` llega vacío (0)

## Causa Raíz
El campo `selected_price` en el formulario HTML se rellena con **JavaScript**:
- Línea 1213: `<input type="hidden" name="selected_price" id="selected_price" value=""/>`
- Línea 1427: `document.getElementById('selected_price').value = price;`

**Problema**: Este JavaScript se ejecuta cuando el usuario selecciona parámetros de alquiler (duración, km, etc.), pero:
1. Si el usuario llena el formulario incompleto, `selected_price` queda vacío
2. El JavaScript podría no ejecutarse correctamente
3. No hay validación que obligue al usuario a seleccionar primero el precio

## Soluciones Posibles

### Opción 1: Hacer obligatorio el cálculo de precio (más correcto)
- Agregar validación JavaScript que impida enviar el formulario sin precio
- Recalcular precio en el servidor si falta (fallback)

### Opción 2: Extraer precio de los parámetros (más robusto)
- El endpoint puede recibir `selected_duration`, `selected_km`, etc.
- Recalcular el precio en `/rental/payment` basado en tarifa de categoría
- No depender de un campo oculto JavaScript

### Opción 3: Recolectar datos primero (simplificar flujo)
- Crear un paso previo donde el usuario calcula el precio
- Luego enviar el formulario de pago con el precio precalculado

## Implementación Recomendada
**Opción 2** (recalcular en servidor) es la más robusta:
1. El endpoint recibe `category_id`, `start_date`, `end_date`, etc.
2. Busca la tarifa de la categoría
3. Calcula el precio automáticamente
4. Si `selected_price` llega, lo usa; si no, calcula

Esto hace el sistema independiente del JavaScript del cliente.

