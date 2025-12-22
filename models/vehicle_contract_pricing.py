# -*- coding: utf-8 -*-
# Copyright 2025
# Extensión de Vehicle Contract para Sistema de Pricing Automático

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VehicleContractPricing(models.Model):
    """Extensión de Vehicle Contract con cálculo automático de precios"""
    _inherit = 'vehicle.contract'

    # ============================================
    # CÁLCULO AUTOMÁTICO DE PRECIOS
    # ============================================
    
    calculated_rent = fields.Monetary(
        string='Precio Calculado (Vehículo)',
        compute='_compute_rent_from_pricing_rules',
        store=True,
        currency_field='currency_id',
        help='Precio calculado automáticamente según categoría del vehículo, km y duración'
    )
    
    calculated_rent_without_vat = fields.Monetary(
        string='Precio Calculado (sin IVA)',
        compute='_compute_calculated_rent_without_vat',
        store=True,
        currency_field='currency_id'
    )
    
    price_manually_modified = fields.Boolean(
        string='Precio Modificado Manualmente',
        compute='_check_price_modified',
        store=True,
        help='Indica si el precio fue modificado manualmente respecto al calculado'
    )
    
    discount_reason = fields.Text(
        string='Motivo del Descuento/Modificación',
        help='Explicar por qué se modificó el precio (ej: Cliente VIP, Promoción, etc.)'
    )
    
    applied_pricing_rule_id = fields.Many2one(
        'vehicle.pricing.rule',
        string='Tarifa Aplicada',
        compute='_compute_applied_pricing_rule',
        store=True,
        help='Referencia a la tarifa que se aplicó automáticamente'
    )
    
    # ============================================
    # PRODUCTOS PARA FACTURACIÓN
    # ============================================
    
    pricing_product_id = fields.Many2one(
        'product.product',
        string='Producto de Alquiler',
        compute='_compute_pricing_product',
        store=True,
        help='Producto que se usará en la factura para el alquiler del vehículo'
    )
    
    insurance_product_id = fields.Many2one(
        'product.product',
        string='Producto de Seguro',
        compute='_compute_insurance_product',
        store=True,
        help='Producto que se usará en la factura para el seguro'
    )
    
    # ============================================
    # SEGUROS (OBLIGATORIOS)
    # ============================================
    
    insurance_type = fields.Selection([
        ('basic', 'Seguro Básico - Franquicia 300€'),
        ('no_franchise', 'Seguro Sin Franquicia'),
    ], string='Tipo de Seguro',
        required=True,
        default='basic',
        help='El seguro es obligatorio. Por defecto se aplica el básico con franquicia de 300€'
    )
    
    driver_special = fields.Boolean(
        string='Conductor Especial (<25 o >60 años)',
        default=False,
        help='Marcar si el conductor tiene menos de 25 años o más de 60 años (tarifa de seguro más alta)'
    )
    
    insurance_price_per_day = fields.Monetary(
        string='Seguro por Día',
        compute='_compute_insurance_price',
        store=True,
        currency_field='currency_id',
        help='Precio del seguro por día (calculado automáticamente)'
    )
    
    insurance_price_without_vat = fields.Monetary(
        string='Seguro por Día (sin IVA)',
        compute='_compute_insurance_price_without_vat',
        store=True,
        currency_field='currency_id'
    )
    
    total_insurance_cost = fields.Monetary(
        string='Costo Total Seguro',
        compute='_compute_total_insurance_cost',
        store=True,
        currency_field='currency_id',
        help='Costo total del seguro = precio por día × días totales'
    )
    
    total_insurance_cost_without_vat = fields.Monetary(
        string='Costo Total Seguro (sin IVA)',
        compute='_compute_total_insurance_cost_without_vat',
        store=True,
        currency_field='currency_id'
    )
    
    # ============================================
    # KM EXTRA (PARA FLEXIRENT)
    # ============================================
    
    is_flexirent = fields.Boolean(
        string='Es FLEXIRENT',
        compute='_compute_is_flexirent',
        store=True,
        help='Indica si este contrato usa tarifa FLEXIRENT (larga temporada)'
    )
    
    flexirent_km_included = fields.Float(
        string='Km Incluidos (FLEXIRENT)',
        help='Kilómetros incluidos en el paquete FLEXIRENT'
    )
    
    extra_km_used = fields.Float(
        string='Km Extra Utilizados',
        compute='_compute_extra_km_used',
        store=True,
        help='Kilómetros que exceden el límite del paquete'
    )
    
    extra_km_price_unit = fields.Monetary(
        string='Precio por Km Extra',
        currency_field='currency_id',
        help='Precio por kilómetro adicional (configurable, por defecto 0.21€)'
    )
    
    extra_km_cost = fields.Monetary(
        string='Costo Km Extra',
        compute='_compute_extra_km_cost',
        store=True,
        currency_field='currency_id',
        help='Costo total de kilómetros extra = km extra × precio por km'
    )
    
    # ============================================
    # TOTALES FINALES CON IVA / SIN IVA
    # ============================================
    
    subtotal_vehicle_rent = fields.Monetary(
        string='Subtotal Vehículo',
        compute='_compute_subtotal_vehicle_rent',
        store=True,
        currency_field='currency_id',
        help='Total de alquiler del vehículo (con km extra si aplica)'
    )
    
    subtotal_vehicle_rent_without_vat = fields.Monetary(
        string='Subtotal Vehículo (sin IVA)',
        compute='_compute_subtotal_vehicle_rent_without_vat',
        store=True,
        currency_field='currency_id'
    )
    
    grand_total_with_vat = fields.Monetary(
        string='Total General (IVA incluido)',
        compute='_compute_grand_total',
        store=True,
        currency_field='currency_id',
        help='Total: Vehículo + Seguro + Extras'
    )
    
    grand_total_without_vat = fields.Monetary(
        string='Total General (sin IVA)',
        compute='_compute_grand_total_without_vat',
        store=True,
        currency_field='currency_id'
    )
    
    # ============================================
    # MÉTODOS COMPUTADOS - PRICING AUTOMÁTICO
    # ============================================
    
    @api.depends('vehicle_id', 'vehicle_id.category_id', 'total_km', 'total_days', 'start_date', 'pricing_type')
    def _compute_rent_from_pricing_rules(self):
        """Calcula automáticamente el precio basándose en las reglas de tarificación"""
        for record in self:
            if not record.vehicle_id or not record.vehicle_id.category_id:
                record.calculated_rent = 0.0
                continue
            
            # Para FLEXIRENT, solo necesitamos días
            if record.pricing_type == 'flexirent':
                if not record.total_days:
                    record.calculated_rent = 0.0
                    continue
            else:
                # Para tarifa estándar, necesitamos días (km es opcional)
                if not record.total_days:
                    record.calculated_rent = 0.0
                    continue
            
            # Buscar la regla de pricing aplicable
            pricing_rule_model = self.env['vehicle.pricing.rule']
            
            # SIEMPRE buscar tarifa estándar directamente
            pricing_rule = pricing_rule_model.search([
                ('vehicle_category_id', '=', record.vehicle_id.category_id.id),
                ('pricing_type', '=', 'standard'),
                ('active', '=', True)
            ], limit=1, order='valid_from desc')
            
            if pricing_rule:
                record.calculated_rent = pricing_rule.price_per_unit
                
                # SIEMPRE actualizar el campo rent, pero solo rent_type si no está definido
                record.rent = pricing_rule.price_per_unit
                if not record.rent_type or record.rent_type == False:
                    record.rent_type = 'days'
                
                # Si es FLEXIRENT, guardar info adicional
                if pricing_rule.pricing_type == 'flexirent':
                    record.flexirent_km_included = pricing_rule.flexirent_km_total
                    record.extra_km_price_unit = pricing_rule.extra_km_price
            else:
                record.calculated_rent = 0.0
                # Mostrar advertencia si no hay tarifa
                if record.vehicle_id.category_id and record.total_km and record.total_days:
                    # Solo loggear, no lanzar error que bloquearía el formulario
                    _logger = self.env['ir.logging']
                    _logger.create({
                        'name': 'vehicle.contract.pricing',
                        'type': 'server',
                        'level': 'warning',
                        'message': f'No se encontró tarifa para categoría {record.vehicle_id.category_id.name}, '
                                 f'{record.total_km}km, {record.total_days} días',
                        'path': 'vehicle_rental',
                        'func': '_compute_rent_from_pricing_rules',
                        'line': '1',
                    })
    
    @api.depends('calculated_rent')
    def _compute_calculated_rent_without_vat(self):
        """Calcula el precio calculado sin IVA"""
        for record in self:
            record.calculated_rent_without_vat = record.calculated_rent / 1.21 if record.calculated_rent else 0.0
    
    @api.depends('vehicle_id', 'vehicle_id.category_id', 'total_km', 'total_days', 'start_date')
    def _compute_applied_pricing_rule(self):
        """Guarda referencia a la tarifa aplicada"""
        for record in self:
            if not record.vehicle_id or not record.vehicle_id.category_id:
                record.applied_pricing_rule_id = False
                continue
            
            if not record.total_km or not record.total_days:
                record.applied_pricing_rule_id = False
                continue
            
            pricing_rule_model = self.env['vehicle.pricing.rule']
            pricing_rule = pricing_rule_model.find_pricing_rule(
                category_id=record.vehicle_id.category_id.id,
                total_km=record.total_km,
                total_days=record.total_days,
                rental_date=record.start_date.date() if record.start_date else fields.Date.today()
            )
            
            record.applied_pricing_rule_id = pricing_rule.id if pricing_rule else False
    
    @api.depends('rent', 'calculated_rent')
    def _check_price_modified(self):
        """Verifica si el precio fue modificado manualmente"""
        for record in self:
            if record.calculated_rent and record.rent:
                # Tolerancia de 0.01 para evitar problemas de redondeo
                record.price_manually_modified = abs(record.rent - record.calculated_rent) > 0.01
            else:
                record.price_manually_modified = False
    
    @api.depends('applied_pricing_rule_id')
    def _compute_is_flexirent(self):
        """Determina si el contrato es FLEXIRENT"""
        for record in self:
            record.is_flexirent = (
                record.applied_pricing_rule_id and
                record.applied_pricing_rule_id.pricing_type == 'flexirent'
            )
    
    @api.depends('applied_pricing_rule_id', 'applied_pricing_rule_id.product_id')
    def _compute_pricing_product(self):
        """Obtiene el producto de la tarifa aplicada"""
        for record in self:
            if record.applied_pricing_rule_id and record.applied_pricing_rule_id.product_id:
                record.pricing_product_id = record.applied_pricing_rule_id.product_id
            else:
                # Fallback: usar producto genérico de alquiler
                product_template = self.env.ref('vehicle_rental.vehicle_rent_charge', raise_if_not_found=False)
                if product_template and hasattr(product_template, 'product_variant_ids') and product_template.product_variant_ids:
                    record.pricing_product_id = product_template.product_variant_ids[0].id
                else:
                    record.pricing_product_id = product_template.id if product_template else False
    
    @api.depends('insurance_type')
    def _compute_insurance_product(self):
        """Obtiene el producto según el tipo de seguro"""
        for record in self:
            product_template = False
            if record.insurance_type == 'basic':
                product_template = self.env.ref('vehicle_rental.product_insurance_basic', raise_if_not_found=False)
            elif record.insurance_type == 'no_franchise':
                product_template = self.env.ref('vehicle_rental.product_insurance_no_franchise', raise_if_not_found=False)
            
            # Obtener product.product (variante) desde product.template
            if product_template and product_template.product_variant_ids:
                record.insurance_product_id = product_template.product_variant_ids[0].id
            else:
                record.insurance_product_id = False
    
    # ============================================
    # MÉTODOS COMPUTADOS - SEGUROS
    # ============================================
    
    @api.depends('insurance_type', 'driver_special', 'total_days', 'start_date')
    def _compute_insurance_price(self):
        """Calcula el precio del seguro por día"""
        for record in self:
            if not record.total_days:
                record.insurance_price_per_day = 0.0
                continue
            
            insurance_model = self.env['vehicle.insurance.pricing']
            price = insurance_model.find_insurance_price(
                insurance_type=record.insurance_type,
                total_days=record.total_days,
                is_special_driver=record.driver_special,
                rental_date=record.start_date.date() if record.start_date else fields.Date.today()
            )
            
            record.insurance_price_per_day = price if price else 0.0
    
    @api.depends('insurance_price_per_day')
    def _compute_insurance_price_without_vat(self):
        """Calcula el precio del seguro sin IVA"""
        for record in self:
            record.insurance_price_without_vat = record.insurance_price_per_day / 1.21 if record.insurance_price_per_day else 0.0
    
    @api.depends('insurance_price_per_day', 'total_days')
    def _compute_total_insurance_cost(self):
        """Calcula el costo total del seguro"""
        for record in self:
            record.total_insurance_cost = record.insurance_price_per_day * record.total_days if record.insurance_price_per_day and record.total_days else 0.0
    
    @api.depends('total_insurance_cost')
    def _compute_total_insurance_cost_without_vat(self):
        """Calcula el costo total del seguro sin IVA"""
        for record in self:
            record.total_insurance_cost_without_vat = record.total_insurance_cost / 1.21 if record.total_insurance_cost else 0.0
    
    # ============================================
    # MÉTODOS COMPUTADOS - KM EXTRA
    # ============================================
    
    @api.depends('is_flexirent', 'flexirent_km_included', 'total_km')
    def _compute_extra_km_used(self):
        """Calcula los km extra utilizados en FLEXIRENT"""
        for record in self:
            if record.is_flexirent and record.flexirent_km_included:
                extra = record.total_km - record.flexirent_km_included
                record.extra_km_used = extra if extra > 0 else 0.0
            else:
                record.extra_km_used = 0.0
    
    @api.depends('extra_km_used', 'extra_km_price_unit')
    def _compute_extra_km_cost(self):
        """Calcula el costo de los km extra"""
        for record in self:
            record.extra_km_cost = record.extra_km_used * record.extra_km_price_unit if record.extra_km_used and record.extra_km_price_unit else 0.0
    
    # ============================================
    # MÉTODOS COMPUTADOS - TOTALES
    # ============================================
    
    @api.depends('rent', 'total_days', 'extra_km_cost')
    def _compute_subtotal_vehicle_rent(self):
        """Calcula el subtotal del alquiler del vehículo (con km extra si aplica)"""
        for record in self:
            base_rent = (record.rent * record.total_days) if record.rent and record.total_days else 0.0
            record.subtotal_vehicle_rent = base_rent + record.extra_km_cost
    
    @api.depends('subtotal_vehicle_rent')
    def _compute_subtotal_vehicle_rent_without_vat(self):
        """Calcula el subtotal del vehículo sin IVA"""
        for record in self:
            record.subtotal_vehicle_rent_without_vat = record.subtotal_vehicle_rent / 1.21 if record.subtotal_vehicle_rent else 0.0
    
    @api.depends('subtotal_vehicle_rent', 'total_insurance_cost', 'extra_service_charge')
    def _compute_grand_total(self):
        """Calcula el total general del contrato"""
        for record in self:
            record.grand_total_with_vat = (
                record.subtotal_vehicle_rent +
                record.total_insurance_cost +
                (record.extra_service_charge or 0.0)
            )
    
    @api.depends('grand_total_with_vat')
    def _compute_grand_total_without_vat(self):
        """Calcula el total general sin IVA"""
        for record in self:
            record.grand_total_without_vat = record.grand_total_with_vat / 1.21 if record.grand_total_with_vat else 0.0
    
    # ============================================
    # ONCHANGE - AUTOCOMPLETAR PRECIO
    # ============================================
    
    @api.onchange('vehicle_id', 'total_km', 'total_days')
    def _onchange_auto_calculate_rent(self):
        """Cuando cambia vehículo, km o días, auto-calcular el precio"""
        if self.calculated_rent and not self.rent:
            # Solo auto-rellenar si el campo rent está vacío
            self.rent = self.calculated_rent
    
    @api.onchange('calculated_rent')
    def _onchange_suggest_calculated_rent(self):
        """Sugerir usar el precio calculado"""
        if self.calculated_rent and self.rent:
            if abs(self.rent - self.calculated_rent) > 0.01:
                return {
                    'warning': {
                        'title': _('Precio Modificado'),
                        'message': _(
                            f'El precio calculado automáticamente es {self.calculated_rent:.2f}€ pero '
                            f'el precio actual es {self.rent:.2f}€. '
                            f'Si esto es intencional, por favor indica el motivo en "Motivo del Descuento".'
                        )
                    }
                }
    
    # ============================================
    # VALIDACIONES
    # ============================================
    
    @api.constrains('rent', 'calculated_rent', 'discount_reason', 'price_manually_modified')
    def _check_discount_reason_required(self):
        """Si el precio fue modificado manualmente, requiere motivo"""
        for record in self:
            if record.price_manually_modified and not record.discount_reason:
                raise ValidationError(
                    _('Debes indicar el motivo de la modificación de precio en el campo "Motivo del Descuento".')
                )
    
    @api.constrains('vehicle_id')
    def _check_vehicle_has_category(self):
        """Valida que el vehículo tenga categoría asignada"""
        for record in self:
            if record.vehicle_id and not record.vehicle_id.category_id:
                raise ValidationError(
                    _('El vehículo seleccionado no tiene una categoría asignada. '
                      'Por favor asigna una categoría al vehículo antes de crear el contrato.')
                )
    
    # ============================================
    # MÉTODOS DE ACCIÓN
    # ============================================
    
    def action_recalculate_price(self):
        """Botón para recalcular el precio según las tarifas actuales"""
        self.ensure_one()
        self._compute_rent_from_pricing_rules()
        
        if self.calculated_rent:
            self.rent = self.calculated_rent
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Precio Recalculado'),
                    'message': _('El precio se ha actualizado a %.2f€ según las tarifas actuales.') % self.calculated_rent,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('No se encontró una tarifa aplicable para este contrato.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
    
    def action_view_pricing_rule(self):
        """Botón para ver la tarifa aplicada"""
        self.ensure_one()
        if not self.applied_pricing_rule_id:
            raise UserError(_('No hay ninguna tarifa aplicada a este contrato.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tarifa Aplicada'),
            'res_model': 'vehicle.pricing.rule',
            'res_id': self.applied_pricing_rule_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    # ============================================
    # FACTURACIÓN AUTOMÁTICA
    # ============================================
    
    def _get_insurance_product(self):
        """Método auxiliar para obtener el producto de seguro del contrato"""
        self.ensure_one()
        
        # Buscar directamente el producto por external_id
        if self.insurance_type == 'basic':
            product_template = self.env.ref('vehicle_rental.product_insurance_basic', raise_if_not_found=False)
        elif self.insurance_type == 'no_franchise':
            product_template = self.env.ref('vehicle_rental.product_insurance_no_franchise', raise_if_not_found=False)
        else:
            return False
        
        # Obtener product.product (variante) desde product.template
        if product_template:
            if hasattr(product_template, 'product_variant_ids') and product_template.product_variant_ids:
                return product_template.product_variant_ids[0]
            else:
                # Si es directamente un product.product
                return product_template
        
        return False
    
    def action_create_invoice_automatic(self):
        """Crea factura automáticamente con productos y precios del contrato"""
        self.ensure_one()
        
        if not self.customer_id:
            raise UserError(_('Debe especificar un cliente antes de crear la factura.'))
        
        if not self.pricing_product_id:
            raise UserError(_('No se pudo determinar el producto de alquiler. Verifique que el vehículo tenga categoría asignada.'))
        
        # Preparar líneas de factura
        invoice_lines = []
        
        # LÍNEA 1: Alquiler del vehículo
        vehicle_line = {
            'product_id': self.pricing_product_id.id,
            'name': f"Alquiler {self.vehicle_id.category_id.name if self.vehicle_id.category_id else self.vehicle_id.model_id.name}\n"
                    f"Vehículo: {self.vehicle_id.license_plate}\n"
                    f"Período: {self.start_date.strftime('%d/%m/%Y')} - {self.end_date.strftime('%d/%m/%Y')}\n"
                    f"Días: {self.total_days:.0f} | Km: {self.total_km:.0f}",
            'quantity': self.total_days,
            'price_unit': self.rent,
            'tax_ids': [(6, 0, self.pricing_product_id.taxes_id.ids)],
        }
        invoice_lines.append((0, 0, vehicle_line))
        
        # LÍNEA 2: Seguro (SIEMPRE, porque es obligatorio)
        import logging
        _logger = logging.getLogger(__name__)
        
        # Obtener el producto de seguro directamente
        insurance_product = self._get_insurance_product()
        
        # Si no hay precio calculado automáticamente, usar precio del producto o predeterminado
        if self.insurance_price_per_day and self.insurance_price_per_day > 0:
            insurance_price = self.insurance_price_per_day
        elif insurance_product and insurance_product.list_price > 0:
            insurance_price = insurance_product.list_price
        else:
            # Precio predeterminado si no hay tarifa: 8€ básico, 12€ sin franquicia
            insurance_price = 8.0 if self.insurance_type == 'basic' else 12.0
        
        _logger.info(f"DEBUG SEGURO - Tipo: {self.insurance_type}, Producto: {insurance_product}, Precio: {insurance_price}")
        
        if insurance_product:
            insurance_name = "Seguro Básico - Franquicia 300€" if self.insurance_type == 'basic' else "Seguro Sin Franquicia"
            if self.driver_special:
                insurance_name += " (Conductor Especial)"
            
            insurance_line = {
                'product_id': insurance_product.id,
                'name': insurance_name,
                'quantity': self.total_days,
                'price_unit': insurance_price,
                'tax_ids': [(6, 0, insurance_product.taxes_id.ids)],
            }
            invoice_lines.append((0, 0, insurance_line))
        else:
            _logger.warning(f"⚠️  SEGURO NO AÑADIDO - Producto: {insurance_product}, Precio: {insurance_price}, Tipo: {self.insurance_type}")
        
        # LÍNEA 3: Km Extra (si aplica en FLEXIRENT)
        if self.extra_km_cost and self.extra_km_cost > 0:
            extra_km_product = self.env.ref('vehicle_rental.product_extra_km_flexirent', raise_if_not_found=False)
            if not extra_km_product:
                # Usar producto genérico de extras
                extra_km_product = self.env.ref('vehicle_rental.vehicle_rent_extra_charge', raise_if_not_found=False)
            
            if extra_km_product:
                extra_km_line = {
                    'product_id': extra_km_product.id,
                    'name': f"Kilómetros Extra - FLEXIRENT\n{self.extra_km_used:.0f} km × {self.extra_km_price_unit:.2f}€",
                    'quantity': self.extra_km_used,
                    'price_unit': self.extra_km_price_unit,
                    'tax_ids': [(6, 0, extra_km_product.taxes_id.ids)],
                }
                invoice_lines.append((0, 0, extra_km_line))
        
        # LÍNEA 4: Servicios Extra (si existen)
        for extra_service in self.extra_service_ids:
            if extra_service.product_id:
                extra_line = {
                    'product_id': extra_service.product_id.id,
                    'name': extra_service.name or extra_service.product_id.name,
                    'quantity': extra_service.qty,
                    'price_unit': extra_service.price,
                    'tax_ids': [(6, 0, extra_service.product_id.taxes_id.ids)],
                }
                invoice_lines.append((0, 0, extra_line))
        
        # Crear la factura
        invoice_vals = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.reference_no,
            'invoice_line_ids': invoice_lines,
            'narration': f"Factura automática generada desde contrato {self.reference_no}",
            'vehicle_contract_id': self.id,  # ← Vincular con el contrato para que aparezca en el dashboard
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Guardar referencia en el contrato para evitar facturas duplicadas
        self.invoice_id = invoice.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura Creada'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

