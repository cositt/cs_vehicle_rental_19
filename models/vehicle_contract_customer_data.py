# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

# Contract field -> customer field, copied while the contract field is empty
CUSTOMER_LICENSE_FIELDS = ('driver_license_number', 'driver_license_issue_date', 'driver_license_expiry_date')
FUEL_FULL = '4'


class VehicleContractCustomerData(models.Model):
    """What a new contract fills on its own (Jesús Muñoz, 2026-10-22).

    Choosing the customer brings its DNI/CIF, address and licence; an expired
    licence or DNI is flagged; payment and fuel start with the usual values.
    """
    _inherit = 'vehicle.contract'

    payment_type = fields.Selection(default='full_payment')
    initial_fuel_level = fields.Selection(default=FUEL_FULL)
    driver_license_expired = fields.Boolean(
        string="Carnet caducado", compute='_compute_document_expired',
        help="El carnet caduca antes de la devolución.")
    customer_dni_expired = fields.Boolean(
        string="DNI caducado", compute='_compute_document_expired',
        help="El DNI caduca antes de la devolución.")

    @api.depends('driver_license_expiry_date', 'customer_dni_expiry_date', 'end_date')
    def _compute_document_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            limit = max(today, rec.end_date.date()) if rec.end_date else today
            rec.driver_license_expired = bool(rec.driver_license_expiry_date
                                              and rec.driver_license_expiry_date < limit)
            rec.customer_dni_expired = bool(rec.customer_dni_expiry_date
                                            and rec.customer_dni_expiry_date < limit)

    @api.model
    def _customer_document_values(self, customer):
        """DNI/CIF, address and licence of the customer."""
        if not customer:
            return {}
        address = ', '.join(part for part in (
            customer.street, customer.street2,
            ' '.join(p for p in (customer.zip, customer.city) if p)) if part)
        values = {
            # A company contact inherits the company VAT: its own DNI goes apart
            'customer_dni': customer.driver_identity_number or customer.vat,
            'customer_address': address,
        }
        values.update({name: customer[name] for name in CUSTOMER_LICENSE_FIELDS})
        return {name: value for name, value in values.items() if value}

    @api.onchange('customer_id')
    def onchange_customer_details(self):
        """Onchange customer details"""
        for rec in self:
            rec.customer_phone = rec.customer_id.phone
            rec.customer_email = rec.customer_id.email
            # A new customer replaces the data of the previous one
            for name, value in self._customer_document_values(rec.customer_id).items():
                rec[name] = value

    @api.onchange('pricing_type')
    def _onchange_pricing_type_payment(self):
        """FLEXIRENT is a monthly fee: propose monthly instalments."""
        if self.pricing_type == 'flexirent' and self.payment_type in (False, 'full_payment'):
            self.payment_type = 'monthly'

    @api.onchange('driver_license_expiry_date', 'customer_dni_expiry_date', 'end_date')
    def _onchange_document_expiry(self):
        expired = []
        if self.driver_license_expired:
            expired.append(_('el carnet de conducir'))
        if self.customer_dni_expired:
            expired.append(_('el DNI'))
        if expired:
            return {'warning': {
                'title': _('Documento caducado'),
                'message': _('Caduca %s antes de la devolución. Pida el documento en vigor '
                             'antes de entregar el vehículo.', _(' y ').join(expired)),
            }}

    @api.model_create_multi
    def create(self, vals_list):
        """The booking wizard and the website create contracts without the onchange."""
        partners = self.env['res.partner'].browse(
            [vals['customer_id'] for vals in vals_list if vals.get('customer_id')])
        by_id = {partner.id: partner for partner in partners}
        new_vals_list = []
        for vals in vals_list:
            customer = by_id.get(vals.get('customer_id'))
            defaults = {name: value for name, value in self._customer_document_values(customer).items()
                        if not vals.get(name)}
            new_vals_list.append(dict(vals, **defaults))
        return super().create(new_vals_list)
