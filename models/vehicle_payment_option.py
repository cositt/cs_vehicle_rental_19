# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class VehiclePaymentOption(models.Model):
    """Vehicle Payment Option"""
    _name = 'vehicle.payment.option'
    _description = __doc__
    _rec_name = 'name'
    _order = 'payment_date, id'

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
        """Factura de la cuota: su parte del alquiler y del seguro.

        Lo que se cobra una sola vez (depósito, servicios y cargos extra) va en
        la primera cuota; los km extra, en la última.
        """
        invoices = self.env['account.move']
        for rec in self:
            invoices |= rec._create_invoice()
        if len(invoices) != 1:
            return True
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoices.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_('La cuota "%s" ya está facturada (%s).',
                              self.name, self.invoice_id.name))
        if self.payment_amount == 0:
            raise UserError(_(
                'La cuota "%s" tiene el importe a cero. Indique el importe a '
                'cobrar antes de generar la factura.',
                self.name or _('sin nombre'),
            ))
        contract = self.vehicle_contract_id
        schedule = contract.vehicle_payment_option_ids.sorted(lambda o: (o.payment_date, o.id))
        is_first = self == schedule[:1]
        is_last = self == schedule[-1:]
        # Parte del alquiler que cubre esta cuota, para repartir el seguro igual
        share = (self.payment_amount / contract.total_vehicle_rent
                 if contract.total_vehicle_rent else 1.0)
        tax = contract.tax_ids.ids
        invoice_lines = [(0, 0, {
            'product_id': self.invoice_item_id.id,
            'name': self.name,
            'quantity': 1,
            'price_unit': self.payment_amount,
            'tax_ids': tax,
        })]
        invoice_lines += self._insurance_lines(contract, share)
        if is_first:
            invoice_lines += self._one_off_lines(contract, tax)
        if is_last:
            invoice_lines += self._extra_km_lines(contract)

        invoice = self.env['account.move'].sudo().create({
            'partner_id': contract.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.payment_date,
            'invoice_line_ids': invoice_lines,
            'vehicle_contract_id': contract.id,
        })
        # La cuota refleja el total facturado (alquiler + seguro + extras)
        self.write({'invoice_id': invoice.id, 'payment_amount': invoice.amount_total})
        _logger.info("CUOTA: factura %s de %s - total %s", invoice.name, self.name,
                     invoice.amount_total)
        return invoice

    def _insurance_lines(self, contract, share):
        if not (contract.insurance_type and contract.insurance_price_per_day > 0):
            return []
        name = ("Seguro Básico - Franquicia 750 € + IVA" if contract.insurance_type == 'basic'
                else "Seguro Sin Franquicia")
        if contract.driver_special:
            name += " (Conductor Especial)"
        product = contract.insurance_product_id
        return [(0, 0, {
            'product_id': product.id or False,
            'name': name,
            'quantity': round((contract.total_days or 1) * share, 2),
            'price_unit': contract.insurance_price_per_day,
            'tax_ids': [(6, 0, contract.tax_ids.ids)],
        })]

    def _one_off_lines(self, contract, tax):
        lines = []
        if contract.use_deposit_from_rule and contract.calculated_deposit > 0:
            deposit = contract.calculated_deposit
        elif not contract.use_deposit_from_rule and contract.if_any_deposit and contract.deposit > 0:
            deposit = contract.deposit
        else:
            deposit = 0
        if deposit > 0:
            lines.append((0, 0, {
                'product_id': self.env.ref('vehicle_rental.vehicle_rent_deposit').id,
                'name': f"Depósito de Seguridad - {contract.reference_no}",
                'quantity': 1,
                'price_unit': deposit,
                # La fianza no es una venta: sin IVA
                'tax_ids': [],
            }))
        for extra_service in contract.extra_service_ids.filtered('product_id'):
            lines.append((0, 0, {
                'product_id': extra_service.product_id.id,
                'name': extra_service.description or extra_service.product_id.name,
                'quantity': extra_service.product_qty,
                'price_unit': extra_service.amount,
                'tax_ids': [(6, 0, contract._extra_service_taxes(extra_service.product_id).ids)],
            }))
        if contract.total_extra_charges > 0:
            lines.append((0, 0, {
                'product_id': self.env.ref('vehicle_rental.vehicle_rent_extra_charge').id,
                'name': 'Cargos Extras',
                'quantity': 1,
                'price_unit': contract.total_extra_charges,
                'tax_ids': tax,
            }))
        return lines

    def _extra_km_lines(self, contract):
        if not contract.extra_km_cost > 0:
            return []
        product = (self.env.ref('vehicle_rental.product_extra_km_flexirent', raise_if_not_found=False)
                   or self.env.ref('vehicle_rental.vehicle_rent_extra_charge', raise_if_not_found=False))
        if not product:
            return []
        return [(0, 0, {
            'product_id': product.id,
            'name': f"Kilómetros Extra - FLEXIRENT\n{contract.extra_km_used:.0f} km × "
                    f"{contract.extra_km_price_unit:.2f}€",
            'quantity': contract.extra_km_used,
            'price_unit': contract.extra_km_price_unit,
            'tax_ids': [(6, 0, contract.tax_ids.ids)],
        })]
