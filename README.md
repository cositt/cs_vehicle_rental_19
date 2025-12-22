# 🚗 Vehicle Rental (Sunset) - Módulo de Alquiler de Vehículos

<div align="center">
  <img src="https://cositt.com/wp-content/uploads/2020/11/Logo-Cositt-01-original.png" alt="Cositt Logo" width="200"/>
</div>

## 📋 Descripción

**Vehicle Rental (Sunset)** es un módulo completo de gestión de alquiler de vehículos para Odoo 18.0 Enterprise que permite gestionar flotas de vehículos, contratos de alquiler, clientes, facturación y mantenimiento de forma integral.

## ✨ Características Principales

### 🎯 **Gestión de Flota**
- **Gestión completa de vehículos**: Información detallada, estados, mantenimiento
- **Disponibilidad en tiempo real**: Vista de calendario con disponibilidad de vehículos
- **Estados de vehículos**: Disponible, En mantenimiento, Alquilado
- **Seguimiento de odómetro**: Control de kilometraje y uso

### 📊 **Dashboard Inteligente**
- **Métricas en tiempo real**: Vehículos totales, disponibles, en mantenimiento
- **Estados de contratos**: Borrador, En progreso, Devueltos, Cancelados
- **Gráficos interactivos**: Duración de alquiler, facturación mensual
- **Cronograma Gantt**: Vista temporal de contratos

### 💼 **Gestión de Contratos**
- **Proceso completo**: Desde consulta hasta devolución
- **Múltiples tipos de alquiler**: Por hora, día, semana, mes, año, km, millas
- **Cálculos automáticos**: Totales, cargos extra, impuestos
- **Opciones de pago**: Pago completo, diario, semanal, mensual, trimestral, anual

### 🌐 **Portal Web para Clientes**
- **Consulta de disponibilidad**: Búsqueda por fechas y categorías
- **Reserva online**: Proceso de reserva completo
- **Seguimiento de consultas**: Portal del cliente
- **Notificaciones por email**: Confirmaciones automáticas

### 🔧 **Mantenimiento y Reportes**
- **Programación de mantenimiento**: Horarios automáticos
- **Solicitudes de mantenimiento**: Gestión de reparaciones
- **Reportes de daños**: Documentación de rayones y daños
- **Facturación de mantenimiento**: Integración con proveedores

## 🚀 Instalación

### Requisitos
- **Odoo 18.0 Enterprise**
- **Python 3.8+**
- **PostgreSQL 12+**

### Pasos de Instalación

1. **Clonar el repositorio:**
```bash
git clone git@github.com:cositt/cs_vehicle_rental.git
```

2. **Copiar al directorio de addons de Odoo:**
```bash
cp -r cs_vehicle_rental/vehicle_rental /path/to/odoo/addons/
```

3. **Actualizar lista de módulos:**
```bash
# En Odoo: Apps > Update Apps List
```

4. **Instalar el módulo:**
```bash
# En Odoo: Apps > Buscar "Vehicle Rental" > Install
```

## 📖 Configuración Inicial

### 1. **Configuración de Vehículos**
1. Ir a **Vehículos > Vehículos**
2. Crear/editar vehículos con:
   - **Precios de alquiler**: Por diferentes períodos
   - **Cargos extra**: Por exceso de tiempo/distancia
   - **Estado**: Disponible/En mantenimiento
   - **Horario de mantenimiento**: Asignar programa

### 2. **Configuración de Políticas**
1. **Políticas de Cancelación**: Términos y condiciones
2. **Términos de Acuerdo**: Condiciones generales del alquiler
3. **Horarios de Mantenimiento**: Días de mantenimiento por vehículo

### 3. **Configuración de Productos**
- **Productos de alquiler**: Crear productos para diferentes tipos de vehículos
- **Servicios adicionales**: Productos para servicios extra
- **Depósitos**: Productos para depósitos de seguridad

## 🎯 Flujos de Trabajo

### **FLUJO 1: Proceso de Alquiler (Usuario Interno)**

#### Paso 1: Crear Contrato
1. Ir a **Contratos > Crear**
2. Seleccionar cliente y vehículo
3. Configurar fechas y términos
4. Establecer precios y cargos

#### Paso 2: Confirmar Contrato
1. Cambiar estado a "En Progreso"
2. Generar facturas automáticamente
3. Enviar confirmación al cliente

#### Paso 3: Gestión del Alquiler
1. **Seguimiento**: Estado del vehículo y contrato
2. **Comunicación**: Notificaciones automáticas
3. **Modificaciones**: Cambios en fechas o servicios

#### Paso 4: Devolución
1. **Inspección**: Verificar estado del vehículo
2. **Cálculo de cargos**: Daños, excesos, etc.
3. **Facturación final**: Cargos adicionales
4. **Devolución de depósito**: Si aplica

