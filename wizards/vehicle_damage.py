# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _
from odoo.exceptions import UserError


class VehicleDamage(models.TransientModel):
    """Vehicle Damage"""
    _name = 'vehicle.damage'
    _description = __doc__

    is_any_damage = fields.Boolean(string="Any Damage")
    description = fields.Html(string="Description")
    damage_amount = fields.Monetary(string="Damage Amount")
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")

    def vehicle_damage_amount(self):
        """Action create vehicle damage invoice"""
        rec = self._context.get('active_id')
        vehicle_contract = self.env["vehicle.contract"].browse(rec)
        for rec in self:
            if not rec.damage_amount:
                raise UserError(_(
                    'Indique el importe de los daños antes de generar la factura. '
                    'Si la valoración aún no está hecha, puede facturarla más '
                    'adelante desde la ficha de la devolución.'
                ))
            vehicle_contract.write({
                'description': self.description,
                'damage_amount': self.damage_amount,
            })
            damage_amount = {
                'product_id': self.env.ref('vehicle_rental.vehicle_damage_amount').id,
                'name': vehicle_contract.vehicle_id.name,
                'quantity': 1,
                'price_unit': self.damage_amount,
            }
            invoice_lines = [(0, 0, damage_amount)]
            # Obtener journal de ventas del contrato
            sale_journal = vehicle_contract._get_sale_journal()
            data = {
                'partner_id': vehicle_contract.customer_id.id,
                'move_type': 'out_invoice',
                'journal_id': sale_journal.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'vehicle_contract_id': vehicle_contract.id
            }
            invoice_id = self.env['account.move'].sudo().create(data)
            invoice_id.action_post()
            vehicle_contract.is_invoice_done = True
            return {
                'type': 'ir.actions.act_window',
                'name': 'Invoice',
                'res_model': 'account.move',
                'res_id': invoice_id.id,
                'view_mode': 'form',
                'target': 'current'
            }
