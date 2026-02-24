# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VehicleContractExtension(models.Model):
    _name = 'vehicle.contract.extension'
    _description = 'Ampliación de contrato de alquiler'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    contract_id = fields.Many2one(
        'vehicle.contract',
        string='Contrato',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='contract_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='contract_id.currency_id',
    )
    original_end_date = fields.Datetime(
        string='Fecha fin original',
        related='contract_id.end_date',
        readonly=True,
    )
    new_end_date = fields.Datetime(
        string='Nueva fecha de fin',
        required=True,
        tracking=True,
    )
    extension_days = fields.Float(
        string='Días de ampliación',
        compute='_compute_extension_days',
        store=True,
        readonly=True,
    )
    daily_rate = fields.Monetary(
        string='Tarifa por día',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Por defecto la del contrato; se puede mantener o cambiar.',
    )
    extension_amount = fields.Monetary(
        string='Importe ampliación',
        currency_field='currency_id',
        compute='_compute_extension_amount',
        store=True,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado a firmar'),
        ('signed', 'Firmado'),
        ('invoiced', 'Facturado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', tracking=True, copy=False)
    extension_invoice_id = fields.Many2one(
        'account.move',
        string='Factura ampliación',
        readonly=True,
        copy=False,
    )
    extension_invoice_state = fields.Selection(
        related='extension_invoice_id.payment_state',
        string='Estado pago factura',
    )
    partner_id = fields.Many2one(
        'res.partner',
        related='contract_id.customer_id',
        string='Cliente',
        store=True,
    )

    @api.depends('contract_id.end_date', 'new_end_date')
    def _compute_extension_days(self):
        for rec in self:
            if rec.contract_id and rec.contract_id.end_date and rec.new_end_date:
                if rec.new_end_date <= rec.contract_id.end_date:
                    rec.extension_days = 0.0
                else:
                    delta = rec.new_end_date - rec.contract_id.end_date
                    rec.extension_days = delta.total_seconds() / (24.0 * 3600)
            else:
                rec.extension_days = 0.0

    @api.depends('extension_days', 'daily_rate')
    def _compute_extension_amount(self):
        for rec in self:
            rec.extension_amount = (rec.extension_days or 0.0) * (rec.daily_rate or 0.0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_contract_id'):
            contract = self.env['vehicle.contract'].browse(self.env.context['default_contract_id'])
            if contract.exists() and 'daily_rate' in fields_list and not res.get('daily_rate'):
                res['daily_rate'] = contract.rent or 0.0
        return res

    @api.constrains('contract_id', 'new_end_date')
    def _check_new_end_date(self):
        for rec in self:
            if not rec.contract_id or not rec.contract_id.end_date or not rec.new_end_date:
                continue
            if rec.new_end_date <= rec.contract_id.end_date:
                raise ValidationError(
                    _('La nueva fecha de fin debe ser posterior a la fecha de fin original del contrato.')
                )

    def action_send_to_sign(self):
        """Abre el wizard de Odoo Sign para enviar a firmar (si está instalado)."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Solo se puede enviar a firmar una ampliación en borrador.'))
        if not self.contract_id.customer_id:
            raise UserError(_('El contrato no tiene cliente asignado.'))
        try:
            action = self.env['ir.actions.actions']._for_xml_id('sign.action_sign_send_request')
            action['context'] = {
                'default_reference_doc': f'{self._name},{self.id}',
                'default_signer_id': self.contract_id.customer_id.id,
            }
            self.state = 'sent'
            return action
        except ValueError:
            self.action_mark_sent()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Módulo Sign no instalado. Ampliación marcada como "Enviado". Use "Marcar como firmado" cuando el cliente haya firmado.'),
                    'type': 'info',
                    'sticky': False,
                },
            }

    def action_mark_sent(self):
        """Marcar como enviado a firmar (cuando no se usa Sign o se envía por otro medio)."""
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'sent'

    def action_mark_signed(self):
        """Marcar como firmado manualmente (firma presencial)."""
        for rec in self:
            if rec.state in ('draft', 'sent'):
                rec.state = 'signed'

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('invoiced',):
                rec.state = 'cancelled'

    def action_create_extension_invoice(self):
        """Crea la factura de la ampliación y actualiza la fecha de fin del contrato."""
        self.ensure_one()
        if self.state != 'signed':
            raise UserError(_('Solo se puede facturar una ampliación que esté firmada.'))
        if self.extension_invoice_id:
            raise UserError(_('Esta ampliación ya tiene factura creada.'))
        contract = self.contract_id
        if not contract.customer_id:
            raise UserError(_('El contrato no tiene cliente asignado.'))
        product = self.env.ref('vehicle_rental.vehicle_rent_charge', raise_if_not_found=False)
        if not product:
            product = contract.invoice_item_id
        if not product:
            raise UserError(_('No hay producto de alquiler configurado para la factura.'))
        journal = self.env['account.journal'].sudo().search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(_('No se encontró diario de ventas.'))
        name_line = _('Ampliación de alquiler – %s – %s día(s)') % (
            contract.reference_no,
            self.extension_days,
        )
        invoice_vals = {
            'partner_id': contract.customer_id.id,
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'invoice_origin': _('Ampliación %s') % contract.reference_no,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': name_line,
                'quantity': self.extension_days,
                'price_unit': self.daily_rate,
                'tax_ids': [(6, 0, product.taxes_id.ids)],
            })],
        }
        invoice = self.env['account.move'].sudo().create(invoice_vals)
        self.write({
            'extension_invoice_id': invoice.id,
            'state': 'invoiced',
        })
        contract.write({'end_date': self.new_end_date})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de ampliación'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_extension_invoice(self):
        """Abrir la factura de la ampliación."""
        self.ensure_one()
        if not self.extension_invoice_id:
            raise UserError(_('Esta ampliación no tiene factura.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de ampliación'),
            'res_model': 'account.move',
            'res_id': self.extension_invoice_id.id,
            'view_mode': 'form',
        }
