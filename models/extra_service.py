# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models


class ExtraService(models.Model):
    """Vehicle Extra Service"""
    _name = 'extra.service'
    _description = __doc__
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    description = fields.Char(string="Description")
    product_qty = fields.Float(string="Quantity", required=True, default=1)
    amount = fields.Monetary(string="Amount")
    total_service_charge = fields.Monetary(string="Sub Total",
                                           compute='_compute_total_service_charge')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    vehicle_contract_id = fields.Many2one('vehicle.contract', ondelete="cascade")

    @api.onchange('product_id')
    def vehicle_extra_service_charge(self):
        """Vehicle extra service charge"""
        for rec in self:
            rec.amount = rec.product_id.lst_price

    @api.depends('product_qty', 'amount')
    def _compute_total_service_charge(self):
        """Compute total service charge"""
        for rec in self:
            rec.total_service_charge = rec.product_qty * rec.amount
