# Manual de Uso - Módulo Vehicle Rental (Sunset)

## Índice
1. [Descripción General](#descripción-general)
2. [Estructura del Módulo](#estructura-del-módulo)
3. [Configuración Inicial](#configuración-inicial)
4. [Funcionalidades Principales](#funcionalidades-principales)
5. [Flujos de Proceso](#flujos-de-proceso)
6. [Panel de Control](#panel-de-control)
7. [Gestión de Vehículos](#gestión-de-vehículos)
8. [Gestión de Contratos](#gestión-de-contratos)
9. [Portal Web para Clientes](#portal-web-para-clientes)
10. [Mantenimiento y Reportes](#mantenimiento-y-reportes)

---

## Descripción General

El módulo **Vehicle Rental (Sunset)** es un sistema completo de gestión de alquiler de vehículos que permite:

- **Gestión completa de flota**: Vehículos, mantenimiento, disponibilidad
- **Proceso de alquiler**: Desde consulta hasta devolución
- **Portal web**: Para que los clientes realicen consultas y reservas
- **Facturación automática**: Generación de facturas y pagos
- **Dashboard**: Panel de control con métricas en tiempo real
- **Mantenimiento**: Programación y seguimiento de mantenimientos

---

## Estructura del Módulo

### Modelos Principales
- **Vehicle Contract**: Contratos de alquiler
- **Fleet Vehicle**: Vehículos de la flota (extendido)
- **Customer Documents**: Documentos del cliente
- **Cancellation Policy**: Políticas de cancelación
- **Insurance Policy**: Pólizas de seguro
- **Extra Service**: Servicios adicionales
- **Vehicle Payment Option**: Opciones de pago
- **Maintenance Schedule**: Horarios de mantenimiento
- **Rental Agreement Terms**: Términos del acuerdo
- **Vehicle Scratch Report**: Reportes de rayones

### Wizards (Asistentes)
- **Rental Contract Booking**: Reserva de contratos
- **Vehicle Damage**: Gestión de daños
- **Return Deposit**: Devolución de depósitos
- **Lead Rental Contract**: Conversión de leads a contratos
- **Maintenance Request Bill**: Facturación de mantenimiento

### Controladores Web
- **Vehicle Availability**: Disponibilidad de vehículos
- **Web Contract Booking**: Reservas desde web

---

## Configuración Inicial

### 1. Configuración de Vehículos
1. Ir a **Vehículos > Vehículos**
2. Crear/editar vehículos con:
   - **Precios de alquiler**: Por día, semana, mes, año, km, millas, hora
   - **Cargos extra**: Por exceso de tiempo/distancia
   - **Estado**: Disponible o en mantenimiento
   - **Horario de mantenimiento**: Asignar programa de mantenimiento

### 2. Configuración de Políticas
1. **Políticas de Cancelación**:
   - Ir a **Configuraciones > Políticas de Cancelación**
   - Crear políticas con términos y condiciones

2. **Términos de Acuerdo**:
   - Ir a **Configuraciones > Términos de Acuerdo de Alquiler**
   - Definir términos generales del alquiler

3. **Horarios de Mantenimiento**:
   - Ir a **Configuraciones > Horarios de Mantenimiento**
   - Configurar días de mantenimiento por vehículo

---

## Funcionalidades Principales

### 1. Panel de Control (Dashboard)
**Ubicación**: Menú principal > Panel

**Métricas disponibles**:
- Total de vehículos
- Vehículos disponibles
- Vehículos en mantenimiento
- Contratos en borrador
- Contratos en progreso
- Contratos devueltos
- Contratos cancelados
- Total de clientes
- Facturas de clientes
- Facturas pendientes

**Gráficos**:
- Duración de alquiler por contrato
- Facturación mensual
- Cronograma de contratos (Gantt)

### 2. Gestión de Disponibilidad
**Ubicación**: Menú principal > Disponibilidad

- Vista de calendario con disponibilidad de vehículos
- Filtros por fechas y vehículos
- Visualización de contratos activos

### 3. Consultas de Reserva
**Ubicación**: Menú principal > Consultas de Reserva

- Gestión de leads/consultas de clientes
- Conversión de consultas a contratos
- Seguimiento de oportunidades

---

## Flujos de Proceso

### FLUJO 1: Proceso de Alquiler Completo (Usuario Interno)

#### Paso 1: Crear Consulta/Lead
1. Ir a **Consultas de Reserva**
2. Crear nueva consulta con:
   - Datos del cliente
   - Vehículo deseado
   - Fechas de inicio y fin
   - Información de contacto

#### Paso 2: Convertir Lead a Contrato
1. Desde la consulta, usar el wizard **"Crear Contrato de Alquiler"**
2. Completar datos del contrato:
   - Cliente
   - Vehículo
   - Fechas
   - Tipo de alquiler (días, semanas, meses, etc.)
   - Precios y cargos adicionales

#### Paso 3: Configurar Contrato
1. **Datos del Cliente**:
   - Información de contacto
   - Documentos requeridos
   - Datos del conductor (si aplica)

2. **Configuración del Alquiler**:
   - Tipo de renta (hora, día, semana, mes, año, km, millas)
   - Cálculo automático de totales
   - Cargos extra por exceso
   - Depósito requerido

3. **Servicios Adicionales**:
   - Agregar productos/servicios extra
   - Configurar cantidades y precios

4. **Opciones de Pago**:
   - Configurar fechas de pago
   - Montos de pago
   - Crear facturas de pago

#### Paso 4: Confirmar Contrato
1. Revisar todos los datos
2. Cambiar estado a **"En Progreso"**
3. El vehículo automáticamente cambia a **"No Disponible"**

#### Paso 5: Gestión Durante el Alquiler
1. **Seguimiento**: El contrato aparece en el dashboard
2. **Facturación**: Generar facturas según opciones de pago
3. **Comunicación**: Envío automático de emails

#### Paso 6: Devolución del Vehículo
1. **Evaluación de Daños**:
   - Usar wizard **"Daños del Vehículo"**
   - Documentar cualquier daño
   - Calcular costos de reparación

2. **Devolución de Depósito**:
   - Usar wizard **"Devolución de Depósito"**
   - Calcular monto a devolver
   - Generar nota de crédito

3. **Finalizar Contrato**:
   - Cambiar estado a **"Devuelto"**
   - El vehículo vuelve a estar disponible

### FLUJO 2: Proceso de Alquiler (Cliente Web)

#### Paso 1: Consulta de Disponibilidad
1. Cliente accede al portal web
2. Navega a **"Consultas de Reserva"**
3. Completa formulario con:
   - Fechas de inicio y fin
   - Categoría de vehículo (opcional)
   - Número de asientos (opcional)

#### Paso 2: Selección de Vehículo
1. El sistema muestra vehículos disponibles
2. Cliente selecciona vehículo deseado
3. Completa datos de contacto

#### Paso 3: Envío de Consulta
1. Cliente envía la consulta
2. Se crea automáticamente un lead en el sistema
3. Cliente recibe confirmación

#### Paso 4: Seguimiento
1. Cliente puede ver sus consultas en el portal
2. Recibe notificaciones por email
3. Puede acceder a detalles de la consulta

### FLUJO 3: Gestión de Mantenimiento

#### Paso 1: Programación de Mantenimiento
1. Ir a **Vehículos > Vehículos**
2. Seleccionar vehículo
3. Asignar **Horario de Mantenimiento**
4. El sistema programa automáticamente el mantenimiento

#### Paso 2: Solicitud de Mantenimiento
1. Cuando es necesario, crear **Solicitud de Mantenimiento**
2. Especificar:
   - Tipo de mantenimiento
   - Partes necesarias
   - Servicios requeridos
   - Proveedor

#### Paso 3: Facturación de Mantenimiento
1. Usar wizard **"Factura de Solicitud de Mantenimiento"**
2. Seleccionar proveedor
3. Generar factura de proveedor automáticamente

---

## Panel de Control

### Dashboard Principal
**Acceso**: Menú principal > Panel

**Información mostrada**:
- **Métricas clave**: Vehículos, contratos, clientes, facturas
- **Gráfico de duración**: Contratos por período
- **Facturación mensual**: Ingresos por mes
- **Cronograma Gantt**: Vista temporal de contratos

### Filtros y Búsquedas
- Por fechas
- Por estado de contrato
- Por vehículo
- Por cliente

---

## Gestión de Vehículos

### Crear/Editar Vehículo
1. Ir a **Vehículos > Vehículos**
2. Configurar:
   - **Datos básicos**: Marca, modelo, año, matrícula
   - **Precios de alquiler**: Por diferentes períodos
   - **Cargos extra**: Por exceso de tiempo/distancia
   - **Estado**: Disponible/En mantenimiento
   - **Mantenimiento**: Asignar horario de mantenimiento

### Estados del Vehículo
- **Disponible**: Listo para alquiler
- **En Mantenimiento**: No disponible por mantenimiento

### Transiciones Automáticas
- Al crear contrato: Vehículo → No disponible
- Al finalizar contrato: Vehículo → Disponible
- Al programar mantenimiento: Vehículo → En mantenimiento

---

## Gestión de Contratos

### Estados del Contrato
1. **Borrador**: Contrato creado pero no confirmado
2. **En Progreso**: Contrato activo, vehículo alquilado
3. **Devuelto**: Vehículo devuelto, contrato finalizado
4. **Cancelado**: Contrato cancelado

### Campos Principales del Contrato

#### Información del Cliente
- Cliente principal
- Teléfono y email
- Documentos requeridos
- Conductor (si aplica)

#### Información del Vehículo
- Vehículo seleccionado
- Matrícula
- Odómetro inicial
- Año del modelo
- Tipo de combustible
- Transmisión

#### Configuración del Alquiler
- **Tipo de renta**: Hora, día, semana, mes, año, km, millas
- **Fechas**: Inicio y fin del alquiler
- **Cálculos automáticos**: Total de días, renta total
- **Cargos extra**: Por exceso de tiempo o distancia

#### Servicios Adicionales
- Productos/servicios extra
- Cantidades y precios
- Cálculo automático de totales

#### Opciones de Pago
- Fechas de pago programadas
- Montos de cada pago
- Generación automática de facturas

#### Seguros y Políticas
- Pólizas de seguro
- Políticas de cancelación
- Términos del acuerdo

### Wizards Disponibles

#### 1. Reserva de Contrato de Alquiler
- Seleccionar cliente
- Elegir fechas
- Mostrar vehículos disponibles
- Crear contrato automáticamente

#### 2. Daños del Vehículo
- Documentar daños encontrados
- Calcular costos de reparación
- Generar factura de daños

#### 3. Devolución de Depósito
- Calcular monto a devolver
- Generar nota de crédito
- Finalizar proceso de devolución

#### 4. Lead a Contrato
- Convertir consulta en contrato
- Transferir datos del lead
- Crear contrato completo

---

## Portal Web para Clientes

### Funcionalidades del Portal

#### 1. Consulta de Disponibilidad
**URL**: `/web/booking-enquiry`

**Proceso**:
1. Cliente ingresa fechas de alquiler
2. Opcionalmente filtra por categoría y asientos
3. Sistema muestra vehículos disponibles
4. Cliente puede seleccionar vehículo

#### 2. Envío de Consulta
**URL**: `/rental/booking-enquiry`

**Proceso**:
1. Cliente completa datos de contacto
2. Selecciona vehículo deseado
3. Envía consulta
4. Recibe confirmación

#### 3. Lista de Consultas
**URL**: `/rental/booking-enquiries`

**Funcionalidades**:
- Ver todas las consultas del cliente
- Búsqueda y filtrado
- Navegación entre consultas
- Acceso a detalles

#### 4. Detalle de Consulta
**URL**: `/rental/booking-inquiry/<token>`

**Información mostrada**:
- Datos de la consulta
- Vehículo seleccionado
- Estado de la consulta
- Navegación a consultas anteriores/siguientes

### Validaciones del Portal
- Fechas no pueden ser anteriores a hoy
- Fecha fin debe ser posterior a fecha inicio
- Campos obligatorios validados
- Solo vehículos disponibles mostrados

---

## Mantenimiento y Reportes

### Gestión de Mantenimiento

#### 1. Horarios de Mantenimiento
**Ubicación**: Configuraciones > Horarios de Mantenimiento

**Configuración**:
- Nombre del horario
- Días de mantenimiento
- Aplicar a vehículos específicos

#### 2. Solicitudes de Mantenimiento
**Ubicación**: Menú principal > Solicitudes de Mantenimiento

**Funcionalidades**:
- Crear solicitudes de mantenimiento
- Asignar proveedores
- Gestionar partes y servicios
- Facturar mantenimiento

#### 3. Facturación de Mantenimiento
**Wizard**: "Factura de Solicitud de Mantenimiento"

**Proceso**:
1. Seleccionar solicitud de mantenimiento
2. Elegir proveedor
3. Generar factura automáticamente
4. Incluir partes y servicios

### Reportes Disponibles

#### 1. Informes de Rayones
**Ubicación**: Configuraciones > Informes de Rayones

**Funcionalidades**:
- Documentar rayones en vehículos
- Adjuntar imágenes
- Generar reportes

#### 2. Reportes de Contratos
**Ubicación**: Contratos > Reportes

**Tipos de reportes**:
- Contratos por período
- Ingresos por vehículo
- Análisis de rentabilidad
- Estados de contratos

### Automatizaciones

#### 1. Cronogramas Automáticos
- Programación de mantenimiento
- Notificaciones de vencimiento
- Actualización de estados

#### 2. Emails Automáticos
- Confirmación de contratos
- Recordatorios de devolución
- Notificaciones de mantenimiento

---

## Configuraciones Avanzadas

### 1. Secuencias
- Numeración automática de contratos
- Referencias únicas
- Configuración por empresa

### 2. Plantillas de Email
- Confirmación de contratos
- Recordatorios
- Notificaciones de estado

### 3. Formatos de Reporte
- Configuración de papel
- Encabezados y pies
- Logos y branding

### 4. Permisos de Acceso
- Roles de usuario
- Permisos por modelo
- Acceso al portal web

---

## Flujo Completo de Ejemplo

### Escenario: Alquiler de Furgoneta por 3 días

#### 1. Cliente Web (Consulta)
1. Cliente accede al portal
2. Busca furgonetas disponibles del 15 al 18 de enero
3. Selecciona furgoneta "Ford Transit"
4. Completa datos de contacto
5. Envía consulta

#### 2. Usuario Interno (Procesamiento)
1. Recibe notificación de nueva consulta
2. Revisa datos del cliente
3. Usa wizard "Crear Contrato de Alquiler"
4. Configura contrato:
   - Cliente: Juan Pérez
   - Vehículo: Ford Transit
   - Fechas: 15-18 enero
   - Tipo: 3 días
   - Precio: €50/día = €150
   - Depósito: €200
5. Confirma contrato (estado: En Progreso)

#### 3. Durante el Alquiler
1. Sistema genera factura automáticamente
2. Cliente recibe email de confirmación
3. Vehículo cambia a "No Disponible"
4. Dashboard muestra contrato activo

#### 4. Devolución
1. Cliente devuelve vehículo
2. Usuario evalúa estado:
   - Sin daños: Devolución completa del depósito
   - Con daños: Usar wizard "Daños del Vehículo"
3. Usar wizard "Devolución de Depósito"
4. Generar nota de crédito
5. Cambiar estado a "Devuelto"
6. Vehículo vuelve a "Disponible"

---

## Consejos de Uso

### Para Usuarios Internos
1. **Configurar precios**: Establecer precios claros por tipo de alquiler
2. **Documentar daños**: Siempre documentar estado del vehículo
3. **Seguir flujo**: No saltarse pasos en el proceso
4. **Comunicar**: Mantener comunicación con clientes
5. **Mantenimiento**: Programar mantenimientos regulares

### Para Clientes Web
1. **Fechas precisas**: Ingresar fechas exactas de alquiler
2. **Datos completos**: Proporcionar información de contacto válida
3. **Seguimiento**: Revisar estado de consultas regularmente
4. **Comunicación**: Responder a consultas del personal

### Mejores Prácticas
1. **Backup regular**: Respaldo de datos importantes
2. **Actualizaciones**: Mantener sistema actualizado
3. **Capacitación**: Entrenar usuarios en el sistema
4. **Documentación**: Mantener documentación actualizada
5. **Monitoreo**: Revisar métricas del dashboard regularmente

---

## Solución de Problemas Comunes

### 1. Vehículo no aparece como disponible
- Verificar estado del vehículo
- Revisar contratos activos
- Comprobar fechas de mantenimiento

### 2. Error en cálculo de precios
- Verificar configuración de precios del vehículo
- Revisar tipo de alquiler seleccionado
- Comprobar cargos adicionales

### 3. Problemas con facturación
- Verificar datos del cliente
- Revisar productos configurados
- Comprobar permisos de facturación

### 4. Portal web no funciona
- Verificar configuración de website
- Comprobar permisos de acceso
- Revisar plantillas web

---

## Contacto y Soporte

Para soporte técnico o consultas sobre el módulo:
- **Desarrollador**: Cositt
- **Website**: https://cositt.com
- **Licencia**: OPL-1
- **Versión**: 2.7

---

*Este manual cubre todas las funcionalidades del módulo Vehicle Rental (Sunset) v2.7. Para actualizaciones o nuevas funcionalidades, consulte la documentación oficial del módulo.*
