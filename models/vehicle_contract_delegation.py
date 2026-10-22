# -*- coding: utf-8 -*-
from odoo import api, fields, models


class VehicleContractDelegation(models.Model):
    """Pick-up and drop-off delegations of the contract.

    Choosing a delegation fills the address, which stays editable. The vehicle
    gets its company and delegation when handed over if it had none, and moves
    to the drop-off delegation when returned.
    """
    _inherit = 'vehicle.contract'

    pick_up_delegation_id = fields.Many2one(
        'vehicle.rental.delegation', string='Delegación de Recogida', index=True,
        help='Por defecto, la delegación donde está el vehículo.')
    drop_off_delegation_id = fields.Many2one(
        'vehicle.rental.delegation', string='Delegación de Entrega', index=True,
        help='El vehículo pasa a esta delegación cuando se devuelve.')

    @api.model
    def _delegation_address(self, vals, prefix):
        """Address of the chosen delegation, without overriding what vals already bring."""
        delegation = self.env['vehicle.rental.delegation'].browse(vals[f'{prefix}_delegation_id'])
        return {key: value for key, value in delegation._address_values(prefix).items()
                if key not in vals}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('pick_up_delegation_id') and vals.get('vehicle_id'):
                vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
                vals['pick_up_delegation_id'] = vehicle.sudo().delegation_id.id
            for prefix in ('pick_up', 'drop_off'):
                if vals.get(f'{prefix}_delegation_id'):
                    vals.update(self._delegation_address(vals, prefix))
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        for prefix in ('pick_up', 'drop_off'):
            if vals.get(f'{prefix}_delegation_id'):
                vals.update(self._delegation_address(vals, prefix))
        return super().write(vals)

    @api.onchange('pick_up_delegation_id')
    def _onchange_pick_up_delegation(self):
        if self.pick_up_delegation_id:
            self.update(self.pick_up_delegation_id._address_values('pick_up'))

    @api.onchange('drop_off_delegation_id')
    def _onchange_drop_off_delegation(self):
        if self.drop_off_delegation_id:
            self.update(self.drop_off_delegation_id._address_values('drop_off'))

    @api.onchange('vehicle_id')
    def _onchange_vehicle_delegation(self):
        if self.vehicle_id.delegation_id:
            self.pick_up_delegation_id = self.vehicle_id.delegation_id
            self._onchange_pick_up_delegation()

    def a_draft_to_b_in_progress(self):
        result = super().a_draft_to_b_in_progress()
        for contract in self.filtered(lambda c: c.status == 'b_in_progress' and c.vehicle_id):
            vehicle = contract.vehicle_id.sudo()
            values = {}
            if not vehicle.company_id:
                values['company_id'] = contract.company_id.id
            if not vehicle.delegation_id and contract.pick_up_delegation_id:
                values['delegation_id'] = contract.pick_up_delegation_id.id
            if values:
                vehicle.write(values)
        return result

    def _apply_return(self):
        result = super()._apply_return()
        for contract in self.filtered('vehicle_id'):
            vehicle = contract.vehicle_id.sudo()
            values = {}
            if contract.drop_off_delegation_id:
                values.update(delegation_id=contract.drop_off_delegation_id.id,
                              location=contract.drop_off_delegation_id.name)
            if not vehicle.company_id:
                values['company_id'] = contract.company_id.id
            if values:
                vehicle.write(values)
        return result
