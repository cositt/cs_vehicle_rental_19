# Diseño: Ampliación de contrato con documentación firmable y facturación

**Modo investigación** – No implementado. Documento de referencia para una futura ampliación de contrato (extensión de fechas) con documento firmado por el cliente y facturación asociada.

---

## 1. Objetivo

Permitir **ampliar** un contrato de alquiler ya existente (por ejemplo, el cliente devuelve más tarde), con:

1. **Nueva documentación** que describa la ampliación y que **deba ser firmada por el cliente**.
2. **Facturación** por los días (u horas) adicionales.

---

## 2. Contexto actual en el módulo

- **vehicle.contract**: tiene `start_date`, `end_date`, `signature` (Binary), `date` (fecha de firma), y varias facturas: `invoice_id`, `deposit_invoice_id`, `extra_charge_invoice_id`, etc.
- **Sustitución de vehículo**: ya existe un addendum (`vehicle_substitution_addendum_report`) con PDF y zona de firma; se puede usar como patrón.
- **Facturación**: se crean `account.move` desde el contrato (alquiler, depósito, extras, cancelación). El contrato principal usa `vehicle_contract_pricing` y `action_create_invoice_automatic`.

---

## 3. Enfoque propuesto

### 3.1 Entidad: Ampliación de contrato

- **Modelo nuevo** (ej. `vehicle.contract.extension`):
  - `contract_id` → Many2one a `vehicle.contract` (contrato original).
  - `original_end_date` → fecha de fin original (información).
  - `new_end_date` → nueva fecha de fin acordada.
  - `extension_days` (o `extension_hours`) → calculado.
  - `daily_rate` → tarifa por día (o por hora) aplicada a la ampliación; **por defecto la del contrato**, pero el encargado puede **mantenerla o cambiarla**.
  - `extension_amount` → importe total (calculado: días × daily_rate), o editable si se permite.
  - `state`: `draft` | `sent` | `signed` | `invoiced` | `cancelled`.
  - `document_pdf` → Binary (opcional), o usar reporte QWeb como el addendum.
  - `signature` → Binary (firma del cliente).
  - `signature_date` → Datetime (cuándo firmó).
  - `extension_invoice_id` → Many2one `account.move` (factura de la ampliación).

- **Relación con contrato**: el contrato podría tener `extension_ids` (One2many) y, una vez la ampliación está `signed`, actualizar `contract.end_date` a `new_end_date` (o dejar solo el histórico en la ampliación, según política).

### 3.2 Documento a firmar

- **Reporte QWeb** (como `vehicle_substitution_addendum_report`):
  - Título tipo “Ampliación de contrato – [referencia contrato]”.
  - Resumen: contrato original, fechas originales, **nueva fecha de fin**, días/horas de ampliación, **importe a facturar**.
  - Condiciones (texto legal breve).
  - **Zona de firma** (imagen de firma si está guardada, o “Pendiente de firma”).
  - Acción de informe: `ir.actions.report` sobre `vehicle.contract.extension` con template PDF.

- **Flujo de firma** (opciones):
  - **A) Módulo Odoo Sign (recomendado)** – Ver sección 7 (Uso del módulo Odoo Sign).
  - **B)** Portal propio: botón “Firmar ampliación” que abre el PDF y un widget de firma, guarda `signature` y `signature_date` y pasa estado a `signed`.
  - **C)** Presencial: el empleado muestra el PDF y usa el campo `signature` en el formulario de Odoo.

### 3.3 Facturación

- **Momento**: cuando la ampliación esté **firmada** (`state == signed`), se permite generar la factura (botón “Crear factura de ampliación” o automático al marcar como firmada).
- **Contenido de la factura**:
  - Línea(s) de alquiler por los días/horas adicionales (producto de alquiler, cantidad = días/horas, precio = tarifa acordada).
  - Opcional: misma lógica de impuestos que en el contrato principal.
