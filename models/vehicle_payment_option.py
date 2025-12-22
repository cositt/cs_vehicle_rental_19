# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from ..utils import _display_rental_notification


class VehiclePaymentOption(models.Model):
    """Vehicle Payment Option"""
    _name = 'vehicle.payment.option'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True, translate=True)
    payment_date = fields.Date(string="Payment Date", required=True)
    payment_amount = fields.Monetary(string="Payment Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    invoice_item_id = fields.Many2one('product.product', string="Invoice Item")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    payment_state = fields.Selection(related="invoice_id.payment_state",
                                     string="Payment State")
    vehicle_contract_id = fields.Many2one('vehicle.contract', ondelete='cascade')

    def action_create_payment_invoice(self):
        """Action create payment invoice"""
        tax = []
        invoice_lines = []
        for rec in self.vehicle_contract_id.tax_ids:
            tax.append(rec.id)
        for rec in self:
            if rec.payment_amount == 0:
                message = _display_rental_notification(
                    message="""Please add the proper payment amount""",
                    message_type='warning')
                return message
            
            # LÍNEA 1: Alquiler del vehículo
            payment_details = {
                'product_id': self.invoice_item_id.id,
                'name': self.name,
                'quantity': 1,
                'price_unit': self.payment_amount,
                'tax_ids': tax,
            }
            invoice_lines.append((0, 0, payment_details))
            
            # LÍNEA 2: Seguro (si está configurado)
            contract = self.vehicle_contract_id
            # Debug: verificar datos del seguro
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"DEBUG SEGURO - Tipo: {contract.insurance_type}, Precio: {contract.insurance_price_per_day}, Producto: {contract.insurance_product_id}")
            
            # Verificar si el contrato tiene seguro configurado
            if contract.insurance_type and contract.insurance_price_per_day and contract.insurance_price_per_day > 0:
                # Determinar el nombre del seguro
                if contract.insurance_type == 'basic':
                    insurance_name = "Seguro Básico - Franquicia 300€"
                else:
                    insurance_name = "Seguro Sin Franquicia"
                
                # Agregar conductor especial si aplica
                if contract.driver_special:
                    insurance_name += " (Conductor Especial)"
                
                # Crear línea de seguro
                insurance_line = {
                    'product_id': contract.insurance_product_id.id if contract.insurance_product_id else False,
                    'name': insurance_name,
                    'quantity': contract.total_days if contract.total_days else 1,
                    'price_unit': contract.insurance_price_per_day,
                    'tax_ids': [(6, 0, contract.insurance_product_id.taxes_id.ids)] if contract.insurance_product_id and contract.insurance_product_id.taxes_id else [],
                }
                invoice_lines.append((0, 0, insurance_line))
        
        data = {
            'partner_id': self.vehicle_contract_id.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.payment_date,
            'invoice_line_ids': invoice_lines,
            'vehicle_contract_id': self.vehicle_contract_id.id
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        self.invoice_id = invoice_id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
