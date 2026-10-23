# -*- coding: utf-8 -*-
"""Invoices of a contract belong to the company of the contract.

Found in the Phase 7 regression (multi-company): the invoices were created in
the active company of whoever pressed the button, or of the daily invoicing
task, not in the company of the contract.
"""
from datetime import timedelta

from odoo.tests.common import new_test_user, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_invoice_company')
class TestInvoiceCompany(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other = cls.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '!=', cls.company.id)], limit=1).company_id
        cls.other_tax = cls.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'), ('company_id', '=', cls.other.id), ('amount', '=', 21)], limit=1)
        cls.contract_other = cls._create_contract(cls.spare_vehicle, cls.customer, status='a_draft')
        cls.contract_other.write({
            'company_id': cls.other.id, 'tax_ids': [(6, 0, cls.other_tax.ids)],
            'payment_type': 'full_payment', 'use_deposit_from_rule': False,
            'if_any_deposit': False, 'deposit': 0.0})

    def setUp(self):
        super().setUp()
        self.assertTrue(self.other, 'needs a second company with a sales journal')
        self.assertEqual(self.env.company, self.company)

    def test_installment_invoice_is_in_the_company_of_the_contract(self):
        self.contract_other.action_create_vehicle_payment()
        option = self.contract_other.vehicle_payment_option_ids[0]
        self.assertEqual(option.company_id, self.other)
        option.action_create_payment_invoice()
        self.assertEqual(option.invoice_id.company_id, self.other)
        self.assertEqual(option.invoice_id.journal_id.company_id, self.other)

    def test_any_contract_invoice_is_in_the_company_of_the_contract(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.customer.id,
            'vehicle_contract_id': self.contract_other.id,
            'invoice_line_ids': [(0, 0, {'name': 'Cargo', 'price_unit': 10.0, 'tax_ids': False})]})
        self.assertEqual(invoice.company_id, self.other)

    def test_explicit_company_is_kept(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.customer.id, 'company_id': self.company.id,
            'invoice_line_ids': [(0, 0, {'name': 'Cargo', 'price_unit': 10.0, 'tax_ids': False})]})
        self.assertEqual(invoice.company_id, self.company)

    def test_group_invoice_is_in_the_company_of_its_contracts(self):
        group = self.env['vehicle.contract.group'].create({
            'customer_id': self.customer.id, 'start_date': self.contract_other.start_date,
            'end_date': self.contract_other.end_date})
        self.contract_other.group_id = group
        self.assertEqual(group.company_id, self.other)


@tagged('post_install', '-at_install', 'vehicle_invoice_company')
class TestContractChildrenCompany(TestInvoiceCompany):
    """What hangs from a contract of another company is hidden like the contract."""

    CHILD_MODELS = ('vehicle.contract.extension', 'vehicle.contract.return',
                    'vehicle.contract.substitution', 'vehicle.payment.option',
                    'vehicle.contract.group')

    def test_every_child_model_has_a_company_rule(self):
        for model in self.CHILD_MODELS:
            rules = self.env['ir.rule'].search([('model_id.model', '=', model), ('global', '=', True)])
            self.assertTrue(rules.filtered(lambda r: 'company_ids' in r.domain_force), model)

    def test_clerk_of_one_company_does_not_see_the_other(self):
        clerk = new_test_user(
            self.env, login='solo_principal', groups='base.group_user,fleet.fleet_group_manager',
            company_id=self.company.id, company_ids=[self.company.id, self.other.id])
        self.contract_other.action_create_vehicle_payment()
        extension = self.env['vehicle.contract.extension'].create({
            'contract_id': self.contract_other.id,
            'new_end_date': self.contract_other.end_date + timedelta(days=2), 'daily_rate': 50.0})
        as_clerk = self.env(user=clerk, context={'allowed_company_ids': [self.company.id]})
        self.assertFalse(as_clerk['vehicle.payment.option'].search(
            [('vehicle_contract_id', '=', self.contract_other.id)]))
        self.assertFalse(as_clerk['vehicle.contract.extension'].search([('id', '=', extension.id)]))
        both = self.env(user=clerk, context={'allowed_company_ids': [self.company.id, self.other.id]})
        self.assertTrue(both['vehicle.contract.extension'].search([('id', '=', extension.id)]))
