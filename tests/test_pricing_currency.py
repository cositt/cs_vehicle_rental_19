# -*- coding: utf-8 -*-
"""Tariffs are priced in the currency of their company (EUR), never in USD."""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'vehicle_pricing')
class TestPricingCurrency(TransactionCase):

    def test_no_tariff_in_a_foreign_currency(self):
        """The 274 tariffs imported on 2025-12-19 came in USD."""
        rules = self.env['vehicle.pricing.rule'].with_context(active_test=False).search([])
        wrong = rules.filtered(lambda r: r.currency_id != r.company_id.currency_id)
        self.assertFalse(wrong, f"{len(wrong)} tarifas con moneda distinta a la de su compañía: "
                                f"{set(wrong.mapped('currency_id.name'))}")

    def test_companies_work_in_euros(self):
        for company in self.env['res.company'].search([]):
            with self.subTest(company=company.name):
                self.assertEqual(company.currency_id, self.env.ref('base.EUR'))
