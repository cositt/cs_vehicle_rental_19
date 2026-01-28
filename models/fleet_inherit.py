# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from ..utils import _display_rental_notification


class FleetVehicle(models.Model):
    """Fleet Vehicle"""
    _inherit = 'fleet.vehicle'
    _description = __doc__

    rent_day = fields.Monetary(string="Alquiler por Día")
    rent_week = fields.Monetary(string="Rent per Week")
    rent_month = fields.Monetary(string="Rent per Month")
    rent_km = fields.Monetary(string="Rent per Kilometer")
    rent_mi = fields.Monetary(string="Rent per Mile")

    rent_hour = fields.Monetary(string="Rent per Hour")
    rent_year = fields.Monetary(string="Rent per Year")

    extra_charge_day = fields.Monetary(string="Charge per Day")
    extra_charge_week = fields.Monetary(string="Charge per Week")
    extra_charge_month = fields.Monetary(string="Charge per Month")
    extra_charge_km = fields.Monetary(string="Charge per Kilometer")
    extra_charge_mi = fields.Monetary(string="Charge per Mile")

    extra_charge_hour = fields.Monetary(string="Charge per Hour")
    extra_charge_year = fields.Monetary(string="Charge per Year")

    rental_contract_count = fields.Integer(compute='_compute_total_rental_contract',
                                           string=" Contracts")
    status = fields.Selection(
        [('available', 'Operational'), ('in_maintenance', 'Under Maintenance')],
        string="Status", default="available")
    maintenance_schedule_id = fields.Many2one('maintenance.schedule', string="Horario de Mantenimiento")
    maintenance_request_id = fields.Many2one('maintenance.request', string="Solicitud de Mantenimiento")
    maintenance_request_count = fields.Integer(compute='_compute_maintenance_request_count')
    maintenance_bill_count = fields.Integer(compute='_compute_maintenance_bill_count')

    # Vehicle Expanses
    is_any_vehicle_expense = fields.Boolean(string="¿Hay Gastos del Vehículo?")
    fleet_expense_ids = fields.One2many(comodel_name='hr.expense', inverse_name='fleet_vehicle_id')

    def available_to_in_maintenance(self):
        """Mark vehicle as 'In Maintenance' if no active contract is in progress."""
        for rec in self:
            existing_contract = self.env['vehicle.contract'].search(
                [('vehicle_id', '=', rec.id), ('status', '=', 'b_in_progress')]
            )
            if existing_contract:
                message = _display_rental_notification(
                    message="""Ya existe un contrato en progreso para este vehículo. Por favor, asegúrese
                     de que el coche sea devuelto antes de cambiar el estado a 'En Mantenimiento'.""",
                    message_type='warning')
                return message
            rec.status = 'in_maintenance'
        return None  # Ensure consistent return values

    def in_maintenance_to_available(self):
        """In maintenance to available"""
        self.status = 'available'

    def _compute_total_rental_contract(self):
        """Total rental contract"""
        for rec in self:
            rec.rental_contract_count = self.env['vehicle.contract'].search_count(
                [('vehicle_id', '=', rec.id)])

    def action_rental_contract_view(self):
        """Action rental contract view"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rental Contracts'),
            'res_model': 'vehicle.contract',
            'domain': [('vehicle_id', '=', self.id)],
            'view_mode': 'list,form,kanban,calendar,pivot,activity',
            'target': 'current',
            'context': {
                'create': False,
            }
        }

    def action_create_book_contract(self):
        """Action create book contract"""
        context = self._context
        customer = self.env['res.partner'].browse(context.get('customer_id'))
        data = {
            'vehicle_id': self.id,
            'driver_id': self.driver_id.id,
            'last_odometer': self.odometer,
            'odometer_unit': self.odometer_unit,
            'model_year': self.model_year,
            'transmission': self.transmission,
            'fuel_type': self.fuel_type,
            'license_plate': self.license_plate,
            'customer_id': customer.id,
            'customer_phone': customer.phone,
            'customer_email': customer.email,
            'start_date': context.get('start_date'),
            'end_date': context.get('end_date'),
            'company_id': context.get('company_id'),
            'rent': context.get('calculated_price', 0.0),
            'rent_type': 'days',
            'pricing_type': context.get('pricing_type'),
        }
        vehicle_contract = self.env['vehicle.contract'].create(data)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vehicle Contract'),
            'res_model': 'vehicle.contract',
            'res_id': vehicle_contract.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def return_action_to_open(self):
        """Return action to open"""
        self.ensure_one()
        context = self.env.context
        xml_id = context.get('xml_id')
        if not xml_id:
            return False
        if xml_id == 'fleet_vehicle_log_contract_action':
            return self.action_maintenances_request_view()
        action = self.env.ref(f'fleet.{xml_id}').sudo().read()[
            0]  # Use env.ref() instead of _for_xml_id
        action.update(
            context=dict(context, default_vehicle_id=self.id, group_by=False),
            domain=[('vehicle_id', '=', self.id)]
        )
        return action

    def action_create_maintenance_request(self):
        """Action create maintenance request"""
        for vehicle in self:
            if not vehicle.maintenance_schedule_id:
                message = _display_rental_notification(
                    message="""Por favor, elija un horario de mantenimiento de las opciones disponibles.""",
                    message_type='warning')
                return message
            today_date = fields.Date.today()
            vehicle_brand = vehicle.model_id.brand_id.name
            vehicle_model = vehicle.model_id.name
            license_plate = vehicle.license_plate
            maintenance_days = vehicle.maintenance_schedule_id.maintenance_days
            # Retrieve the last maintenance request's upcoming maintenance date
            last_maintenance_request = self.env['maintenance.request'].search(
                [('fleet_vehicle_id', '=', vehicle.id)], order='upcoming_maintenance_date desc',
                limit=1
            )
            last_request_date = last_maintenance_request.upcoming_maintenance_date \
                if last_maintenance_request else today_date
            # Calculate the next maintenance date based on the
            # last request date and maintenance schedule
            upcoming_maintenance_date = last_request_date + relativedelta(days=maintenance_days)
            data = {
                'name':
                    f"Solicitud de Mantenimiento para - {vehicle_brand}/{vehicle_model}/{license_plate}",
                'request_date': last_request_date,
                # Set request_date to the last request's upcoming_maintenance_date
                'description': 'Mantenimiento programado',
                'maintenance_schedule_id': vehicle.maintenance_schedule_id.id,
                'upcoming_maintenance_date': upcoming_maintenance_date,
                'fleet_vehicle_id': vehicle.id,
            }
            maintenance_request = self.env['maintenance.request'].create(data)
            vehicle.maintenance_request_id = maintenance_request.id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Maintenance Request'),
                'res_model': 'maintenance.request',
                'res_id': maintenance_request.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return True

    def _compute_maintenance_request_count(self):
        """Compute maintenance request count"""
        for rec in self:
            rec.maintenance_request_count = self.env['maintenance.request'].search_count(
                [('fleet_vehicle_id', '=', rec.id)])

    def action_maintenances_request_view(self):
        """Action maintenance request view"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Requests'),
            'res_model': 'maintenance.request',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('fleet_vehicle_id', '=', self.id)],
            'context': {
                'default_fleet_vehicle_id': self.id,
                'create': False,
            },
        }

    def _compute_maintenance_bill_count(self):
        """Compute maintenance bill count"""
        for rec in self:
            rec.maintenance_bill_count = self.env['account.move'].search_count(
                [('fleet_vehicle_id', '=', rec.id)])

    def action_maintenance_bill_views(self):
        """Action maintenance bill views"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Bills'),
            'res_model': 'account.move',
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'domain': [('fleet_vehicle_id', '=', self.id)],
            'context': {
                'create': False,
            }
        }

    @api.constrains('driver_id')
    def _check_driver_is_employees(self):
        """Check driver is also employee"""
        for record in self:
            if record.driver_id and not record.driver_id.employee_ids:
                raise ValidationError(_(
                    "The selected driver must be one of the allowed employees."))


class FleetVehicleLogContract(models.Model):
    """Fleet Vehicle Log Contract"""
    _inherit = 'fleet.vehicle.log.contract'
    _description = __doc__

    license_plate = fields.Char(string="License Plate")
