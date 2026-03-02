# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class FleetVehicleMultiBooking(models.Model):
    _inherit = 'fleet.vehicle'

    def action_create_book_contract(self):
        """Override: desvía al flujo correcto según el contexto del wizard."""
        wizard_model = self.env.context.get('wizard_model')
        wizard_id = self.env.context.get('wizard_id')

        if wizard_model and wizard_id:
            wizard = self.env[wizard_model].browse(wizard_id)
            if wizard.exists():
                if hasattr(wizard, 'multi_booking_id') and wizard.multi_booking_id:
                    return wizard._add_to_multi_booking(self)
                if hasattr(wizard, 'group_id') and wizard.group_id:
                    return wizard.action_create_contract_for_vehicle(self.id)

        return super().action_create_book_contract()
