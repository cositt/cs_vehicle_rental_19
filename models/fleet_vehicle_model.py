# -*- coding: utf-8 -*-
# Copyright 2025
# Extension del modelo de flota para añadir un nuevo tipo de vehículo.
from odoo import models, fields


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    vehicle_type = fields.Selection(
        selection_add=[('van', 'Furgoneta')],
        ondelete={'van': 'set default'}
    )


class FleetVehicleModelCategory(models.Model):
    """Herencia de fleet.vehicle.model.category para agregar campos de depósito"""
    _inherit = 'fleet.vehicle.model.category'
    
    # Campos de depósito por tipo de tarjeta
    deposit_percent_credit = fields.Float(
        string='Depósito % (Tarjeta de Crédito)',
        default=15.0,
        help='Porcentaje de depósito requerido para tarjetas de crédito'
    )
    
    deposit_percent_debit = fields.Float(
        string='Depósito % (Tarjeta de Débito)',
        default=30.0,
        help='Porcentaje de depósito requerido para tarjetas de débito'
    )
    
    deposit_amount_credit = fields.Float(
        string='Depósito Fijo (Crédito)',
        help='Monto fijo de depósito para tarjetas de crédito (si está definido, prevalece sobre %)'
    )
    
    deposit_amount_debit = fields.Float(
        string='Depósito Fijo (Débito)',
        help='Monto fijo de depósito para tarjetas de débito (si está definido, prevalece sobre %)'
    )