- **Vinculación**: `extension_invoice_id` en la ampliación; en la factura, `invoice_origin` o campo específico (ej. “Ampliación contrato REF”).
- **Estado**: al crear y validar la factura, pasar ampliación a `invoiced` y, si se desea, actualizar `contract.end_date` al `new_end_date`.

### 3.4 Flujo resumido

1. Usuario crea **Ampliación** desde el contrato (wizard o botón “Ampliar contrato”).
2. Se rellenan nuevas fechas y tarifa; estado `draft`.
3. Se genera el **PDF** del documento de ampliación (reporte).
4. Se **envía al cliente** (portal o email con enlace).
5. Cliente **firma** (portal o presencial) → estado `signed`, se guardan `signature` y `signature_date`.
6. Usuario (o automatismo) **crea factura** de la ampliación → estado `invoiced`, se guarda `extension_invoice_id`.
7. Opcional: actualizar `contract.end_date` a `new_end_date` para que disponibilidad y resto de lógica usen la nueva fecha.

---

## 4. Flujo para el encargado (paso a paso)

Flujo desde el punto de vista del empleado que amplía el contrato (con Odoo Sign como opción de firma).

### 4.1 Crear la ampliación

1. El encargado abre el **contrato** que quiere ampliar (estado En curso o similar).
2. Pulsa el botón **“Ampliar contrato”** (o “Nueva ampliación”).
3. Se abre un **formulario de ampliación** (o un wizard):
   - Contrato: ya rellenado (el actual).
   - **Fecha de fin original**: solo lectura (la del contrato).
   - **Nueva fecha de fin**: el encargado la elige (ej. un día más).
   - **Tarifa aplicada**: el encargado puede **mantener la tarifa del contrato** (precargada) o **introducir otra** (ej. oferta por ampliación, tarifa de último momento). Campo precio por día (o por hora) editable.
   - **Importe total** de la ampliación: calculado (días × tarifa); solo lectura o editable según política.
4. Guarda. La ampliación queda en estado **Borrador**.

### 4.2 Enviar a firmar al cliente

5. En el formulario de la ampliación, pulsa **“Enviar a firmar”**.
6. Se abre el **wizard de Odoo Sign** (o el flujo de envío que se implemente):
   - Plantilla: “Ampliación de contrato” (ya preseleccionada si se fija por defecto).
   - **Firmante**: el cliente del contrato (contacto del contrato); el email se rellena automáticamente.
   - Asunto y mensaje opcionales (ej. “Por favor firme la ampliación del contrato REF-XXX”).
7. El encargado pulsa **“Enviar”**. Sign envía el email al cliente con el enlace para firmar.
8. La ampliación pasa a estado **“Enviado”** (o “Pendiente de firma”) y en el chatter aparece la petición de firma vinculada.

### 4.3 Mientras el cliente no ha firmado

9. El encargado puede:
   - Ver el estado de la petición en Sign (Enviado / Firmado / Caducado).
   - Abrir la petición desde un botón “Ver petición de firma” en la ampliación.
   - Reenviar recordatorio si Sign lo permite.
   - Cancelar la ampliación si el cliente desiste (estado **Cancelada**).

### 4.4 Cuando el cliente ha firmado

10. Sign marca la petición como **Firmado** y, si está configurado, hace message_post en la ampliación y adjunta el PDF firmado.
11. La ampliación pasa automáticamente (o el encargado la marca) a estado **“Firmado”**.
12. En el formulario de la ampliación se habilita el botón **“Crear factura de ampliación”**.

### 4.5 Facturar y cerrar

13. El encargado pulsa **“Crear factura de ampliación”**.
14. Se crea una **factura de cliente** (out_invoice) con:
    - Línea: concepto “Ampliación de alquiler – REF contrato”, cantidad = días ampliados, precio = tarifa acordada.
    - Origen / referencia vinculada a la ampliación (y al contrato).
15. La ampliación pasa a estado **“Facturado”** y se guarda el enlace a la factura (`extension_invoice_id`).
16. Opcional: el sistema (o el encargado con un botón) **actualiza la fecha de fin del contrato** a la nueva fecha de fin, para que disponibilidad y listados usen ya la fecha ampliada.

