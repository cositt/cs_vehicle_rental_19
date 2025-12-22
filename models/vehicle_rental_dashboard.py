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
        customers = self.env['res.partner'].search_count([])

        customer_invoice = rental_invoices.search_count(
            [('vehicle_contract_id', '!=', False), ('move_type', '=', 'out_invoice')])
        pending_invoices = rental_invoices.search_count(
            [('vehicle_contract_id', '!=', False), ('payment_state', '!=', 'paid'),
             ('move_type', '=', 'out_invoice')])

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

        }
        return data

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
        """Rental contract invoice by month"""
        year = fields.Date.today().year
        data_dict = {'Enero': 0,
                     'Febrero': 0,
                     'Marzo': 0,
                     'Abril': 0,
                     'Mayo': 0,
                     'Junio': 0,
                     'Julio': 0,
                     'Agosto': 0,
                     'Septiembre': 0,
                     'Octubre': 0,
                     'Noviembre': 0,
                     'Diciembre': 0,
                     }

        invoice_id = self.env['account.move'].search([
            ('vehicle_contract_id', '!=', False),
            ('move_type', '=', 'out_invoice')
        ])
        for data in invoice_id:
            if data.invoice_date and data.invoice_date.year == year:
                if data.vehicle_contract_id.status == 'c_return':
                    month_num = data.invoice_date.month
                    month_names = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
                    month = month_names[month_num - 1]
                    data_dict[month] = data_dict.get(month, 0) + data.amount_total
        return [list(data_dict.keys()), list(data_dict.values())]
