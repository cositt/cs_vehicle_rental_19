# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models
from datetime import datetime, time


def parse_time_str(time_str, default=None):
    """Parse time string HH:MM to time object"""
    if not time_str:
        return default or time.min
    try:
        h, m = map(int, time_str.split(':'))
        return time(h, m)
    except:
        return default or time.min


class LeadRentalContract(models.TransientModel):
    """Lead Rental Contract"""
    _name = 'lead.rental.contract'
    _description = __doc__

    crm_lead_id = fields.Many2one('crm.lead', string="Lead")
    partner_id = fields.Many2one("res.partner", string="Customer")
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle",
                                 domain="[('status', '=', 'available')]")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")

    @api.model
    def default_get(self, field_names):
        """Set default values from crm lead"""
        res = super().default_get(field_names)
        active_id = self.env.context.get('active_id')
        
        if active_id:
            lead = self.env['crm.lead'].browse(active_id)
            if lead.exists():
                # Establecer el lead
                res['crm_lead_id'] = lead.id
                
                # Cliente
                if lead.partner_id:
                    res['partner_id'] = lead.partner_id.id
                
                # Vehículo - buscar por categoría si no hay vehículo específico
                if hasattr(lead, 'vehicle_id') and lead.vehicle_id:
                    res['vehicle_id'] = lead.vehicle_id.id
                elif hasattr(lead, 'selected_category_id') and lead.selected_category_id:
                    vehicle = self.env['fleet.vehicle'].search([
                        ('model_id.category_id', '=', lead.selected_category_id.id),
                        ('status', '=', 'available')
                    ], limit=1)
                    if vehicle:
                        res['vehicle_id'] = vehicle.id
                
                # Obtener horas del lead
                start_time_obj = parse_time_str(getattr(lead, 'start_time', None), time(9, 0))
                end_time_obj = parse_time_str(getattr(lead, 'end_time', None), time(9, 0))
                
                # Fechas - convertir de Date a Datetime usando las horas del lead
                if hasattr(lead, 'start_date') and lead.start_date:
                    if isinstance(lead.start_date, str):
                        date_obj = datetime.strptime(lead.start_date, '%Y-%m-%d').date()
                        res['start_date'] = datetime.combine(date_obj, start_time_obj)
                    else:
                        res['start_date'] = datetime.combine(lead.start_date, start_time_obj)
                
                if hasattr(lead, 'end_date') and lead.end_date:
                    if isinstance(lead.end_date, str):
                        date_obj = datetime.strptime(lead.end_date, '%Y-%m-%d').date()
                        res['end_date'] = datetime.combine(date_obj, end_time_obj)
                    else:
                        res['end_date'] = datetime.combine(lead.end_date, end_time_obj)
        
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to fill data from lead if not provided"""
        records = super().create(vals_list)
        for record in records:
            if record.crm_lead_id and (not record.partner_id or not record.vehicle_id or not record.start_date or not record.end_date):
                lead = record.crm_lead_id
                start_time_obj = parse_time_str(getattr(lead, 'start_time', None), time(9, 0))
                end_time_obj = parse_time_str(getattr(lead, 'end_time', None), time(9, 0))
                
                if not record.partner_id and lead.partner_id:
                    record.partner_id = lead.partner_id
                
                if not record.vehicle_id and lead.vehicle_id:
                    record.vehicle_id = lead.vehicle_id
                
                if not record.start_date and lead.start_date:
                    record.start_date = datetime.combine(lead.start_date, start_time_obj)
                
                if not record.end_date and lead.end_date:
                    record.end_date = datetime.combine(lead.end_date, end_time_obj)
        
        return records
    
    @api.onchange('crm_lead_id')
    def _onchange_crm_lead_id(self):
        """Update fields when lead changes"""
        if self.crm_lead_id:
            lead = self.crm_lead_id
            start_time_obj = parse_time_str(getattr(lead, 'start_time', None), time(9, 0))
            end_time_obj = parse_time_str(getattr(lead, 'end_time', None), time(9, 0))
            
            start_datetime = False
            end_datetime = False
            if lead.start_date:
                start_datetime = datetime.combine(lead.start_date, start_time_obj)
            if lead.end_date:
                end_datetime = datetime.combine(lead.end_date, end_time_obj)
            
            self.partner_id = lead.partner_id if lead.partner_id else False
            
            if lead.vehicle_id:
                self.vehicle_id = lead.vehicle_id
            elif hasattr(lead, 'selected_category_id') and lead.selected_category_id:
                vehicle = self.env['fleet.vehicle'].search([
                    ('model_id.category_id', '=', lead.selected_category_id.id),
                    ('status', '=', 'available')
                ], limit=1)
                self.vehicle_id = vehicle if vehicle else False
            else:
                self.vehicle_id = False
            self.start_date = start_datetime
            self.end_date = end_datetime

    def action_create_rental_contract(self):
        """Create rental contract from lead"""
        # Obtener ubicación del lead
        location = getattr(self.crm_lead_id, 'location', '') or ''
        
        # Buscar provincia/estado por nombre de ubicación
        state_id = False
        if location:
            state = self.env['res.country.state'].search([
                ('country_id.code', '=', 'ES'),
                ('name', 'ilike', location)
            ], limit=1)
            if state:
                state_id = state.id
        
        # España por defecto
        spain = self.env['res.country'].search([('code', '=', 'ES')], limit=1)
        
        contract_vals = {
            'crm_lead_id': self.crm_lead_id.id,
            'customer_id': self.partner_id.id,
            'customer_phone': self.partner_id.phone,
            'customer_email': self.partner_id.email,
            'vehicle_id': self.vehicle_id.id,
            'model_year': self.vehicle_id.model_year,
            'transmission': self.vehicle_id.transmission,
            'fuel_type': self.vehicle_id.fuel_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'pick_up_city': location,
            'drop_off_city': location,
            'pick_up_state_id': state_id,
            'pick_up_country_id': spain.id if spain else False,
            'drop_off_state_id': state_id,
            'drop_off_country_id': spain.id if spain else False,
            'rent': booking_data.get('selected_price', 0),
        }
        
        contract = self.env['vehicle.contract'].create(contract_vals)
        self.crm_lead_id.contract_id = contract.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.contract',
            'res_id': contract.id,
            'view_mode': 'form',
            'target': 'current',
        }
