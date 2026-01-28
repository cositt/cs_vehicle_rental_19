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
    
    # Campos para filtro de disponibilidad (en memoria, no persistentes)
    selected_category_id = fields.Many2one('fleet.vehicle.model.category', string="Vehicle Category")
    search_vehicle = fields.Char(string="Search Vehicle")
    
    fleet_vehicle_ids = fields.Many2many('fleet.vehicle', string="Vehicle")

    @api.onchange('selected_category_id', 'start_date', 'end_date', 'search_vehicle', 'company_id')
    def _onchange_available_vehicle(self):
        """Update available vehicles based on category, dates, search and company"""
        if not self.selected_category_id or not self.start_date or not self.end_date:
            self.fleet_vehicle_ids = False
            return
        
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
        
        # 3. Base domain: categoria, compañía, status available, excluir ocupados y reservados
        domain = [
            ('status', '=', 'available'),
            ('company_id', '=', self.company_id.id),
            '|',
            ('category_id', '=', self.selected_category_id.id),
            ('model_id.category_id', '=', self.selected_category_id.id),
            ('id', 'not in', occupied_vehicle_ids + reserved_vehicle_ids),
        ]
        
        # 4. Aplicar filtro de búsqueda si existe
        if self.search_vehicle:
            search_term = self.search_vehicle.lower()
            vehicles = self.env['fleet.vehicle'].search(domain)
            vehicles = vehicles.filtered(
                lambda v: search_term in (v.name or '').lower() or 
                          search_term in (v.model_id.name or '').lower()
            )
            self.fleet_vehicle_ids = [(6, 0, vehicles.ids)]
        else:
            available_vehicles = self.env['fleet.vehicle'].search(domain)
            self.fleet_vehicle_ids = [(6, 0, available_vehicles.ids)]
