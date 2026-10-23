# -*- coding: utf-8 -*-
"""Renting a vehicle is a service: income goes to 705 "Prestaciones de servicios".

The Spanish chart sets 700000 "Ventas de mercaderías" as the income account of
the company and of the sales journal, so every rental invoice was booked as a
sale of goods.
"""
import importlib.util

from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase


def _account(env, company, code):
    return env['account.account'].with_company(company).search([
        ('code', '=', code), ('company_ids', 'in', company.ids)], limit=1)


@tagged('post_install', '-at_install', 'vehicle_income_account')
class TestIncomeAccount(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.services = _account(cls.env, cls.company, '705000')
        cls.goods = _account(cls.env, cls.company, '700000')

    def _rent_invoice(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'payment_type': 'full_payment', 'use_deposit_from_rule': False,
                        'if_any_deposit': False, 'deposit': 0.0})
        contract.action_create_vehicle_payment()
        option = contract.vehicle_payment_option_ids[0]
        option.action_create_payment_invoice()
        return contract, option.invoice_id

    def test_rent_invoice_goes_to_services(self):
        contract, invoice = self._rent_invoice()
        rent = invoice.invoice_line_ids.filtered(lambda l: l.product_id == contract.invoice_item_id)
        self.assertEqual(rent.account_id, self.services)

    def test_line_without_product_goes_to_services(self):
        _contract, invoice = self._rent_invoice()
        invoice.write({'invoice_line_ids': [(0, 0, {'name': 'Cargo manual', 'price_unit': 10.0})]})
        manual = invoice.invoice_line_ids.filtered(lambda l: l.name == 'Cargo manual')
        self.assertEqual(manual.account_id, self.services)

    def test_migration_moves_booked_lines_to_services(self):
        _contract, invoice = self._rent_invoice()
        invoice.invoice_line_ids.account_id = self.goods
        invoice.action_post()
        self.env.flush_all()

        path = file_path('vehicle_rental/migrations/19.0.6.13/post-migrate.py')
        spec = importlib.util.spec_from_file_location('income_account_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, '19.0.6.12')
        self.env.invalidate_all()

        self.assertEqual(invoice.invoice_line_ids.account_id, self.services)
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(self.company.income_account_id, self.services)
