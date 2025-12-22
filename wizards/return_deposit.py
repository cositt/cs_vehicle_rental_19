# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from ..utils import _display_rental_notification
from odoo import models, fields, api, _


class ReturnDeposit(models.TransientModel):
    """Return Deposit"""
    _name = 'return.deposit'
    _description = __doc__

    contract_id = fields.Many2one('vehicle.contract', string="Contract")
    total_deposit = fields.Monetary(string="Total Deposit")
    return_deposit = fields.Monetary(string="Amount to Return")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id", store=True)

    @api.model
    def default_get(self, field_names):
        """Set default values from vehicle contract"""
        res = super().default_get(field_names)
        active_id = self.env.context.get('active_id')
        if active_id:
            contract = self.env['vehicle.contract'].browse(active_id)
            if contract:
                res.update({
                    'contract_id': contract.id,
                    'total_deposit': contract.deposit,
                    'return_deposit': contract.deposit,
                })
        return res

    def create_return_deposit_invoice(self):
        """Handle vehicle rent deposit process."""
        contract = self.contract_id
        invoice_lines = []
        if not self.return_deposit:
            return _display_rental_notification(
                message=_("Please note: A return deposit amount is required."),
                message_type='warning'
            )
        invoice_line_vals = {
            'product_id': self.env.ref('vehicle_rental.vehicle_rent_deposit').id,
            'name': f"Return Deposit for - {contract.reference_no} - {contract.vehicle_id.name}",
            'quantity': 1,
            'price_unit': self.return_deposit,
        }
        invoice_lines.append((0, 0, invoice_line_vals))
        # Prepare invoice
        data = {
            'partner_id': contract.customer_id.id,
            'move_type': 'out_refund',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'vehicle_contract_id': contract.id
        }

        invoice = self.env['account.move'].sudo().create(data)
        contract.return_deposit_invoice_id = invoice.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Deposit Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
