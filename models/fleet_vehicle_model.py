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
