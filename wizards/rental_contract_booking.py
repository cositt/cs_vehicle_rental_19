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
    
    # Campos para seleccionar tarifa
    selected_category_id = fields.Many2one('fleet.vehicle.model.category', string="Vehicle Category")
    search_vehicle = fields.Char(string="Search Vehicle")
    duration_range = fields.Selection(string="Duration", selection='_get_duration_options')
    km_range = fields.Selection(string="Km Range", selection='_get_km_options')
    pricing_type = fields.Selection(string="Pricing Type", selection='_get_pricing_type_options', default='standard')
    calculated_price = fields.Float(string="Price (€/day)", compute='_compute_price', store=False)
    
    fleet_vehicle_ids = fields.Many2many('fleet.vehicle', string="Vehicle")
    # Almacenar el precio calculado en un campo normal para poder pasarlo por contexto
    stored_calculated_price = fields.Float(string="Stored Price", default=0.0)

    def _get_duration_options(self):
        """Get unique duration ranges from vehicle.pricing.rule"""
        pricing_rules = self.env['vehicle.pricing.rule'].search([('active', '=', True)])
        durations = list(set(pricing_rules.mapped('duration_range')))
        return [(d, d) for d in sorted(durations)]

    def _get_km_options(self):
        """Get unique km ranges from vehicle.pricing.rule"""
        pricing_rules = self.env['vehicle.pricing.rule'].search([('active', '=', True)])
        km_ranges = list(set(pricing_rules.mapped('km_range')))
        return [(k, k) for k in sorted(km_ranges)]

    def _get_pricing_type_options(self):
        """Get unique pricing types from vehicle.pricing.rule"""
        pricing_rules = self.env['vehicle.pricing.rule'].search([('active', '=', True)])
        types = list(set(pricing_rules.mapped('pricing_type')))
        return [(t, t) for t in sorted(types)]

    def _parse_duration_range(self, duration_str):
        """Parse duration string (e.g., '3-5d', '1-2d', '4h') to get min and max days"""
        if not duration_str:
            return 0, 0
        
        if 'h' in duration_str.lower():
            # For hours, return 1 day min/max
            return 1, 1
        elif 'd' in duration_str.lower():
            # Extract min and max from format like "3-5d"
            try:
                parts = duration_str.replace('d', '').split('-')
                min_days = int(parts[0])
                max_days = int(parts[1]) if len(parts) > 1 else min_days
                return min_days, max_days
            except:
                return 0, 0
        return 0, 0

    @api.onchange('start_date', 'duration_range')
    def _onchange_set_end_date(self):
        """Auto-fill end_date based on duration_range minimum"""
        from datetime import timedelta
        if not self.start_date or not self.duration_range:
            return
        
        min_days, max_days = self._parse_duration_range(self.duration_range)
        if min_days > 0:
            # Set end_date to start_date + min_days
            end_dt = self.start_date + timedelta(days=min_days)
            self.end_date = end_dt

    @api.depends('selected_category_id', 'duration_range', 'km_range', 'pricing_type')
    def _compute_price(self):
        """Calculate price from vehicle.pricing.rule"""
        for record in self:
            if not record.selected_category_id or not record.duration_range or not record.km_range or not record.pricing_type:
                record.calculated_price = 0.0
                continue
            
            pricing_rule = self.env['vehicle.pricing.rule'].search([
                ('vehicle_category_id', '=', record.selected_category_id.id),
                ('duration_range', '=', record.duration_range),
                ('km_range', '=', record.km_range),
                ('pricing_type', '=', record.pricing_type),
                ('active', '=', True),
            ], limit=1)
            
            if pricing_rule:
                record.calculated_price = pricing_rule.price_per_unit
            else:
                record.calculated_price = 0.0

    @api.onchange('selected_category_id', 'start_date', 'end_date', 'search_vehicle', 'company_id', 'duration_range', 'km_range', 'pricing_type')
    def _onchange_available_vehicle(self):
        """Update available vehicles based on category, dates, search and filters"""
        if not self.selected_category_id or not self.start_date or not self.end_date:
            self.fleet_vehicle_ids = False
            return
        
        # 1. Buscar contratos ocupados
        occupied_contracts = self.env['vehicle.contract'].search([
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('status', 'in', ['b_in_progress', 'c_return']),
            ('vehicle_id.company_id', '=', self.company_id.id),
        ])
        occupied_vehicle_ids = occupied_contracts.mapped('vehicle_id').ids
        
        # 2. Buscar contratos reservados (a_draft)
        reserved_contracts = self.env['vehicle.contract'].search([
            ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date),
            ('status', '=', 'a_draft'),
            ('vehicle_id', '!=', False),
            ('vehicle_id.company_id', '=', self.company_id.id),
        ])
        reserved_vehicle_ids = reserved_contracts.mapped('vehicle_id').ids
        
        # 3. Dominio base
        domain = [
            ('status', '=', 'available'),
            ('company_id', '=', self.company_id.id),
            '|',
            ('category_id', '=', self.selected_category_id.id),
            ('model_id.category_id', '=', self.selected_category_id.id),
            ('id', 'not in', occupied_vehicle_ids + reserved_vehicle_ids),
        ]
        
        # 4. Filtro de búsqueda
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

    def action_create_contract_with_vehicle(self, vehicle_id):
        """Create vehicle contract with specific vehicle from list button"""
        self.ensure_one()
        
        vehicle = self.env['fleet.vehicle'].browse(vehicle_id)
        if not vehicle or not vehicle.exists():
            from odoo.exceptions import UserError
            raise UserError("El vehículo no existe.")
        
        # Create contract with wizard data including calculated price
        contract_data = {
            'vehicle_id': vehicle.id,
            'driver_id': vehicle.driver_id.id if vehicle.driver_id else False,
            'last_odometer': vehicle.odometer,
            'odometer_unit': vehicle.odometer_unit,
            'model_year': vehicle.model_year,
            'transmission': vehicle.transmission,
            'fuel_type': vehicle.fuel_type,
            'license_plate': vehicle.license_plate,
            'customer_id': self.customer_id.id,
            'customer_phone': self.customer_id.phone,
            'customer_email': self.customer_id.email,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'company_id': self.company_id.id,
            'rent': self.calculated_price,  # Pass the calculated price directly
            'rent_type': 'days',
            'pricing_type': self.pricing_type,
        }
        
        vehicle_contract = self.env['vehicle.contract'].create(contract_data)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Contract',
            'res_model': 'vehicle.contract',
            'res_id': vehicle_contract.id,
            'view_mode': 'form',
            'target': 'current'
        }
