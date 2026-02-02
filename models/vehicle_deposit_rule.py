# -*- coding: utf-8 -*-
# Copyright 2025
# Sistema de Depósitos Dinámicos para Vehicle Rental

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VehicleDepositRule(models.Model):
    """
    Modelo para gestionar depósitos dinámicos basados en:
    - Tipo de tarjeta (débito/crédito)
    - Categoría de vehículo
    - Precio del alquiler
    """
    _name = 'vehicle.deposit.rule'
    _description = 'Regla de Depósitos Dinámicos por Tipo de Tarjeta'
    _order = 'vehicle_category_id, card_type'
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
        help='Desactivar para ocultar depósitos obsoletos sin eliminarlos'
    )

    # ============================================
    # CONFIGURACIÓN
    # ============================================
    vehicle_category_id = fields.Many2one(
        'fleet.vehicle.model.category',
        string='Categoría de Vehículo',
        required=True,
        ondelete='restrict',
        help='Tipo de vehículo al que aplica esta tarifa de depósito'
    )

    card_type = fields.Selection(
        [
            ('debit', 'Tarjeta de Débito'),
            ('credit', 'Tarjeta de Crédito'),
        ],
        string='Tipo de Tarjeta',
        required=True,
        help='Tipo de tarjeta para el cual se aplica este depósito'
    )

    # ============================================
    # CONFIGURACIÓN DE DEPÓSITO
    # ============================================
    deposit_fixed = fields.Monetary(
        string='Depósito Fijo',
        default=0,
        currency_field='currency_id',
        help='Cantidad fija de depósito para este tipo de tarjeta y categoría'
    )

    deposit_percentage = fields.Float(
        string='Porcentaje sobre Alquiler (%)',
        default=0,
        help='Porcentaje adicional del precio de alquiler como depósito (ej: 10 = 10% del alquiler)'
    )

    apply_both = fields.Boolean(
        string='Aplicar Ambos (Fijo + Porcentaje)',
        default=False,
        help='Si está activo, suma depósito fijo + porcentaje. Si no, toma el máximo de ambos.'
    )

    min_deposit = fields.Monetary(
        string='Depósito Mínimo',
        default=0,
        currency_field='currency_id',
        help='Depósito mínimo aunque el cálculo sea menor'
    )

    max_deposit = fields.Monetary(
        string='Depósito Máximo',
        default=0,
        currency_field='currency_id',
        help='Depósito máximo (0 = sin límite)'
    )

    # ============================================
    # MONEDA
    # ============================================
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
        help='Fecha desde la cual esta regla de depósito está activa'
    )

    valid_until = fields.Date(
        string='Válido Hasta',
        help='Fecha hasta la cual esta regla es válida. Dejar vacío para validez indefinida.'
    )

    # ============================================
    # INFORMACIÓN ADICIONAL
    # ============================================
    notes = fields.Text(
        string='Notas',
        help='Notas y condiciones especiales'
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

    @api.depends('vehicle_category_id', 'card_type')
    def _compute_name(self):
        """Genera nombre descriptivo automáticamente"""
        for record in self:
            card_label = dict(record._fields['card_type'].selection).get(record.card_type, '')
            record.name = f"{record.vehicle_category_id.name or 'Sin categoría'} - {card_label}"

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

    @api.constrains('deposit_fixed', 'deposit_percentage')
    def _check_deposit_values(self):
        """Valida que al menos uno de los depósitos tenga un valor"""
        for record in self:
            if record.deposit_fixed <= 0 and record.deposit_percentage <= 0:
                raise ValidationError(
                    _('Debe especificar al menos un Depósito Fijo o un Porcentaje.')
                )

    @api.constrains('min_deposit', 'max_deposit')
    def _check_deposit_limits(self):
        """Valida que el depósito mínimo no sea mayor que el máximo"""
        for record in self:
            if record.max_deposit > 0 and record.min_deposit > record.max_deposit:
                raise ValidationError(
                    _('El Depósito Mínimo no puede ser mayor que el Depósito Máximo.')
                )

    # Constraint SQL para evitar duplicados
    _sql_constraints = [
        ('unique_deposit_rule',
         'UNIQUE(vehicle_category_id, card_type, valid_from, company_id)',
         'Ya existe una regla de depósito para esta categoría, tipo de tarjeta y fecha.'),
    ]

    # ============================================
    # MÉTODOS DE CÁLCULO
    # ============================================

    def calculate_deposit(self, rental_price):
        """
        Calcula el depósito basado en la regla y el precio del alquiler.
        
        Args:
            rental_price: Precio del alquiler (float/Decimal)
        
        Returns:
            Monto del depósito calculado (float)
        """
        self.ensure_one()

        deposit = 0

        if self.apply_both:
            # Aplicar ambos: fijo + porcentaje
            deposit = self.deposit_fixed + (rental_price * self.deposit_percentage / 100)
        else:
            # Tomar el máximo entre fijo y porcentaje
            percentage_amount = rental_price * self.deposit_percentage / 100
            deposit = max(self.deposit_fixed, percentage_amount)

        # Aplicar límite mínimo
        if self.min_deposit > 0:
            deposit = max(deposit, self.min_deposit)

        # Aplicar límite máximo
        if self.max_deposit > 0:
            deposit = min(deposit, self.max_deposit)

        return deposit

    # ============================================
    # MÉTODOS DE BÚSQUEDA
    # ============================================

    def find_deposit_rule(self, category_id, card_type, rule_date=None):
        """
        Busca la regla de depósito aplicable para una combinación de parámetros.
        
        Args:
            category_id: ID de la categoría del vehículo
            card_type: Tipo de tarjeta ('debit' o 'credit')
            rule_date: Fecha para buscar regla vigente (por defecto hoy)
        
        Returns:
            Registro de vehicle.deposit.rule o False
        """
        if not rule_date:
            rule_date = fields.Date.today()

        domain = [
            ('vehicle_category_id', '=', category_id),
            ('card_type', '=', card_type),
            ('valid_from', '<=', rule_date),
            '|', ('valid_until', '=', False), ('valid_until', '>=', rule_date),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ]

        return self.search(domain, limit=1, order='valid_from desc')

    def get_deposit_amount(self, category_id, card_type, rental_price):
        """
        Obtiene el monto de depósito calculado para una reserva.
        
        Args:
            category_id: ID de la categoría del vehículo
            card_type: Tipo de tarjeta ('debit' o 'credit')
            rental_price: Precio del alquiler
        
        Returns:
            Monto del depósito (float) o 0 si no hay regla
        """
        rule = self.find_deposit_rule(category_id, card_type)
        if rule:
            return rule.calculate_deposit(rental_price)
        return 0
