# -*- coding: utf-8 -*-
from odoo import fields, models


class VehicleContractDriverConfirm(models.TransientModel):
    """Confirmation before handing a vehicle over without an authorized driver."""
    _name = 'vehicle.contract.driver.confirm'
    _description = "Confirmar entrega sin conductor"

    contract_ids = fields.Many2many('vehicle.contract', string="Contratos", readonly=True)

    def action_confirm(self):
        self.ensure_one()
        return self.contract_ids.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
