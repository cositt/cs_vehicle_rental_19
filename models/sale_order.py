# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class SaleOrder(models.Model):
    """Sale Order - Vehicle Rental Extension"""
    _inherit = 'sale.order'

    # Campos de vehículo para reservas
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle",
                                 domain="[('status', '=', 'available')]")
    rental_start_date = fields.Datetime(string="Pick-up Date")
    rental_end_date = fields.Datetime(string="Return Date")
    vehicle_contract_id = fields.Many2one('vehicle.contract', string="Vehicle Contract",
                                         readonly=True, copy=False)
    is_vehicle_rental = fields.Boolean(string="Is Vehicle Rental",
                                       compute='_compute_is_vehicle_rental',
                                       store=True)

    @api.depends('vehicle_id', 'opportunity_id.vehicle_id')
    def _compute_is_vehicle_rental(self):
        """Determine if this order is for vehicle rental"""
        for order in self:
            order.is_vehicle_rental = bool(order.vehicle_id or 
                                          (order.opportunity_id and order.opportunity_id.vehicle_id))

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        """Copy vehicle and dates from opportunity/lead (compatible across Odoo versions)."""
        res = {}

        # Compatibility guard: in some Odoo versions parent has no _onchange_opportunity_id
        parent_method = getattr(super(SaleOrder, self), '_onchange_opportunity_id', None)
        if callable(parent_method):
            parent_res = parent_method()
            if isinstance(parent_res, dict):
                res = parent_res

        if self.opportunity_id and self.opportunity_id.vehicle_id:
            self.vehicle_id = self.opportunity_id.vehicle_id

            from datetime import datetime, time

            if hasattr(self.opportunity_id, 'start_date') and self.opportunity_id.start_date:
                if isinstance(self.opportunity_id.start_date, str):
                    date_obj = datetime.strptime(self.opportunity_id.start_date, '%Y-%m-%d').date()
                else:
                    date_obj = self.opportunity_id.start_date
                self.rental_start_date = datetime.combine(date_obj, time.min)

            if hasattr(self.opportunity_id, 'end_date') and self.opportunity_id.end_date:
                if isinstance(self.opportunity_id.end_date, str):
                    date_obj = datetime.strptime(self.opportunity_id.end_date, '%Y-%m-%d').date()
                else:
                    date_obj = self.opportunity_id.end_date
                self.rental_end_date = datetime.combine(date_obj, time.max)

        return res

    def action_create_vehicle_contract(self):
        """Open wizard to create vehicle contract from sale order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Contrato de Vehículo',
            'res_model': 'sale.order.to.vehicle.contract',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_vehicle_id': self.vehicle_id.id if self.vehicle_id else False,
                'default_start_date': self.rental_start_date,
                'default_end_date': self.rental_end_date,
            }
        }

