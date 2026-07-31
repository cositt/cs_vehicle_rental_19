# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime

from markupsafe import Markup

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
        readonly=True,
        copy=False,
        help='Fecha de fin del contrato en el momento de crear la ampliación. '
             'Se congela al crear para que la ampliación conserve su histórico '
             'aunque el contrato se amplíe después.',
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

    def _get_base_end_date(self):
        """Fecha de fin de referencia: la congelada al crear, o la del contrato."""
        self.ensure_one()
        return self.original_end_date or self.contract_id.end_date

    @api.depends('original_end_date', 'contract_id.end_date', 'new_end_date')
    def _compute_extension_days(self):
        for rec in self:
            base_end_date = rec._get_base_end_date()
            if base_end_date and rec.new_end_date and rec.new_end_date > base_end_date:
                delta = rec.new_end_date - base_end_date
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
            if contract.exists():
                if 'daily_rate' in fields_list and not res.get('daily_rate'):
                    res['daily_rate'] = contract.rent or 0.0
                if 'original_end_date' in fields_list and not res.get('original_end_date'):
                    res['original_end_date'] = contract.end_date
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Congelar la fecha de fin original del contrato al crear la ampliación."""
        for vals in vals_list:
            if not vals.get('original_end_date') and vals.get('contract_id'):
                contract = self.env['vehicle.contract'].browse(vals['contract_id'])
                vals['original_end_date'] = contract.end_date
        return super().create(vals_list)

    @api.constrains('original_end_date', 'contract_id', 'new_end_date')
    def _check_new_end_date(self):
        for rec in self:
            base_end_date = rec._get_base_end_date()
            if not base_end_date or not rec.new_end_date:
                continue
            if rec.new_end_date <= base_end_date:
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
                rec._post_signed_to_contract()

    def _post_signed_to_contract(self):
        """Dejar constancia en el chatter del contrato de que la ampliación se firmó."""
        self.ensure_one()
        if not self.contract_id:
            return
        body = Markup('''
            <div style="padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px;">
                <h4 style="color: #856404; margin: 0 0 10px 0;">
                    <i class="fa fa-pencil-square-o"></i> Ampliación de Contrato Firmada
                </h4>
                <table style="width: 100%%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; font-weight: bold; width: 40%%;">Fecha fin original:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Nueva fecha de fin:</td>
                        <td style="padding: 5px;"><strong>%s</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Días de ampliación:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Importe:</td>
                        <td style="padding: 5px;">%s %s</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 5px; font-size: 11px; color: #856404;">
                            Pendiente de facturar. La fecha de fin del contrato se actualizará al emitir la factura.
                        </td>
                    </tr>
                </table>
            </div>
        ''') % (
            self.original_end_date or '-',
            self.new_end_date or '-',
            f"{self.extension_days:,.1f}",
            f"{self.extension_amount:,.2f}",
            self.currency_id.symbol or '',
        )
        self.contract_id.message_post(body=body)

    def _generate_addendum_attachment(self):
        """Renderizar el addendum de ampliación y adjuntarlo al contrato."""
        self.ensure_one()
        report = self.env.ref(
            'vehicle_rental.action_report_vehicle_contract_extension_addendum',
            raise_if_not_found=False
        )
        if not report:
            return None
        pdf_content, _dummy = report.sudo()._render_qweb_pdf(
            report.report_name, res_ids=self.ids
        )
        if not pdf_content:
            return None
        filename = _('Addendum_Ampliacion_%s.pdf') % self.contract_id.reference_no
        return self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'vehicle.contract',
            'res_id': self.contract_id.id,
            'mimetype': 'application/pdf',
        })

    def _post_invoiced_to_contract(self, invoice, previous_end_date):
        """Postear el resumen de la ampliación facturada en el chatter del contrato."""
        self.ensure_one()
        addendum = self._generate_addendum_attachment()

        body = Markup('''
            <div style="padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;">
                <h4 style="color: #155724; margin: 0 0 10px 0;">
                    <i class="fa fa-calendar-plus-o"></i> Ampliación de Contrato Facturada
                </h4>
                <table style="width: 100%%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; font-weight: bold; width: 40%%;">Fecha fin:</td>
                        <td style="padding: 5px;">%s → <strong>%s</strong></td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 5px; font-weight: bold;">Días de ampliación:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Tarifa por día:</td>
                        <td style="padding: 5px;">%s %s</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Importe total:</td>
                        <td style="padding: 5px;"><strong>%s %s</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Factura:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 10px 5px; text-align: center;">
                            <a href="/web#id=%s&amp;model=vehicle.contract.extension&amp;view_type=form"
                               style="color: #007bff; text-decoration: none; font-weight: bold;">
                                <i class="fa fa-file-text-o"></i> Ver Addendum/Anexo
                            </a>
                        </td>
                    </tr>
                </table>
            </div>
        ''') % (
            previous_end_date or '-',
            self.new_end_date or '-',
            f"{self.extension_days:,.1f}",
            f"{self.daily_rate:,.2f}", self.currency_id.symbol or '',
            f"{self.extension_amount:,.2f}", self.currency_id.symbol or '',
            invoice.name or _('Borrador'),
            self.id,
        )

        if addendum:
            self.contract_id.message_post(body=body, attachment_ids=[addendum.id])
        else:
            self.contract_id.message_post(body=body)

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
        previous_end_date = contract.end_date
        self.write({
            'extension_invoice_id': invoice.id,
            'state': 'invoiced',
        })
        contract.write({'end_date': self.new_end_date})
        # Dejar constancia en el contrato: resumen + addendum adjunto
        self._post_invoiced_to_contract(invoice, previous_end_date)
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
