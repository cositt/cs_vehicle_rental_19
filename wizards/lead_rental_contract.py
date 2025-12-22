# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models
from datetime import datetime, time


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
                    # Buscar un vehículo disponible de la categoría seleccionada
                    vehicle = self.env['fleet.vehicle'].search([
                        ('model_id.category_id', '=', lead.selected_category_id.id),
                        ('status', '=', 'available')
                    ], limit=1)
                    if vehicle:
                        res['vehicle_id'] = vehicle.id
                
                # Fechas - convertir de Date a Datetime
                if hasattr(lead, 'start_date') and lead.start_date:
                    if isinstance(lead.start_date, str):
                        date_obj = datetime.strptime(lead.start_date, '%Y-%m-%d').date()
                        res['start_date'] = datetime.combine(date_obj, time.min)
                    else:
                        res['start_date'] = datetime.combine(lead.start_date, time.min)
                
                if hasattr(lead, 'end_date') and lead.end_date:
                    if isinstance(lead.end_date, str):
                        date_obj = datetime.strptime(lead.end_date, '%Y-%m-%d').date()
                        res['end_date'] = datetime.combine(date_obj, time.max)
                    else:
                        res['end_date'] = datetime.combine(lead.end_date, time.max)
        
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to fill data from lead if not provided"""
        records = super().create(vals_list)
        for record in records:
            if record.crm_lead_id and (not record.partner_id or not record.vehicle_id or not record.start_date or not record.end_date):
                # Llenar datos faltantes desde el lead
                lead = record.crm_lead_id
                
                if not record.partner_id and lead.partner_id:
                    record.partner_id = lead.partner_id
                
                if not record.vehicle_id and lead.vehicle_id:
                    record.vehicle_id = lead.vehicle_id
                
                if not record.start_date and lead.start_date:
                    record.start_date = datetime.combine(lead.start_date, time.min)
                
                if not record.end_date and lead.end_date:
                    record.end_date = datetime.combine(lead.end_date, time.max)
        
        return records
    
    @api.onchange('crm_lead_id')
    def _onchange_crm_lead_id(self):
        """Update fields when lead changes"""
        if self.crm_lead_id:
            lead = self.crm_lead_id
            # Convert Date fields to Datetime
            start_datetime = False
            end_datetime = False
            if lead.start_date:
                start_datetime = datetime.combine(lead.start_date, time.min)
            if lead.end_date:
                end_datetime = datetime.combine(lead.end_date, time.max)
            
            self.partner_id = lead.partner_id if lead.partner_id else False
            
            # Buscar vehículo por categoría si no hay vehículo específico
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
        contract = self.env['vehicle.contract'].create({
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
        })
        self.crm_lead_id.contract_id = contract.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.contract',
            'res_id': contract.id,
            'view_mode': 'form',
            'target': 'current',
        }
