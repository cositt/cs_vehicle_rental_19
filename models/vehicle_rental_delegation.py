# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Address fields shared by delegation and contract pick-up / drop-off
ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')


class VehicleRentalDelegation(models.Model):
    """Delegation (branch) where vehicles are picked up and dropped off.

    Shared by every company: Sunset rents Pinveco vehicles from the same
    delegations. Created by the customer, nothing is preloaded.
    """
    _name = 'vehicle.rental.delegation'
    _description = 'Delegación'
    _order = 'sequence, name'

    name = fields.Char(string='Delegación', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    street = fields.Char(string='Calle')
    street2 = fields.Char(string='Calle 2')
    zip = fields.Char(string='C.P.')
    city = fields.Char(string='Ciudad')
    state_id = fields.Many2one('res.country.state', string='Provincia',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='País',
                                 default=lambda self: self.env.ref('base.es', raise_if_not_found=False))
    phone = fields.Char(string='Teléfono')
    email = fields.Char(string='Email')
    schedule = fields.Text(string='Horario')
    vehicle_count = fields.Integer(string='Vehículos', compute='_compute_vehicle_count')

    def _compute_vehicle_count(self):
        counts = dict(self.env['fleet.vehicle'].sudo()._read_group(
            [('delegation_id', 'in', self.ids)], ['delegation_id'], ['__count']))
        for delegation in self:
            delegation.vehicle_count = counts.get(delegation, 0)

    def _address_values(self, prefix):
        """Contract address values (pick_up_* / drop_off_*) for this delegation."""
        self.ensure_one()
        return {f'{prefix}_{name}': self[name].id if name.endswith('_id') else (self[name] or False)
                for name in ADDRESS_FIELDS}

    @api.model
    def _website_delegations(self):
        """Active delegations for the public pages, as plain values."""
        return [{
            'name': delegation.name,
            'address': ', '.join(part for part in (
                delegation.street, delegation.street2,
                ' '.join(p for p in (delegation.zip, delegation.city) if p)) if part),
            'phone': delegation.phone or '',
            'email': (delegation.email or '').lower(),
            'schedule': delegation.schedule or '',
        } for delegation in self.sudo().search([])]
