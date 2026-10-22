# -*- coding: utf-8 -*-
from odoo import api, fields, models

LICENSE_FIELDS = ('driver_license_number', 'driver_license_issue_date', 'driver_license_expiry_date')


class VehicleContractDriver(models.Model):
    """Authorized driver of the contract.

    Optional: the contract saves without one and handing the vehicle over only
    asks for confirmation. It is the customer or one of its contacts, a driver
    created from the contract becomes a child contact of the customer company,
    and its licence fills the contract fields that are still empty.
    """
    _inherit = 'vehicle.contract'

    customer_commercial_partner_id = fields.Many2one(
        related='customer_id.commercial_partner_id', string="Empresa del cliente")
    authorized_driver_id = fields.Many2one(
        'res.partner', string="Conductor autorizado", tracking=True,
        domain="['|', '|', ('id', '=', customer_id), ('id', '=', customer_commercial_partner_id),"
               " ('parent_id', '=', customer_commercial_partner_id)]",
        help="Quien conduce el vehículo. Si no está en la lista, créelo aquí: "
             "se guarda como contacto de la empresa del cliente.")

    def _authorized_driver_domain(self):
        self.ensure_one()
        company = self.customer_id.commercial_partner_id
        return ['|', '|', ('id', '=', self.customer_id.id), ('id', '=', company.id),
                ('parent_id', '=', company.id)]

    def _authorized_driver_creation_context(self):
        self.ensure_one()
        return {
            'default_parent_id': self.customer_id.commercial_partner_id.id,
            'default_type': 'contact',
            'default_is_company': False,
        }

    def _driver_license_values(self, driver, current=None):
        """Licence of the driver for the contract fields that are still empty."""
        current = current or {}
        return {name: driver[name] for name in LICENSE_FIELDS if driver[name] and not current.get(name)}

    @api.onchange('authorized_driver_id')
    def _onchange_authorized_driver(self):
        if self.authorized_driver_id:
            current = {name: self[name] for name in LICENSE_FIELDS}
            for name, value in self._driver_license_values(self.authorized_driver_id, current).items():
                self[name] = value

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        contracts.filtered('authorized_driver_id')._fill_driver_license()
        return contracts

    def write(self, vals):
        result = super().write(vals)
        if vals.get('authorized_driver_id'):
            self._fill_driver_license()
        return result

    def _fill_driver_license(self):
        for contract in self:
            current = {name: contract[name] for name in LICENSE_FIELDS}
            values = self._driver_license_values(contract.authorized_driver_id, current)
            if values:
                super(VehicleContractDriver, contract).write(values)

    def a_draft_to_b_in_progress(self):
        without_driver = self.filtered(lambda c: c.status == 'a_draft' and not c.authorized_driver_id)
        if without_driver and not self.env.context.get('hand_over_without_driver'):
            self._check_hand_over_ready()
            return {
                'type': 'ir.actions.act_window',
                'name': "Entregar sin conductor",
                'res_model': 'vehicle.contract.driver.confirm',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_contract_ids': [fields.Command.set(self.ids)]},
            }
        return super().a_draft_to_b_in_progress()