### **FLUJO 2: Consulta Web (Cliente)**

#### Paso 1: Consulta de Disponibilidad
1. Acceder al portal web
2. Introducir fechas de alquiler
3. Filtrar por categoría y asientos
4. Ver vehículos disponibles

#### Paso 2: Selección de Vehículo
1. Elegir vehículo deseado
2. Completar datos de contacto
3. Enviar consulta

#### Paso 3: Seguimiento
1. Recibir confirmación por email
2. Acceder al portal del cliente
3. Ver estado de la consulta

## 🛠️ Funcionalidades Técnicas

### **Modelos Principales**
- **Vehicle Contract**: Contratos de alquiler
- **Fleet Vehicle**: Vehículos (extendido)
- **Customer Documents**: Documentos del cliente
- **Cancellation Policy**: Políticas de cancelación
- **Insurance Policy**: Pólizas de seguro
- **Extra Service**: Servicios adicionales
- **Vehicle Payment Option**: Opciones de pago
- **Maintenance Schedule**: Horarios de mantenimiento

### **Wizards (Asistentes)**
- **Rental Contract Booking**: Reserva de contratos
- **Vehicle Damage**: Gestión de daños
- **Return Deposit**: Devolución de depósitos
- **Lead Rental Contract**: Conversión de leads
- **Maintenance Request Bill**: Facturación de mantenimiento

### **Controladores Web**
- **Vehicle Availability**: Disponibilidad de vehículos
- **Web Contract Booking**: Reservas desde web

## 🌍 Traducciones

El módulo incluye traducciones completas en:
- **Español (es)**: Traducción principal
- **Francés (fr)**: Traducción completa
- **Italiano (it)**: Traducción completa
- **Árabe (ar_001)**: Traducción completa

## 📊 Dashboard y Reportes

### **Métricas Disponibles**
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

### **Gráficos Interactivos**
- **Duración de alquiler**: Por contrato
- **Facturación mensual**: Ingresos por mes
- **Cronograma Gantt**: Vista temporal de contratos

## 🔧 Mantenimiento

### **Gestión de Mantenimiento**
1. **Horarios de Mantenimiento**: Configurar días de mantenimiento
2. **Solicitudes**: Crear solicitudes de mantenimiento
3. **Facturación**: Generar facturas de proveedores
4. **Seguimiento**: Estado de reparaciones

### **Reportes de Daños**
- **Documentación**: Fotos y descripción de daños
- **Cálculo de costos**: Estimación de reparaciones
- **Facturación**: Cargos por daños al cliente

## 🚨 Solución de Problemas

### **Problemas Comunes**

#### **Error: "Campos no válidos: Recoger ciudad, Ciudad de entrega"**
- **Causa**: Contratos creados sin completar ciudades de recogida y entrega
- **Solución**: Editar contrato en estado "Borrador" y completar campos obligatorios

#### **Error: "No se pueden crear cuotas"**
- **Causa**: Campos obligatorios vacíos en contrato
- **Solución**: Completar todos los campos requeridos antes de cambiar estado

#### **Problema: Traducciones no se aplican**
- **Causa**: Caché de traducciones de Odoo
- **Solución**: Limpiar caché y reiniciar servidor

## 📞 Soporte

### **Documentación**
- **Manual de Uso**: `static/description/MANUAL_USO.md`
- **Guía de Instalación**: Este README
- **Ejemplos de Uso**: Documentación en código

### **Contacto**
- **Repositorio**: [GitHub - cs_vehicle_rental](https://github.com/cositt/cs_vehicle_rental)
- **Issues**: Usar sistema de issues de GitHub
- **Documentación**: Consultar manual de uso incluido

## 📄 Licencia

Este módulo está licenciado bajo **OPL-1** (Odoo Public License v1.0).

## 🏷️ Versión

- **Versión**: 1.0.0
- **Compatibilidad**: Odoo 18.0 Enterprise
- **Última actualización**: Octubre 2025

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crear una rama para la funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Commit los cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear un Pull Request

## 📝 Changelog

### **v1.0.0** (Octubre 2025)
- ✅ Módulo inicial completo
- ✅ Traducciones en español
- ✅ Dashboard interactivo
- ✅ Portal web para clientes
- ✅ Gestión completa de contratos
- ✅ Sistema de mantenimiento
- ✅ Reportes y facturación

---

<div align="center">
  <img src="https://cositt.com/wp-content/uploads/2020/11/Logo-Cositt-01-original.png" alt="Cositt Logo" width="150"/>
  
  **Desarrollado por [Cositt](https://cositt.com)** - Soluciones empresariales con Odoo
</div>
