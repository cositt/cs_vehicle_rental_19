# -*- coding: utf-8 -*-
"""Deposit by payment method, from the general conditions of the tariff.

Credit card 300 EUR; debit card 750 EUR, or the credit card amount with the
no-excess insurance; cash 750 EUR with the no-excess insurance compulsory;
FLEXIRENT the debit card amount whatever the payment. The amounts live in
the deposit rules, one per category and payment method.
"""
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DEPOSIT_BY_PAYMENT = {'credit': 300.0, 'debit': 750.0, 'cash': 750.0}
DEPOSIT_RULES_FROM = date(2026, 1, 1)
CASH = [('cash', 'Efectivo')]


class VehicleDepositRuleCash(models.Model):
    _inherit = 'vehicle.deposit.rule'

    card_type = fields.Selection(selection_add=CASH, ondelete={'cash': 'cascade'})


class ResCompanyDeposit(models.Model):
    _inherit = 'res.company'

    def _vehicle_rental_load_deposit_rules(self):
        """One rule per category and payment method, with the tariff amounts.

        Existing rules are corrected instead of duplicated.
        """
        Rule = self.env['vehicle.deposit.rule'].sudo()
        categories = (self.env['fleet.vehicle'].sudo().with_context(active_test=False)
                      .search([('category_id', '!=', False)]).mapped('category_id')
                      | self.env['vehicle.pricing.rule'].sudo().with_context(active_test=False)
                      .search([]).mapped('vehicle_category_id'))
        for company in self:
            for category in categories:
                for card_type, amount in DEPOSIT_BY_PAYMENT.items():
                    rule = Rule.search([
                        ('company_id', '=', company.id),
                        ('vehicle_category_id', '=', category.id),
                        ('card_type', '=', card_type),
                    ], limit=1, order='valid_from desc')
                    values = {'deposit_fixed': amount, 'deposit_percentage': 0.0,
                              'apply_both': False, 'min_deposit': 0.0, 'max_deposit': 0.0,
                              'active': True}
                    if rule:
                        rule.write(values)
                    else:
                        Rule.create(dict(values, company_id=company.id, currency_id=company.currency_id.id,
                                         vehicle_category_id=category.id, card_type=card_type,
                                         valid_from=DEPOSIT_RULES_FROM))


class VehicleContractDeposit(models.Model):
    _inherit = 'vehicle.contract'

    deposit_card_type = fields.Selection(selection_add=CASH, ondelete={'cash': 'set default'})

    def _deposit_payment_method(self):
        """Payment method whose rule gives the deposit of this contract."""
        self.ensure_one()
        if self.pricing_type == 'flexirent':
            return 'debit'
        if self.deposit_card_type == 'debit' and self.insurance_type == 'no_franchise':
            return 'credit'
        return self.deposit_card_type

    @api.depends('vehicle_id', 'vehicle_id.category_id', 'deposit_card_type',
                 'insurance_type', 'pricing_type', 'company_id')
    def _compute_deposit_rule(self):
        Rule = self.env['vehicle.deposit.rule'].sudo()
        for record in self:
            category = record.vehicle_id.category_id
            if not (category and record.deposit_card_type):
                record.deposit_rule_id = False
                continue
            today = fields.Date.today()
            record.deposit_rule_id = Rule.search([
                ('vehicle_category_id', '=', category.id),
                ('card_type', '=', record._deposit_payment_method()),
                ('company_id', '=', (record.company_id or self.env.company).id),
                ('valid_from', '<=', today),
                '|', ('valid_until', '=', False), ('valid_until', '>=', today),
            ], limit=1, order='valid_from desc')

    deposit_rule_note = fields.Char(
        string="Motivo de la regla", compute='_compute_deposit_rule_note',
        help="Por qué se aplica una regla de otro medio de pago.")

    @api.depends('deposit_card_type', 'insurance_type', 'pricing_type')
    def _compute_deposit_rule_note(self):
        for record in self:
            method = record._deposit_payment_method() if record.deposit_card_type else False
            if record.pricing_type == 'flexirent':
                record.deposit_rule_note = _('FLEXIRENT: fianza fija de la tarifa.')
            elif method and method != record.deposit_card_type:
                record.deposit_rule_note = _(
                    'Débito con seguro sin franquicia: se aplica la fianza de tarjeta de crédito.')
            else:
                record.deposit_rule_note = False

    @api.onchange('calculated_deposit', 'use_deposit_from_rule')
    def _onchange_deposit_from_rule(self):
        """Show the deposit of the rule right away, not only after saving."""
        for record in self:
            if record.use_deposit_from_rule and record.calculated_deposit > 0:
                record.if_any_deposit = True
                record.deposit = record.calculated_deposit

    def _check_hand_over_ready(self):
        super()._check_hand_over_ready()
        for rec in self:
            if rec.deposit_card_type == 'cash' and rec.insurance_type != 'no_franchise':
                raise UserError(_(
                    'El contrato %s se paga en efectivo: según las condiciones, '
                    'el seguro sin franquicia es obligatorio. Cámbielo antes de entregar el vehículo.',
                    rec.reference_no,
                ))
