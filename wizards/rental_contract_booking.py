# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models
from datetime import datetime


class RentalContractBooking(models.TransientModel):
    """Rental contract booking"""
    _name = 'rental.contract.booking'
    _description = "Rental Contract Booking"

    customer_id = fields.Many2one("res.partner")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    start_date = fields.Datetime(string="Pick-up Date")
    end_date = fields.Datetime(string="Drop-off Date")
    fleet_vehicle_ids = fields.Many2many('fleet.vehicle', string="Vehicle")

    @api.onchange('start_date', 'end_date')
    def _onchange_available_vehicle(self):
        """Onchange available vehicles"""
        if self.start_date and self.end_date:
            # 1. Buscar contratos ocupados (b_in_progress, c_return) en esas fechas
            occupied_contracts = self.env['vehicle.contract'].search([
                ('start_date', '<=', self.end_date),
                ('end_date', '>=', self.start_date),
                ('status', 'in', ['b_in_progress', 'c_return']),
                ('vehicle_id.company_id', '=', self.company_id.id),
            ])
            occupied_vehicle_ids = occupied_contracts.mapped('vehicle_id').ids
            
            # 2. Buscar contratos reservados (a_draft con vehicle_id) en esas fechas
            reserved_contracts = self.env['vehicle.contract'].search([
                ('start_date', '<=', self.end_date),
                ('end_date', '>=', self.start_date),
                ('status', '=', 'a_draft'),
                ('vehicle_id', '!=', False),
                ('vehicle_id.company_id', '=', self.company_id.id),
            ])
            reserved_vehicle_ids = reserved_contracts.mapped('vehicle_id').ids
            
            # 3. Filtrar vehículos disponibles
            available_vehicles = self.env['fleet.vehicle'].search([
                ('status', '=', 'available'),
                ('company_id', '=', self.company_id.id),
                ('id', 'not in', occupied_vehicle_ids + reserved_vehicle_ids),
            ])
            self.fleet_vehicle_ids = [(6, 0, available_vehicles.ids)]
