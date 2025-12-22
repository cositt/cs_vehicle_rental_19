# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models, _


class MaintenanceRequestBill(models.TransientModel):
    """Maintenance Request Bill"""
    _name = 'maintenance.request.bill'
    _description = __doc__

    vendor_id = fields.Many2one('res.partner', string="Vendor")
    maintenance_request_id = fields.Many2one('maintenance.request',
                                             string="Maintenance Request")

    @api.model
    def default_get(self, fields_list):
        """Maintenance request"""
        res = super().default_get(fields_list)
        active_id = self._context.get('active_id')
        if active_id:
            res['maintenance_request_id'] = active_id
        return res

    def action_create_vendor_bill(self):
        """Action create vendor bill"""
        invoice_lines = []
        sequence_number = 1
        # Add Vehicle Maintenance Parts to invoice lines
        if self.maintenance_request_id.vehicle_maintenance_part_ids:
            invoice_lines.append((0, 0, {
                'display_type': 'line_section',
                'name': "Vehicle Maintenance Parts",
                'sequence': sequence_number,
            }))
            sequence_number += 1
            for record in self.maintenance_request_id.vehicle_maintenance_part_ids:
                part_record = {
                    'product_id': record.product_id.id,
                    'name': record.product_id.name,
                    'quantity': record.quantity,
                    'price_unit': record.price_unit,
                    'sequence': sequence_number,
                }
                sequence_number += 1
                invoice_lines.append((0, 0, part_record))
        # Add Vehicle Maintenance Services to invoice lines
        if self.maintenance_request_id.vehicle_maintenance_service_ids:
            invoice_lines.append((0, 0, {
                'display_type': 'line_section',
                'name': "Vehicle Maintenance Services",
                'sequence': sequence_number,
            }))
            sequence_number += 1
            for rec in self.maintenance_request_id.vehicle_maintenance_service_ids:
                service_record = {
                    'product_id': rec.product_id.id,
                    'name': rec.product_id.name,
                    'quantity': 1,
                    'price_unit': rec.service_charge,
                    'sequence': sequence_number,
                }
                sequence_number += 1
                invoice_lines.append((0, 0, service_record))

        order_data = {
            'partner_id': self.vendor_id.id,
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'maintenance_request_id': self.maintenance_request_id.id,
            'fleet_vehicle_id': self.maintenance_request_id.fleet_vehicle_id.id,
        }
        bill_id = self.env['account.move'].create(order_data)
        self.maintenance_request_id.bill_id = bill_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bill'),
            'res_model': 'account.move',
            'res_id': bill_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
