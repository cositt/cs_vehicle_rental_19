# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
            raise UserError(_(
                'Indique el importe de la fianza a devolver del contrato %s. '
                'Si va a retener la fianza completa, no genere esta factura.',
                contract.reference_no,
            ))
        invoice_line_vals = {
            'product_id': self.env.ref('vehicle_rental.vehicle_rent_deposit').id,
            'name': f"Return Deposit for - {contract.reference_no} - {contract.vehicle_id.name}",
            'quantity': 1,
            'price_unit': self.return_deposit,
        }
        invoice_lines.append((0, 0, invoice_line_vals))
        # Prepare invoice
        # Obtener journal de ventas del contrato
        sale_journal = contract._get_sale_journal()
        data = {
            'partner_id': contract.customer_id.id,
            'move_type': 'out_refund',
            'journal_id': sale_journal.id,
            'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
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
