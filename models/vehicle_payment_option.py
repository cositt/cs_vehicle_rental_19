# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import UserError


class VehiclePaymentOption(models.Model):
    """Vehicle Payment Option"""
    _name = 'vehicle.payment.option'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True, translate=True)
    ref = fields.Char(string="Reference")
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
        """Crea cuota con TODOS los conceptos: alquiler, seguro, depósito, servicios y cargos"""
        tax = []
        invoice_lines = []
        
        for rec in self.vehicle_contract_id.tax_ids:
            tax.append(rec.id)
        
        for rec in self:
            if rec.payment_amount == 0:
                raise UserError(_(
                    'La cuota "%s" tiene el importe a cero. Indique el importe a '
                    'cobrar antes de generar la factura.',
                    rec.name or _('sin nombre'),
                ))
            
            contract = self.vehicle_contract_id
            
            # ═══════════════════════════════════════════
            # LÍNEA 1: ALQUILER DEL VEHÍCULO
            # ═══════════════════════════════════════════
            payment_details = {
                'product_id': self.invoice_item_id.id,
                'name': self.name,
                'quantity': 1,
                'price_unit': self.payment_amount,
                'tax_ids': tax,
            }
            invoice_lines.append((0, 0, payment_details))
            
            # ═══════════════════════════════════════════
            # LÍNEA 2: SEGURO (OBLIGATORIO)
            # ═══════════════════════════════════════════
            import logging
            _logger = logging.getLogger(__name__)
            
            if (contract.insurance_type and 
                contract.insurance_price_per_day and 
                contract.insurance_price_per_day > 0):
                
                insurance_name = "Seguro Básico - Franquicia 300€" if contract.insurance_type == 'basic' else "Seguro Sin Franquicia"
                if contract.driver_special:
                    insurance_name += " (Conductor Especial)"
                
                insurance_line = {
                    'product_id': contract.insurance_product_id.id if contract.insurance_product_id else False,
                    'name': insurance_name,
                    'quantity': contract.total_days if contract.total_days else 1,
                    'price_unit': contract.insurance_price_per_day,
                    'tax_ids': [(6, 0, contract.insurance_product_id.taxes_id.ids)] if contract.insurance_product_id and contract.insurance_product_id.taxes_id else [],
                }
                invoice_lines.append((0, 0, insurance_line))
            
            # ═══════════════════════════════════════════
            # LÍNEA 3: DEPÓSITO DE SEGURIDAD (NUEVO)
            # ═══════════════════════════════════════════
            # Usar calculated_deposit si use_deposit_from_rule=True, sino usar deposit manual
            deposit_amount = 0
            if contract.use_deposit_from_rule and contract.calculated_deposit > 0:
                # Depósito automático desde regla
                deposit_amount = contract.calculated_deposit
            elif not contract.use_deposit_from_rule and contract.if_any_deposit and contract.deposit > 0:
                # Depósito manual ingresado por usuario
                deposit_amount = contract.deposit
            
            if deposit_amount > 0:
                deposit_line = {
                    'product_id': self.env.ref('vehicle_rental.vehicle_rent_deposit').id,
                    'name': f"Depósito de Seguridad - {contract.reference_no}",
                    'quantity': 1,
                    'price_unit': deposit_amount,
                    'tax_ids': tax,
                }
                invoice_lines.append((0, 0, deposit_line))
                _logger.info(f"CUOTA: Depósito {deposit_amount}€ agregado a cuota {rec.name} (automático: {contract.use_deposit_from_rule})")
            
            # ═══════════════════════════════════════════
            # LÍNEA 4: KM EXTRA (FLEXIRENT) (NUEVO)
            # ═══════════════════════════════════════════
            if contract.extra_km_cost and contract.extra_km_cost > 0:
                extra_km_product = self.env.ref('vehicle_rental.product_extra_km_flexirent', raise_if_not_found=False)
                if not extra_km_product:
                    extra_km_product = self.env.ref('vehicle_rental.vehicle_rent_extra_charge', raise_if_not_found=False)
                
                if extra_km_product:
                    extra_km_line = {
                        'product_id': extra_km_product.id,
                        'name': f"Kilómetros Extra - FLEXIRENT\n{contract.extra_km_used:.0f} km × {contract.extra_km_price_unit:.2f}€",
                        'quantity': contract.extra_km_used,
                        'price_unit': contract.extra_km_price_unit,
                        'tax_ids': [(6, 0, extra_km_product.taxes_id.ids)],
                    }
                    invoice_lines.append((0, 0, extra_km_line))
                    _logger.info(f"CUOTA: Km Extra {contract.extra_km_cost}€ agregado a cuota {rec.name}")
            
            # ═══════════════════════════════════════════
            # LÍNEA 5: SERVICIOS EXTRAS (NUEVO)
            # ═══════════════════════════════════════════
            for extra_service in contract.extra_service_ids:
                if extra_service.product_id:
                    service_line = {
                        'product_id': extra_service.product_id.id,
                        'name': extra_service.description or extra_service.product_id.name,
                        'quantity': extra_service.product_qty,
                        'price_unit': extra_service.amount,
                        'tax_ids': tax,
                    }
                    invoice_lines.append((0, 0, service_line))
                    _logger.info(f"CUOTA: Servicio extra {extra_service.amount}€ agregado a cuota {rec.name}")
            
            # ═══════════════════════════════════════════
            # LÍNEA 6: CARGOS EXTRAS (NUEVO)
            # ═══════════════════════════════════════════
            if contract.total_extra_charges and contract.total_extra_charges > 0:
                extra_charges_line = {
                    'product_id': self.env.ref('vehicle_rental.vehicle_rent_extra_charge').id,
                    'name': 'Cargos Extras',
                    'quantity': 1,
                    'price_unit': contract.total_extra_charges,
                    'tax_ids': tax,
                }
                invoice_lines.append((0, 0, extra_charges_line))
                _logger.info(f"CUOTA: Cargos extras {contract.total_extra_charges}€ agregado a cuota {rec.name}")
        
        # ═══════════════════════════════════════════
        # CREAR FACTURA CON TODAS LAS LÍNEAS
        # ═══════════════════════════════════════════
        data = {
            'partner_id': self.vehicle_contract_id.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.payment_date,
            'invoice_line_ids': invoice_lines,
            'vehicle_contract_id': self.vehicle_contract_id.id
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        
        # Guardar la referencia a la factura en la cuota
        # IMPORTANTE: También actualizar payment_amount con el total de la factura
        # para que se refleje correctamente (alquiler + seguro + depósito + extras)
        self.write({
            'invoice_id': invoice_id.id,
            'payment_amount': invoice_id.amount_total  # ← Actualizar con el total de la factura
        })
        
        _logger.info(f"CUOTA: Factura creada {invoice_id.name} - Total: {invoice_id.amount_total}€")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