### 4.6 Resumen visual para el encargado

| Paso | Acción del encargado | Estado ampliación |
|------|----------------------|-------------------|
| 1–4  | Abre contrato → “Ampliar contrato” → Rellena nueva fecha y tarifa → Guarda | Borrador |
| 5–8  | “Enviar a firmar” → Completa wizard Sign (cliente, email) → Envía | Enviado / Pendiente firma |
| 9    | (Opcional) Ver petición, recordatorio o cancelar | — |
| 10–12| Cliente firma → Ampliación pasa a Firmado → Aparece “Crear factura” | Firmado |
| 13–16| “Crear factura de ampliación” → Revisar/validar factura → (Opcional) Actualizar fecha fin contrato | Facturado |

### 4.7 Casos especiales

- **Cliente firma en oficina**: el encargado puede usar la opción “Compartir enlace” de Sign y que el cliente firme en una tablet/ordenador, o usar flujo presencial (imprimir addendum, firma en papel, escanear y adjuntar; en ese caso el estado “Firmado” sería manual).
- **Varias ampliaciones**: si se permiten varias ampliaciones por contrato, cada una tiene su propio documento y su propia factura; la “nueva fecha de fin” del contrato sería la de la última ampliación facturada.
- **Cancelar ampliación**: en Borrador o Enviado, el encargado puede cancelar la ampliación; si se usaba Sign, cancelar también la petición de firma.

---

## 5. Puntos a decidir antes de implementar

| Tema | Opciones |
|------|----------|
| Actualizar `contract.end_date` | Sí al firmar / Sí al facturar / No (solo histórico en ampliación) |
| Firma | Solo portal / Solo presencial / Ambos |
| Factura | Siempre manual tras firma / Automática al firmar / Borrador automático y usuario valida |
| Depósito | Mantener el mismo / Ajustar si política lo exige |
| Múltiples ampliaciones | Una por contrato / Varias ampliaciones encadenadas (varias firmas y facturas) |
| Tarifa de la ampliación | Siempre editable con valor por defecto = tarifa del contrato / Opción explícita “Usar tarifa del contrato” (checkbox) + campo solo si se desmarca |

---

## 6. Archivos / capas a tocar (cuando se implemente)

- **Modelo**: nuevo `vehicle_contract_extension.py` (o integrado en `vehicle_contract.py` como One2many).
- **Vistas**: formulario y árbol de ampliación; botón “Ampliar contrato” en formulario de contrato.
- **Informe**: nuevo XML en `reports/` (template PDF del documento de ampliación con zona de firma).
- **Facturación**: método `action_create_extension_invoice()` (similar a `action_create_extra_charge_invoice` o a la factura de alquiler en pricing).
- **Portal** (si se usa): controlador para mostrar documento + widget de firma y guardar `signature`/`signature_date`; posiblemente heredar de `portal.mixin` o usar `access_token` en la ampliación.

---

## 7. Uso del módulo Odoo Sign (Enterprise)

Sí se puede usar el **módulo Sign** de Odoo (Enterprise) para que el cliente firme el documento de ampliación. Ventajas: envío por email, firma electrónica en navegador, documento firmado guardado y enlace al registro desde Sign.

### 7.1 Cómo funciona Sign

- **sign.template**: plantilla de documento (PDF subido) con “sign items” (campos de firma, texto, etc.) y **roles** (quién debe firmar: ej. “Cliente”, “Empresa”).
- **sign.request**: petición de firma concreta; tiene `template_id`, `request_item_ids` (firmantes: partner_id + role_id), `reference`, `reference_doc` (enlace a un registro, ej. la ampliación) y `state`: `shared` | `sent` | `signed` | `canceled` | `expired`.
- **reference_doc**: es un campo Reference; permite vincular la petición a cualquier modelo que sea **mail.thread**. Al firmar, Sign puede adjuntar el PDF firmado al registro enlazado y hacer `message_post`.
- El wizard estándar **Sign → Enviar a firmar** (`sign_send_request`) permite elegir plantilla, firmantes por rol y opcionalmente `reference_doc` (desde contexto `default_reference_doc`).

