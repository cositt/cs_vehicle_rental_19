# -*- coding: utf-8 -*-
# Copyright 2025
# Sistema de Tarifas de Seguros para Vehicle Rental

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VehicleInsurancePricing(models.Model):
    """Tarificación de Seguros de Vehículos"""
    _name = 'vehicle.insurance.pricing'
    _description = 'Tarifas de Seguros de Vehículos'
    _order = 'insurance_type, duration_range, driver_type'
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
        default=True
    )

    # ============================================
    # TIPO DE SEGURO Y PRODUCTO
    # ============================================
    insurance_type = fields.Selection([
        ('basic', 'Seguro Básico - Franquicia 300€'),
        ('no_franchise', 'Seguro Sin Franquicia'),
    ], string='Tipo de Seguro',
        required=True,
        default='basic',
        help='Básico: franquicia de 300€. Sin Franquicia: cobertura total'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto Asociado',
        compute='_compute_product_id',
        store=True,
        help='Producto que se usará en la factura. Se asigna automáticamente según el tipo de seguro.'
    )

    # ============================================
    # DURACIÓN DEL ALQUILER
    # ============================================
    duration_range = fields.Selection([
        ('1_3', '1-3 días'),
        ('4_7', '4-7 días'),
        ('8_15', '8-15 días'),
        ('16_30', '16-30 días'),
        ('31_60', '31-60 días'),
        ('61_180', '61-180 días'),
        ('181_365', '181-365 días'),
    ], string='Rango de Duración',
        required=True,
        help='Rango de días del alquiler para aplicar esta tarifa'
    )

    # ============================================
    # TIPO DE CONDUCTOR
    # ============================================
    driver_type = fields.Selection([
        ('normal', 'Conductor Normal'),
        ('special', 'Conductor Especial (<25 o >60 años)'),
    ], string='Tipo de Conductor',
        required=True,
        default='normal',
        help='Conductores especiales pagan tarifa más alta'
    )

    # ============================================
    # PRECIOS (CON IVA INCLUIDO)
    # ============================================
    price_per_day = fields.Monetary(
        string='Precio por Día (IVA incluido)',
        required=True,
        currency_field='currency_id',
        help='Precio del seguro por día de alquiler. IVA incluido.'
    )

    price_without_vat = fields.Monetary(
        string='Precio por Día (sin IVA)',
        compute='_compute_price_without_vat',
        store=True,
        currency_field='currency_id',
        help='Precio calculado sin IVA (21%)'
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
        required=True
    )

    valid_until = fields.Date(
        string='Válido Hasta',
        help='Dejar vacío para validez indefinida'
    )

    # ============================================
    # INFORMACIÓN ADICIONAL
    # ============================================
    notes = fields.Text(
        string='Notas',
        help='Condiciones especiales, coberturas incluidas, etc.'
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

    @api.depends('price_per_day')
    def _compute_price_without_vat(self):
        """Calcula el precio sin IVA (dividiendo entre 1.21)"""
        for record in self:
            if record.price_per_day:
                record.price_without_vat = record.price_per_day / 1.21
            else:
                record.price_without_vat = 0.0
    
    @api.depends('insurance_type', 'duration_range')
    def _compute_product_id(self):
        """Asigna el producto según el tipo de seguro y duración de forma dinámica"""
        for record in self:
            if not record.insurance_type or not record.duration_range:
                record.product_id = False
                continue
            
            # Construir el nombre del producto basado en tipo y duración
            insurance_label = dict(record._fields['insurance_type'].selection).get(record.insurance_type, '')
            duration_label = dict(record._fields['duration_range'].selection).get(record.duration_range, '')
            
            # Buscar producto por nombre similar
            # Ej: "Seguro Básico - Franquicia 300€ - 1-3 días"
            search_name = f"{insurance_label} - {duration_label}"
            
            product = self.env['product.product'].search([
                ('name', 'ilike', search_name),
                ('type', '=', 'service'),
                ('categ_id.name', '=', 'Insurance')
            ], limit=1)
            
            # Si no se encuentra por nombre completo, buscar por external_id
            if not product:
                # Generar external_id esperado
                # Ej: product_insurance_basic_1_3, product_insurance_no_franchise_4_7
                insurance_code = 'basic' if record.insurance_type == 'basic' else 'no_franchise'
                duration_code = record.duration_range.replace('-', '_')
                ext_id = f'vehicle_rental.product_insurance_{insurance_code}_{duration_code}'
                
                try:
                    product_template = self.env.ref(ext_id, raise_if_not_found=False)
                    if product_template and hasattr(product_template, 'product_variant_ids'):
                        product = product_template.product_variant_ids[0] if product_template.product_variant_ids else False
                    else:
                        product = False
                except:
                    product = False
            
            # Si aún no hay producto, intentar con el producto genérico por tipo
            if not product:
                if record.insurance_type == 'basic':
                    product = self.env.ref('vehicle_rental.product_insurance_basic', raise_if_not_found=False)
                elif record.insurance_type == 'no_franchise':
                    product = self.env.ref('vehicle_rental.product_insurance_no_franchise', raise_if_not_found=False)
            
            record.product_id = product.id if product else False

    @api.depends('insurance_type', 'duration_range', 'driver_type')
    def _compute_name(self):
        """Genera nombre descriptivo automáticamente"""
        for record in self:
            insurance_label = dict(record._fields['insurance_type'].selection).get(record.insurance_type, '')
            duration_label = dict(record._fields['duration_range'].selection).get(record.duration_range, '')
            driver_label = dict(record._fields['driver_type'].selection).get(record.driver_type, '')
            
            record.name = f"{insurance_label} - {duration_label} - {driver_label}"

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

    @api.constrains('price_per_day')
    def _check_price_positive(self):
        """Valida que el precio sea positivo"""
        for record in self:
            if record.price_per_day <= 0:
                raise ValidationError(
                    _('El precio debe ser mayor que cero.')
                )

    # Constraint SQL para evitar duplicados
    _sql_constraints = [
        ('unique_insurance_pricing',
         'UNIQUE(insurance_type, duration_range, driver_type, valid_from, company_id)',
         'Ya existe una tarifa de seguro con esta combinación de parámetros para la misma fecha.'),
    ]

    # ============================================
    # MÉTODOS DE BÚSQUEDA
    # ============================================

    def find_insurance_price(self, insurance_type, total_days, is_special_driver, rental_date=None):
        """
        Busca el precio de seguro aplicable
        
        Args:
            insurance_type: 'basic' o 'no_franchise'
            total_days: Días totales del alquiler
            is_special_driver: True si conductor <25 o >60 años
            rental_date: Fecha del alquiler (por defecto hoy)
        
        Returns:
            Precio por día o False
        """
        if not rental_date:
            rental_date = fields.Date.today()

        # Determinar el rango de duración
        duration_range = self._get_duration_range_from_days(total_days)
        
        # Determinar tipo de conductor
        driver_type = 'special' if is_special_driver else 'normal'

        # Buscar la tarifa
        domain = [
            ('insurance_type', '=', insurance_type),
            ('duration_range', '=', duration_range),
            ('driver_type', '=', driver_type),
            ('valid_from', '<=', rental_date),
            '|', ('valid_until', '=', False), ('valid_until', '>=', rental_date),
            ('active', '=', True),
        ]

        pricing = self.search(domain, limit=1, order='valid_from desc')
        return pricing.price_per_day if pricing else False

    def _get_duration_range_from_days(self, total_days):
        """Determina el rango de duración según los días totales"""
        if total_days <= 3:
            return '1_3'
        elif total_days <= 7:
            return '4_7'
        elif total_days <= 15:
            return '8_15'
        elif total_days <= 30:
            return '16_30'
        elif total_days <= 60:
            return '31_60'
        elif total_days <= 180:
            return '61_180'
        else:
            return '181_365'

    # ============================================
    # MÉTODOS DE ACCIÓN
    # ============================================

    def action_duplicate_with_new_dates(self):
        """Acción para duplicar tarifa con nuevas fechas de vigencia"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Duplicar Tarifa de Seguro'),
            'res_model': 'vehicle.insurance.pricing',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_insurance_type': self.insurance_type,
                'default_duration_range': self.duration_range,
                'default_driver_type': self.driver_type,
                'default_price_per_day': self.price_per_day,
            }
        }

