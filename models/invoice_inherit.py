# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class RentalInvoice(models.Model):
    """Rental Invoice"""
    _inherit = 'account.move'
    _description = __doc__

    vehicle_contract_id = fields.Many2one('vehicle.contract', string="Vehicle Contract")
    maintenance_request_id = fields.Many2one('maintenance.request', string="Maintenance Request")
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string="Fleet Vehicle")

    @api.model_create_multi
    def create(self, vals_list):
        """Una factura de contrato va en la compañía del contrato, no en la activa."""
        moves = self.browse()
        for vals in vals_list:
            Move = self
            if vals.get('vehicle_contract_id') and not vals.get('company_id') and not vals.get('journal_id'):
                contract = self.env['vehicle.contract'].sudo().browse(vals['vehicle_contract_id'])
                Move = self.with_company(contract.company_id)
            moves |= super(RentalInvoice, Move).create([vals])
        return moves.with_env(self.env)

    def write(self, vals):
        """Notificar al contrato cuando la factura se pague"""
        # Guardar el estado anterior
        old_payment_states = {record.id: record.payment_state for record in self}
        
        # Ejecutar el write original
        result = super(RentalInvoice, self).write(vals)
        
        # Verificar si cambió el estado de pago
        if 'payment_state' in vals:
            for record in self:
                # Si la factura ahora está pagada y antes no lo estaba
                if record.payment_state == 'paid' and old_payment_states.get(record.id) != 'paid':
                    # Si tiene contrato vinculado, notificar en el chatter
                    if record.vehicle_contract_id:
                        record.vehicle_contract_id.message_post(
                            body=_(
                                "💰 <strong>Factura Pagada</strong><br/>"
                                "La factura <a href='#' data-oe-model='account.move' data-oe-id='%s'>%s</a> "
                                "por un importe de <strong>%s</strong> ha sido pagada completamente."
                            ) % (record.id, record.name, f"{record.amount_total:.2f} {record.currency_id.symbol}"),
                            subject=_("Factura Pagada"),
                            message_type='notification',
                            subtype_xmlid='mail.mt_note',
                        )
        
        return result


class RentalDeposit(models.Model):
    """Rental Deposit"""
    _inherit = 'account.payment'
    _description = __doc__

    vehicle_contract_id = fields.Many2one('vehicle.contract', string="Vehicle Contract")
