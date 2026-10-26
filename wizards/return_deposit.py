# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
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
                    'total_deposit': contract.deposit_charged or contract.deposit,
                    'return_deposit': contract.deposit_charged or contract.deposit,
                })
        return res

    def create_return_deposit_invoice(self):
        """Create the credit note giving the deposit back."""
        invoice = self.contract_id._create_deposit_refund(self.return_deposit)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devolución de fianza'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