### 7.2 Integración con la ampliación

1. **Dependencia**: añadir `'sign'` en `depends` del módulo de ampliación (o del vehicle_rental si se integra ahí).
2. **Modelo ampliación**: que herede de `mail.thread` (para que pueda ser `reference_doc`) y tenga `sign_request_ids` (Many2many con `sign.request`) opcional, para listar peticiones desde el formulario (como hace `hr.version` en hr_sign).
3. **Plantilla Sign**: crear en Sign una plantilla “Ampliación de contrato”:
   - Subir el PDF del addendum de ampliación (generado por reporte QWeb o un PDF fijo).
   - Definir un rol “Cliente” y colocar un sign item de tipo firma para ese rol.
4. **Desde el formulario de ampliación**: botón “Enviar a firmar” que abre la acción del wizard de Sign con contexto:
   - `default_reference_doc`: `vehicle.contract.extension,<id>` (la ampliación actual).
   - `default_template_id`: id de la plantilla “Ampliación de contrato” (si se quiere fijar).
   El usuario completa en el wizard el firmante (cliente = `contract_id.customer_id` / `partner_id`) y envía; se crea un `sign.request` con `reference_doc` apuntando a la ampliación.
5. **Cuando el cliente firma**: el estado del `sign.request` pasa a `signed`. Opciones:
   - **Automático**: override de `write` en `sign.request` o método que se llame al completar (si Sign dispara algo sobre `reference_doc`), para actualizar el estado de la ampliación a `signed` y, si se desea, crear la factura o permitir el botón “Crear factura”.
   - **Manual**: el usuario ve en el chatter de la ampliación que el documento está firmado y pulsa “Crear factura de ampliación”.
6. **Documento firmado**: Sign guarda el PDF completado en `sign.request` (`completed_document_attachment_ids`); si `reference_doc` está puesto, el flujo estándar de Sign puede adjuntar una copia al registro enlazado (ver plantillas de correo en `sign/data/mail_templates.xml`).

### 7.3 Referencia en código Odoo

- **hr_sign**: `hr_contract_sign_document_wizard` crea `sign.request` desde contrato HR, asigna roles (empleado + responsable) y enlaza con `version_id.sign_request_ids`.
- **sign.request**: `reference_doc` en `sign_request.py`; wizard en `sign_send_request.py` (crea la petición con `reference_doc`).
- **Condición**: el modelo enlazado debe ser **mail.thread** (para que aparezca en la selección de `reference_doc` y en el wizard).

### 7.4 Resumen

| Aspecto | Con Sign |
|--------|----------|
| Envío al cliente | Por email desde Sign |
| Firma | En navegador (enlace del email) |
| Documento firmado | Guardado en Sign y opcionalmente adjunto al registro |
| Vinculación | `sign.request.reference_doc` → ampliación |
| Cambio de estado ampliación | Manual o con lógica al pasar `sign.request` a `signed` |
| Facturación | Igual que en el diseño base: al estar firmado, crear factura desde ampliación |

---

## 8. Referencias en el código actual

- Contrato: `models/vehicle_contract.py` (signature, date, invoice_id, deposit_invoice_id, etc.).
- Addendum sustitución: `report/vehicle_substitution_addendum_report.xml`.
- Factura desde contrato: `models/vehicle_contract_pricing.py` → `action_create_invoice_automatic`; `vehicle_contract.py` → `action_create_extra_charge_invoice`, depósito, etc.
- Odoo Sign (Enterprise): `enterprise-19.0/sign/` (sign.request, sign.template, reference_doc); `enterprise-19.0/hr_sign/` (wizard y enlace sign_request_ids en hr.version).

Este documento queda como **solo diseño/investigación**; no implica cambios en el código hasta que se decida aplicarlo.
