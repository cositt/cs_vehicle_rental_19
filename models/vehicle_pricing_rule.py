# -*- coding: utf-8 -*-
# Copyright 2025
# Sistema de Tarifas Avanzado para Vehicle Rental

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VehiclePricingRule(models.Model):
    """Regla de Tarificación por Categoría de Vehículo"""
    _name = 'vehicle.pricing.rule'
    _description = 'Regla de Tarificación de Vehículos'
    _order = 'vehicle_category_id, pricing_type, km_range, duration_range'
    _rec_name = 'name'

    # ============================================
    # IDENTIFICACIÓN
    # ============================================
    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True,
        readonly=True
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Desactivar para ocultar tarifas obsoletas sin eliminarlas'
    )

    # ============================================
    # CATEGORÍA DEL VEHÍCULO Y PRODUCTO
    # ============================================
    vehicle_category_id = fields.Many2one(
        'fleet.vehicle.model.category',
        string='Categoría de Vehículo',
        required=True,
        ondelete='restrict',
        help='Tipo de vehículo al que aplica esta tarifa (Tipo A, C, F, etc.)'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto Asociado',
        compute='_compute_product_id',
        store=True,
        help='Producto que se usará en la factura. Se asigna automáticamente según la categoría.'
    )

    # ============================================
    # TIPO DE TARIFA
    # ============================================
    pricing_type = fields.Selection([
        ('standard', 'Tarifa Estándar'),
        ('flexirent', 'Flexirent - Larga Temporada'),
    ], string='Tipo de Tarifa',
        required=True,
        default='standard',
        help='Estándar: tarifas por días/km. Flexirent: paquetes de 30 días'
    )

    # ============================================
    # CONFIGURACIÓN TARIFAS ESTÁNDAR
    # ============================================
    km_range = fields.Selection([
        ('100', '100 Km'),
        ('350', '350 Km'),
        ('500', '500 Km'),
        ('650', '650 Km'),
        ('850', '850 Km'),
        ('unlimited', 'Sin límite'),
    ], string='Rango de Kilometraje',
        help='Límite de kilómetros incluidos en la tarifa estándar'
    )

    duration_range = fields.Selection([
        ('4h', '4h (mañana o tarde)'),
        ('1-2d', '1-2 días'),
        ('3-5d', '3-5 días'),
        ('6-10d', '6-10 días'),
        ('11-20d', '11-20 días'),
        ('21-29d', '21-29 días'),
    ], string='Rango de Duración',
        help='Duración del alquiler para aplicar esta tarifa'
    )

    # ============================================
    # CAMPOS ADICIONALES PARA LA VISTA
    # ============================================
    km_included = fields.Integer(
        string='Km Incluidos',
        help='Kilómetros incluidos en esta tarifa'
    )
    
    package_days = fields.Integer(
        string='Días Paquete',
        help='Días incluidos en el paquete'
    )
    
    km_limit = fields.Char(
        string='Km Límite',
        help='Límite de kilómetros (texto para mostrar)'
    )

    # ============================================
    # CONFIGURACIÓN FLEXIRENT
    # ============================================
    flexirent_km_total = fields.Integer(
        string='Kilometraje Total Incluido',
        help='Total de kilómetros incluidos en el paquete FLEXIRENT de 30 días'
    )
    
    flexirent_duration_days = fields.Integer(
        string='Duración (días)',
        default=30,
        help='Duración del paquete FLEXIRENT (normalmente 30 días)'
    )
    
    extra_km_price = fields.Monetary(
        string='Precio por Km Extra',
        default=0.21,
        currency_field='currency_id',
        help='Precio por kilómetro adicional cuando se excede el límite. Configurable manualmente.'
    )

    # ============================================
    # PRECIOS (CON IVA INCLUIDO)
    # ============================================
    price_per_unit = fields.Monetary(
        string='Precio (IVA incluido)',
        required=True,
        currency_field='currency_id',
        help='Precio por día (estándar) o precio total del paquete (flexirent). IVA incluido.'
    )

    price_without_vat = fields.Monetary(
        string='Precio (sin IVA)',
        compute='_compute_price_without_vat',
        store=True,
        currency_field='currency_id',
        help='Precio calculado sin IVA (21%). Editable en importación.'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ============================================
    # VIGENCIA TEMPORAL
    # ============================================
    valid_from = fields.Date(
        string='Válido Desde',
        default=fields.Date.today,
        required=True,
        help='Fecha desde la cual esta tarifa está activa'
    )

    valid_until = fields.Date(
        string='Válido Hasta',
        help='Fecha hasta la cual esta tarifa es válida. Dejar vacío para validez indefinida.'
    )

    # ============================================
    # INFORMACIÓN ADICIONAL
    # ============================================
    notes = fields.Text(
        string='Notas',
        help='Condiciones especiales, restricciones, etc.'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )

    # ============================================
    # MÉTODOS COMPUTADOS
    # ============================================

    @api.depends('price_per_unit')
    def _compute_price_without_vat(self):
        """Calcula el precio sin IVA (dividiendo entre 1.21)"""
        for record in self:
            if record.price_per_unit:
                record.price_without_vat = record.price_per_unit / 1.21
            else:
                record.price_without_vat = 0.0
    
    @api.depends('vehicle_category_id')
    def _compute_product_id(self):
        """Asigna el producto según la categoría del vehículo"""
        for record in self:
            if record.vehicle_category_id:
                # Buscar producto asociado a esta categoría
                # El producto debe tener el mismo nombre o un external_id específico
                product = self.env['product.product'].search([
                    ('name', 'ilike', record.vehicle_category_id.name),
                    ('type', '=', 'service'),
                    ('categ_id.name', '=', 'Vehicle')
                ], limit=1)
                
                if not product:
                    # Si no existe, intentar buscar por external_id (product.template)
                    category_code = record.vehicle_category_id.name.split()[0].lower()  # "Tipo A" -> "tipo"
                    ext_id = f'vehicle_rental.product_rental_{category_code}'
                    try:
                        product_template = self.env.ref(ext_id, raise_if_not_found=False)
                        # Obtener product.product (variante) desde product.template
                        if product_template and product_template.product_variant_ids:
                            product = product_template.product_variant_ids[0]
                        else:
                            product = False
                    except:
                        product = False
                
                record.product_id = product.id if product else False
            else:
                record.product_id = False

    @api.depends('vehicle_category_id', 'pricing_type', 'km_range', 'duration_range',
                 'flexirent_km_total', 'flexirent_duration_days')
    def _compute_name(self):
        """Genera nombre descriptivo automáticamente"""
        for record in self:
            if record.pricing_type == 'standard':
                km_label = dict(record._fields['km_range'].selection).get(record.km_range, '')
                duration_label = dict(record._fields['duration_range'].selection).get(record.duration_range, '')
                record.name = f"{record.vehicle_category_id.name or 'Sin categoría'} - {km_label} - {duration_label}"
            
            elif record.pricing_type == 'flexirent':
                record.name = (f"{record.vehicle_category_id.name or 'Sin categoría'} - "
                              f"FLEXIRENT {record.flexirent_km_total}km / {record.flexirent_duration_days} días")
            else:
                record.name = f"{record.vehicle_category_id.name or 'Sin categoría'} - {record.pricing_type}"

    # ============================================
    # VALIDACIONES
    # ============================================

    @api.constrains('valid_from', 'valid_until')
    def _check_validity_dates(self):
        """Valida que la fecha de fin sea posterior a la de inicio"""
        for record in self:
            if record.valid_until and record.valid_from:
                if record.valid_until < record.valid_from:
                    raise ValidationError(
                        _('La fecha "Válido Hasta" debe ser posterior a "Válido Desde".')
                    )

    @api.constrains('pricing_type', 'km_range', 'duration_range', 'flexirent_km_total')
    def _check_pricing_configuration(self):
        """Valida que los campos necesarios estén configurados según el tipo de tarifa"""
        for record in self:
            if record.pricing_type == 'standard':
                if not record.km_range or not record.duration_range:
                    raise ValidationError(
                        _('Las tarifas estándar requieren especificar Rango de Kilometraje y Duración.')
                    )
            elif record.pricing_type == 'flexirent':
                if not record.flexirent_km_total:
                    raise ValidationError(
                        _('Las tarifas FLEXIRENT requieren especificar el Kilometraje Total Incluido.')
                    )

    @api.constrains('price_per_unit')
    def _check_price_positive(self):
        """Valida que el precio sea positivo"""
        for record in self:
            if record.price_per_unit <= 0:
                raise ValidationError(
                    _('El precio debe ser mayor que cero.')
                )

    # Constraint SQL para evitar tarifas duplicadas
    _sql_constraints = [
        ('unique_standard_pricing',
         'UNIQUE(vehicle_category_id, pricing_type, km_range, duration_range, valid_from, company_id)',
         'Ya existe una tarifa con esta combinación de parámetros para la misma fecha.'),
        
        ('unique_flexirent_pricing',
         'UNIQUE(vehicle_category_id, pricing_type, flexirent_km_total, flexirent_duration_days, valid_from, company_id)',
         'Ya existe una tarifa FLEXIRENT con estos parámetros para la misma fecha.'),
    ]

    # ============================================
    # MÉTODOS DE BÚSQUEDA
    # ============================================

    def find_pricing_rule(self, category_id, total_km, total_days, rental_date=None, pricing_type='standard'):
        """
        Busca la tarifa aplicable para una combinación de parámetros
        
        Args:
            category_id: ID de la categoría del vehículo
            total_km: Kilómetros totales del alquiler
            total_days: Días totales del alquiler
            rental_date: Fecha del alquiler (por defecto hoy)
            pricing_type: Tipo de tarifa ('standard' o 'flexirent')
        
        Returns:
            Registro de vehicle.pricing.rule o False
        """
        if not rental_date:
            rental_date = fields.Date.today()

        if pricing_type == 'flexirent':
            # Para FLEXIRENT, buscar por duración y km incluidos
            domain = [
                ('vehicle_category_id', '=', category_id),
                ('pricing_type', '=', 'flexirent'),
                ('flexirent_duration_days', '<=', total_days),
                ('flexirent_km_total', '>=', total_km),
                ('valid_from', '<=', rental_date),
                '|', ('valid_until', '=', False), ('valid_until', '>=', rental_date),
                ('active', '=', True),
            ]
            # Ordenar por duración descendente para obtener el paquete más largo que se ajuste
            return self.search(domain, limit=1, order='flexirent_duration_days desc')
        else:
            # Para tarifa estándar, usar la lógica original
            # Determinar el rango de kilometraje
            km_range = self._get_km_range_from_total(total_km)
            
            # Determinar el rango de duración
            duration_range = self._get_duration_range_from_days(total_days)

            # Buscar la tarifa
            domain = [
                ('vehicle_category_id', '=', category_id),
                ('pricing_type', '=', 'standard'),
                ('km_range', '=', km_range),
                ('duration_range', '=', duration_range),
                ('valid_from', '<=', rental_date),
                '|', ('valid_until', '=', False), ('valid_until', '>=', rental_date),
                ('active', '=', True),
            ]

            return self.search(domain, limit=1, order='valid_from desc')

    def _get_km_range_from_total(self, total_km):
        """Determina el rango de kilometraje según el total"""
        if total_km <= 100:
            return '100'
        elif total_km <= 350:
            return '350'
        elif total_km <= 500:
            return '500'
        elif total_km <= 650:
            return '650'
        elif total_km <= 850:
            return '850'
        else:
            return 'unlimited'

    def _get_duration_range_from_days(self, total_days):
        """Determina el rango de duración según los días totales"""
        if total_days <= 0.5:  # 4 horas = 0.5 días
            return '4h'
        elif total_days <= 2:
            return '1_2'
        elif total_days <= 5:
            return '3_5'
        elif total_days <= 10:
            return '6_10'
        elif total_days <= 20:
            return '11_20'
        elif total_days <= 29:
            return '21_29'
        else:
            # Para más de 29 días, considerar FLEXIRENT
            return '21_29'  # O retornar None para forzar FLEXIRENT

    # ============================================
    # MÉTODOS DE ACCIÓN
    # ============================================

    def action_duplicate_with_new_dates(self):
        """Acción para duplicar tarifa con nuevas fechas de vigencia"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Duplicar Tarifa'),
            'res_model': 'vehicle.pricing.rule',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicle_category_id': self.vehicle_category_id.id,
                'default_pricing_type': self.pricing_type,
                'default_km_range': self.km_range,
                'default_duration_range': self.duration_range,
                'default_flexirent_km_total': self.flexirent_km_total,
                'default_flexirent_duration_days': self.flexirent_duration_days,
                'default_extra_km_price': self.extra_km_price,
                'default_price_per_unit': self.price_per_unit,
            }
        }

