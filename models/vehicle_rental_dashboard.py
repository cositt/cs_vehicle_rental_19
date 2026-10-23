# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class VehicleRentalDashboard(models.Model):
    """Vehicle Rental Dashboard"""
    _name = "vehicle.rental.dashboard"
    _description = __doc__

    @api.model
    def get_vehicle_rental_dashboard(self):
        """Vehicle rental dashboard data"""
        fleet_vehicles = self.env['fleet.vehicle']
        vehicle_contract = self.env['vehicle.contract']
        rental_invoices = self.env['account.move']

        total_vehicle = fleet_vehicles.search_count([])
        available_vehicle = fleet_vehicles.search_count([('status', '=', 'available')])
        under_maintenance_vehicle = fleet_vehicles.search_count([('status', '=', 'in_maintenance')])

        draft_vehicle = vehicle_contract.search_count([])
        in_progress_vehicle = vehicle_contract.search_count([('status', '=', 'b_in_progress')])
        return_contract = vehicle_contract.search_count([('status', '=', 'c_return')])
        cancel_contract = vehicle_contract.search_count([('status', '=', 'd_cancel')])
        domains = self._dashboard_domains()
        customers = self.env['res.partner'].search_count(domains['customers'])
        customer_invoice = rental_invoices.search_count(domains['customer_invoice'])
        pending_invoices = rental_invoices.search_count(domains['pending_invoices'])

        data = {
            'total_vehicle': total_vehicle,
            'available_vehicle': available_vehicle,
            'under_maintenance_vehicle': under_maintenance_vehicle,
            'draft_vehicle': draft_vehicle,
            'in_progress_vehicle': in_progress_vehicle,
            'return_contract': return_contract,
            'cancel_contract': cancel_contract,
            'customers': customers,
            'customer_invoice': customer_invoice,
            'pending_invoices': pending_invoices,
            'rent_duration': self.get_rent_contract(),
            'rent_invoice_month': self.get_rent_invoice_month(),
            'domains': domains,
        }
        return data

    def _dashboard_domains(self):
        """Domains of the cards, shared with the lists they open"""
        renters = self.env['vehicle.contract'].search([]).customer_id
        rental_invoices = [('vehicle_contract_id', '!=', False), ('move_type', '=', 'out_invoice')]
        return {
            'customers': [('id', 'in', renters.ids)],
            'customer_invoice': rental_invoices + [('state', '!=', 'cancel')],
            'pending_invoices': rental_invoices + [
                ('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'partial'))],
        }

    def get_rent_contract(self):
        """Return rental contract"""
        contract_data = []
        vehicle_contracts = self.env['vehicle.contract'].search([('status', '=', 'b_in_progress')])
        for contract in vehicle_contracts:
            contract_data.append({
                'name': contract.reference_no,
                'start_date': str(contract.start_date),
                'end_date': str(contract.end_date),
            })
        return contract_data

    def get_rent_invoice_month(self):
        """Rental income by month of this year: posted invoices less refunds,
        without VAT and without deposits (they are owed back, not income)"""
        today = fields.Date.today()
        month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        income = [0.0] * 12
        groups = self.env['account.move.line']._read_group([
            ('move_id.vehicle_contract_id', '!=', False),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', 'in', ('income', 'income_other')),
            ('date', '>=', today.replace(month=1, day=1)),
            ('date', '<=', today.replace(month=12, day=31)),
        ], ['date:month'], ['balance:sum'])
        for month, balance in groups:
            income[month.month - 1] = -balance
        return [month_names, income]
