# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VehicleContractGroup(models.Model):
    _name = 'vehicle.contract.group'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Grupo de Contratos de Vehículos'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(
        string='Referencia', required=True, readonly=True,
        default=lambda self: _('New'), copy=False)
    customer_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    start_date = fields.Datetime(string='Fecha Inicio', tracking=True)
    end_date = fields.Datetime(string='Fecha Fin', tracking=True)

    payment_type = fields.Selection(
        [('daily', 'Diario'),
         ('weekly', 'Semanal'),
         ('monthly', 'Mensual'),
         ('quarterly', 'Trimestral'),
         ('yearly', 'Anual'),
         ('full_payment', 'Pago Completo')],
        string='Tipo de Pago')
    pricing_type = fields.Selection(
        [('standard', 'Tarifa Estándar'),
         ('flexirent', 'FLEXIRENT')],
        string='Tipo de Tarifa', default='standard')
    deposit_card_type = fields.Selection(
        [('debit', 'Tarjeta de Débito'),
         ('credit', 'Tarjeta de Crédito')],
        string='Tipo de Tarjeta', default='debit')
    tax_ids = fields.Many2many('account.tax', string='Impuestos')

    contract_ids = fields.One2many('vehicle.contract', 'group_id', string='Contratos')
    contract_count = fields.Integer(compute='_compute_contract_count', string='Nº Contratos')

    state = fields.Selection(
        [('draft', 'Borrador'),
         ('active', 'Activo'),
         ('partial_return', 'Devolución Parcial'),
         ('done', 'Finalizado'),
         ('cancel', 'Cancelado')],
        string='Estado', compute='_compute_state', store=True, default='draft')

    total_amount = fields.Monetary(
        string='Importe Total', compute='_compute_total_amount', store=True)
    total_deposit = fields.Monetary(
        string='Depósito Total', compute='_compute_total_amount', store=True)

    invoice_ids = fields.Many2many(
        'account.move', string='Facturas Consolidadas',
        relation='vehicle_contract_group_invoice_rel',
        column1='group_id', column2='invoice_id')
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    notes = fields.Text(string='Observaciones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'vehicle.contract.group') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'deposit_card_type' in vals and vals['deposit_card_type']:
            for rec in self:
                rec.contract_ids.write({
                    'deposit_card_type': vals['deposit_card_type'],
                })
        return res

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = len(rec.contract_ids)

    @api.depends('contract_ids.status')
    def _compute_state(self):
        for rec in self:
            if not rec.contract_ids:
                rec.state = 'draft'
                continue
            statuses = set(rec.contract_ids.mapped('status'))
            has_draft = 'a_draft' in statuses
            has_active = 'b_in_progress' in statuses
            has_return = 'c_return' in statuses
            has_cancel = 'd_cancel' in statuses
            non_cancel = statuses - {'d_cancel'}

            if statuses == {'d_cancel'}:
                rec.state = 'cancel'
            elif non_cancel <= {'c_return'}:
                rec.state = 'done'
            elif has_active and has_return:
                rec.state = 'partial_return'
            elif has_active:
                rec.state = 'active'
            elif has_return and has_draft:
                rec.state = 'partial_return'
            else:
                rec.state = 'draft'

    @api.depends('contract_ids.total_vehicle_rent', 'contract_ids.deposit',
                 'contract_ids.calculated_deposit', 'contract_ids.use_deposit_from_rule')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.contract_ids.mapped('total_vehicle_rent'))
            total_dep = 0.0
            for c in rec.contract_ids:
                total_dep += c.calculated_deposit if c.use_deposit_from_rule else c.deposit
            rec.total_deposit = total_dep

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contratos del Grupo',
            'res_model': 'vehicle.contract',
            'view_mode': 'list,form',
            'domain': [('group_id', '=', self.id)],
            'context': {'default_group_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facturas del Grupo',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }

    def action_activate_all(self):
        """Activar todos los contratos hijos en borrador y crear cuotas."""
        self.ensure_one()
        draft_contracts = self.contract_ids.filtered(lambda c: c.status == 'a_draft')
        if not draft_contracts:
            raise UserError(_('No hay contratos en borrador para activar.'))

        errors = []
        for contract in draft_contracts:
            if not contract.rent_type:
                errors.append(_('%s: falta tipo de alquiler') % (contract.reference_no,))
                continue
            if not contract.start_date or not contract.end_date:
                errors.append(_('%s: faltan fechas') % (contract.reference_no,))
                continue

            overlapping = self.env['vehicle.contract'].search([
                ('id', '!=', contract.id),
                ('vehicle_id', '=', contract.vehicle_id.id),
                ('status', 'in', ['b_in_progress', 'c_return']),
                ('start_date', '<=', contract.end_date),
                ('end_date', '>=', contract.start_date),
            ], limit=1)
            if overlapping:
                errors.append(
                    _('%s: solapamiento con %s') % (
                        contract.reference_no, overlapping.reference_no))
                continue

            contract.status = 'b_in_progress'
            if not contract.installment_created and contract.payment_type:
                contract.action_create_vehicle_payment()

        if errors:
            raise UserError('\n'.join(errors))
        return True

    def action_create_consolidated_invoice(self):
        """Facturación consolidada: cuotas + depósito + seguro + extras
        de todos los contratos hijos en UNA sola factura."""
        self.ensure_one()

        active_contracts = self.contract_ids.filtered(
            lambda c: c.status in ('b_in_progress', 'c_return'))
        if not active_contracts:
            raise UserError(_('No hay contratos activos para facturar.'))

        pending_installments = self.env['vehicle.payment.option'].search([
            ('vehicle_contract_id', 'in', active_contracts.ids),
            ('invoice_id', '=', False),
            ('payment_amount', '>', 0),
        ])

        invoice_lines = []
        contracts_with_installments = set()

        for installment in pending_installments:
            contract = installment.vehicle_contract_id
            contracts_with_installments.add(contract.id)
            tax = [(6, 0, contract.tax_ids.ids)]
            vehicle_label = contract.vehicle_id.name or contract.license_plate or ''
            invoice_lines.append((0, 0, {
                'product_id': installment.invoice_item_id.id,
                'name': f'[{vehicle_label}] {installment.name}',
                'quantity': 1,
                'price_unit': installment.payment_amount,
                'tax_ids': tax,
            }))

        for contract in active_contracts:
            tax = [(6, 0, contract.tax_ids.ids)]
            vehicle_label = contract.vehicle_id.name or contract.license_plate or ''

            if contract.id not in contracts_with_installments:
                invoice_lines.append((0, 0, {
                    'product_id': contract.invoice_item_id.id if contract.invoice_item_id else False,
                    'name': f'[{vehicle_label}] Alquiler',
                    'quantity': 1,
                    'price_unit': contract.total_vehicle_rent,
                    'tax_ids': tax,
                }))

            deposit_amount = 0
            if contract.use_deposit_from_rule and contract.calculated_deposit > 0:
                deposit_amount = contract.calculated_deposit
            elif (not contract.use_deposit_from_rule
                  and contract.if_any_deposit and contract.deposit > 0):
                deposit_amount = contract.deposit

            if deposit_amount > 0:
                deposit_product = self.env.ref(
                    'vehicle_rental.vehicle_rent_deposit', raise_if_not_found=False)
                if deposit_product:
                    invoice_lines.append((0, 0, {
                        'product_id': deposit_product.id,
                        'name': f'[{vehicle_label}] Depósito de Seguridad',
                        'quantity': 1,
                        'price_unit': deposit_amount,
                        'tax_ids': tax,
                    }))

            if (contract.insurance_type and
                    contract.insurance_price_per_day and
                    contract.insurance_price_per_day > 0):
                insurance_name = (
                    "Seguro Básico - Franquicia 300€"
                    if contract.insurance_type == 'basic'
                    else "Seguro Sin Franquicia")
                if contract.driver_special:
                    insurance_name += " (Conductor Especial)"
                insurance_line = {
                    'product_id': (contract.insurance_product_id.id
                                   if contract.insurance_product_id else False),
                    'name': f'[{vehicle_label}] {insurance_name}',
                    'quantity': contract.total_days or 1,
                    'price_unit': contract.insurance_price_per_day,
                    'tax_ids': ([(6, 0, contract.insurance_product_id.taxes_id.ids)]
                                if contract.insurance_product_id and contract.insurance_product_id.taxes_id
                                else []),
                }
                invoice_lines.append((0, 0, insurance_line))

            for extra_service in contract.extra_service_ids:
                if extra_service.product_id:
                    invoice_lines.append((0, 0, {
                        'product_id': extra_service.product_id.id,
                        'name': f'[{vehicle_label}] {extra_service.description or extra_service.product_id.name}',
                        'quantity': extra_service.product_qty,
                        'price_unit': extra_service.amount,
                        'tax_ids': tax,
                    }))

        if not invoice_lines:
            raise UserError(_('No hay conceptos pendientes de facturar.'))

        invoice = self.env['account.move'].sudo().create({
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'ref': self.name,
            'narration': _('Factura consolidada del grupo %s') % self.name,
            'invoice_line_ids': invoice_lines,
        })

        if pending_installments:
            pending_installments.write({'invoice_id': invoice.id})
        self.invoice_ids = [(4, invoice.id)]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura Consolidada'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_add_vehicle(self):
        """Abre el wizard de reserva en modo vinculado al grupo."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Añadir Vehículo al Grupo'),
            'res_model': 'rental.contract.booking',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_id': self.customer_id.id,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
                'default_pricing_type': self.pricing_type,
                'default_group_id': self.id,
                'default_is_multi_booking': False,
            },
        }
