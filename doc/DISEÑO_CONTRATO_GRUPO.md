# Diseño: Contrato Grupo (Alquiler Múltiple de Vehículos)

## Objetivo
Permitir alquilar varios vehículos a un mismo cliente bajo un contrato grupo,
manteniendo contratos individuales por vehículo con su propio ciclo de vida,
y consolidando la facturación en una sola factura.

## Arquitectura

### Modelo nuevo: `vehicle.contract.group`
Contenedor (NO hereda de `vehicle.contract`). Agrupa N contratos individuales.

| Campo              | Tipo                     | Descripción                          |
|--------------------|--------------------------|--------------------------------------|
| name               | Char (auto-secuencia)    | Referencia del grupo (GRP-XXXX)      |
| customer_id        | Many2one res.partner     | Cliente (se hereda a hijos)          |
| company_id         | Many2one res.company     | Compañía                             |
| start_date         | Datetime                 | Fecha inicio (min de hijos)          |
| end_date           | Datetime                 | Fecha fin (max de hijos)             |
| payment_type       | Selection                | Tipo de pago                         |
| pricing_type       | Selection                | standard / flexirent                 |
| tax_ids            | Many2many account.tax    | Impuestos                            |
| contract_ids       | One2many vehicle.contract| Contratos hijos                      |
| contract_count     | Integer computed          | Número de contratos                  |
| state              | Selection computed        | Calculado de hijos                   |
| total_amount       | Float computed            | Suma de total_vehicle_rent de hijos  |
| total_deposit      | Float computed            | Suma de depósitos de hijos           |
| invoice_ids        | Many2many account.move   | Facturas consolidadas                |
| notes              | Text                     | Observaciones                        |

### Campo nuevo en `vehicle.contract`
| Campo     | Tipo                              | Descripción                |
|-----------|-----------------------------------|----------------------------|
| group_id  | Many2one vehicle.contract.group   | Enlace al grupo (nullable) |
| is_grouped| Boolean computed                  | True si tiene group_id     |

### Estados del grupo (computed desde contract_ids.status)
- `draft`: todos los hijos en a_draft
- `active`: al menos un hijo en b_in_progress
- `partial_return`: algún hijo devuelto, otros activos
- `done`: todos en c_return
- `cancel`: todos en d_cancel

### Herencia padre→hijo
**Compartido (se define al crear):** customer_id, company_id
**Independiente por hijo:** vehicle_id, start_date, end_date, rent, pricing_type,
insurance_type, deposit, extra_service_ids, status, reference_no

### Facturación consolidada (Opción B)
- Las cuotas se crean normalmente en cada contrato hijo
- El grupo tiene botón "Facturar Período" que:
  1. Recoge cuotas pendientes (sin factura) de todos los hijos
  2. Genera UNA account.move con líneas agrupadas por vehículo [matrícula]
  3. Incluye: alquiler + seguro + depósito + servicios extras por cada hijo
  4. Marca las cuotas como facturadas y vincula la factura al grupo

### Wizard de reserva múltiple (dedicado)
Wizard `rental.multi.booking` con flujo paso a paso:
- Cabecera: cliente, compañía, tipo de pago
- Botón "Añadir Vehículo" → abre el wizard individual `rental.contract.booking`
  en modo multi-booking (misma UI: categoría, fechas, disponibilidad, seleccionar)
- Al pulsar "Reservar" en un vehículo, en vez de crear contrato, crea una línea
  `rental.multi.booking.line` con todos los datos (vehículo, fechas, tarifa, precio)
- Se repite para cada vehículo (cada uno con sus propias fechas y configuración)
- Botón "Crear Reserva Múltiple" genera:
  1. Un `vehicle.contract.group` (start_date=min, end_date=max de las líneas)
  2. N `vehicle.contract` (uno por línea), cada uno con SUS fechas

### Flujo técnico del "Añadir Vehículo"
1. `rental.multi.booking.action_add_vehicle()` abre `rental.contract.booking`
   con contexto `default_multi_booking_id`
2. El usuario configura categoría, fechas, ve disponibilidad
3. Pulsa "Reservar" → `fleet.vehicle.action_create_book_contract()` detecta
   `multi_booking_id` y llama `wizard._add_to_multi_booking(vehicle)`
4. Se crea la línea y se vuelve al form del multi-booking

### Añadir vehículo a grupo existente
Desde el form del grupo, botón "Añadir Vehículo" abre el wizard simple
`rental.contract.booking` pre-rellenado con el cliente y vinculado al grupo.

## Archivos nuevos
- `models/vehicle_contract_group.py` — Modelo grupo
- `models/fleet_vehicle_multi_booking.py` — Override de action_create_book_contract
- `views/vehicle_contract_group_views.xml` — Vistas grupo + herencia contrato
- `wizards/rental_multi_booking.py` — Wizard + líneas de reserva múltiple
- `wizards/rental_multi_booking_views.xml` — Vista dedicada del wizard

## Archivos modificados
- `models/__init__.py` (imports nuevos modelos)
- `models/vehicle_contract.py` (group_id, is_grouped + fix @api.model_create_multi)
- `wizards/__init__.py` (import rental_multi_booking)
- `wizards/rental_contract_booking.py` (multi_booking_id + _add_to_multi_booking)
- `wizards/rental_contract_booking_views.xml` (banner modo multi-booking + campo hidden)
- `views/menus.xml` (menús Contratos Grupo + Reserva Múltiple)
- `security/ir.model.access.csv` (permisos grupo, multi.booking, multi.booking.line)
- `__manifest__.py` (nuevos archivos data, versión 19.0.6.0)
