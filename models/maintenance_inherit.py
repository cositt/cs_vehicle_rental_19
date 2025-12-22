# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class VehicleMaintenancePart(models.Model):
    """Vehicle Maintenance Part"""
    _name = 'vehicle.maintenance.part'
    _description = __doc__
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Part",
                                 domain="[('type', '=', 'consu')]")
    description = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity", default=1)
    price_unit = fields.Monetary(string="Price")
    price_sub_total = fields.Monetary(string="Sub Total",
                                      compute='_compute_price_sub_total')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    maintenance_request_id = fields.Many2one('maintenance.request', ondelete='cascade')

    @api.onchange('product_id')
    def _onchange_part_price(self):
        """Onchange part price"""
        for rec in self:
            rec.price_unit = rec.product_id.lst_price
            rec.description = rec.product_id.name

    @api.depends('quantity', 'price_unit')
    def _compute_price_sub_total(self):
        """Compute price sub total"""
        for rec in self:
            rec.price_sub_total = rec.quantity * rec.price_unit


class VehicleMaintenanceService(models.Model):
    """Vehicle Maintenance Service"""
    _name = 'vehicle.maintenance.service'
    _description = __doc__
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Service",
                                 domain=[('type', '=', 'service')])
    description = fields.Char(string="Description", translate=True)
    service_charge = fields.Monetary(string="Service Charge")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    maintenance_request_id = fields.Many2one('maintenance.request',
                                             ondelete='cascade')

    @api.onchange('product_id')
    def _onchange_service_charge(self):
        """Onchange service charge"""
        for rec in self:
            rec.service_charge = rec.product_id.lst_price


class VehicleMaintenanceRequest(models.Model):
    """Vehicle Maintenance Request"""
    _inherit = 'maintenance.request'
    _description = __doc__

    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string="Fleet Vehicle")
    maintenance_schedule_id = fields.Many2one('maintenance.schedule',
                                              string="Next Maintenance Schedule")
    upcoming_maintenance_date = fields.Date(string="Upcoming Maintenance Date")
    vehicle_maintenance_part_ids = fields.One2many(
        'vehicle.maintenance.part', 'maintenance_request_id')
    vehicle_maintenance_service_ids = fields.One2many(
        'vehicle.maintenance.service', 'maintenance_request_id')

    part_price = fields.Monetary(compute="_compute_part_price",
                                 string="Part Price", store=True)
    service_charge = fields.Monetary(compute="_compute_service_charge",
                                     string="Service Charges", store=True)
    sub_total = fields.Monetary(string="Sub Total", compute="_compute_sub_total")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    bill_id = fields.Many2one('account.move', string="Bill")
    bill_count = fields.Integer(compute='_compute_bill_count',
                                string="Vendor Bill")

    @api.model
    def action_create_schedule_maintenance(self):
        """Action create schedule maintenance"""
        today_date = fields.Date.today()
        maintenance_requests = self.sudo().search([('fleet_vehicle_id', '!=', False)])
        for request in maintenance_requests:
            if today_date == request.upcoming_maintenance_date:
                maintenance_days = request.maintenance_schedule_id.maintenance_days
                # Calculate the next maintenance date
                next_maintenance_date = request.request_date + relativedelta(days=maintenance_days)
                # Create a new maintenance request
                request.fleet_vehicle_id.action_create_maintenance_request()
                # Update the upcoming maintenance date
                request.upcoming_maintenance_date = next_maintenance_date
                # Ensure the new record’s request_date is set correctly
                new_request = self.sudo().search([
                    ('fleet_vehicle_id', '=', request.fleet_vehicle_id.id),
                    ('request_date', '>', request.request_date)
                ], order='request_date asc', limit=1)
                if new_request:
                    new_request.upcoming_maintenance_date = (
                        new_request.request_date
                        + relativedelta(days=request.maintenance_schedule_id.maintenance_days)
                    )

    @api.depends('vehicle_maintenance_part_ids.price_unit', 'vehicle_maintenance_part_ids.quantity')
    def _compute_part_price(self):
        """Compute part price"""
        for rec in self:
            rec.part_price = sum(
                part.price_unit * part.quantity for part in rec.vehicle_maintenance_part_ids)

    @api.depends('vehicle_maintenance_service_ids.service_charge')
    def _compute_service_charge(self):
        """Compute service charge"""
        for rec in self:
            rec.service_charge = sum(
                service.service_charge for service in rec.vehicle_maintenance_service_ids)

    @api.depends('sub_total', 'service_charge', 'part_price')
    def _compute_sub_total(self):
        """Compute sub total"""
        for rec in self:
            rec.sub_total = rec.service_charge + rec.part_price

    def _compute_bill_count(self):
        """Compute bill count"""
        for rec in self:
            rec.bill_count = self.env['account.move'].search_count(
                [('maintenance_request_id', '=', rec.id)])

    def action_vendor_bill_views(self):
        """Action views vendor bills"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': self.bill_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'create': False,
            }
        }
