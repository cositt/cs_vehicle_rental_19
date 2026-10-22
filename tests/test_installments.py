# -*- coding: utf-8 -*-
"""Instalments are fixed amounts, one per period, plus a prorated last one.

Before, every instalment was prorated by the days of its calendar month, so a
FLEXIRENT fee of 2.180 EUR came out as 2.253 / 2.180 / 2.107... The schedule
now always adds up to the rental total, and the daily cron invoices each
instalment once, on its day, without catching up past ones.
"""
from datetime import date, datetime, timedelta

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .test_flexirent import FlexirentCase


@tagged('post_install', '-at_install', 'vehicle_installments')
class TestInstallmentSchedule(FlexirentCase):

    def _standard_contract(self, start, days, payment_type, rent=50.0):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'start_date': start, 'end_date': start + timedelta(days=days),
                        'rent': rent, 'payment_type': payment_type})
        return contract

    def _schedule(self, contract):
        contract.action_create_vehicle_payment()
        options = contract.vehicle_payment_option_ids.sorted('payment_date')
        self.assertAlmostEqual(sum(options.mapped('payment_amount')), contract.total_vehicle_rent,
                               places=2, msg='the schedule must add up to the rental total')
        return options

    def test_flexirent_two_years_is_24_equal_fees(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), payment_type='monthly')
        options = self._schedule(contract)
        self.assertEqual(len(options), 24)
        self.assertEqual(set(options.mapped('payment_amount')), {2180.0})
        self.assertEqual(options[0].payment_date, date(2027, 9, 17))
        self.assertEqual(options[1].payment_date, date(2027, 10, 17))
        self.assertEqual(options[-1].payment_date, date(2029, 8, 17))
        self.assertEqual(options[0].name, 'Cuota 1/24')

    def test_flexirent_leftover_days_are_a_last_prorated_fee(self):
        contract = self._flexirent_contract(datetime(2028, 9, 30, 7, 0), payment_type='monthly')
        options = self._schedule(contract)
        self.assertEqual(len(options), 13)
        self.assertEqual(set(options[:12].mapped('payment_amount')), {2180.0})
        self.assertAlmostEqual(options[-1].payment_amount, round(2180.0 * 13 / 30, 2), places=2)
        self.assertEqual(options[-1].payment_date, date(2028, 9, 17))

    def test_weekly(self):
        contract = self._standard_contract(datetime(2027, 3, 1, 9, 0), 17, 'weekly')
        options = self._schedule(contract)
        self.assertEqual(options.mapped('payment_amount'), [350.0, 350.0, 150.0])
        self.assertEqual(options.mapped('payment_date'),
                         [date(2027, 3, 1), date(2027, 3, 8), date(2027, 3, 15)])

    def test_daily(self):
        contract = self._standard_contract(datetime(2027, 3, 1, 9, 0), 5, 'daily')
        options = self._schedule(contract)
        self.assertEqual(options.mapped('payment_amount'), [50.0] * 5)

    def test_monthly_standard_is_fixed_too(self):
        """A standard rental paid monthly: 30-day blocks, same amount every month."""
        contract = self._standard_contract(datetime(2027, 1, 31, 9, 0), 75, 'monthly', rent=40.0)
        options = self._schedule(contract)
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0].payment_amount, options[1].payment_amount)
        self.assertLess(options[2].payment_amount, options[0].payment_amount)
        self.assertEqual(options[1].payment_date, date(2027, 2, 28))

    def test_quarterly(self):
        contract = self._flexirent_contract(datetime(2028, 9, 17, 7, 0), payment_type='quarterly')
        options = self._schedule(contract)
        self.assertEqual(options.mapped('payment_amount'), [3 * 2180.0] * 4)
        self.assertEqual(options[1].payment_date, date(2027, 12, 17))

    def test_yearly(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), payment_type='yearly')
        options = self._schedule(contract)
        self.assertEqual(options.mapped('payment_amount'), [12 * 2180.0] * 2)

    def test_full_payment_is_one_instalment(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), payment_type='full_payment')
        options = self._schedule(contract)
        self.assertEqual(len(options), 1)
        self.assertEqual(options.payment_amount, 52320.0)

    def test_regenerating_replaces_the_schedule(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), payment_type='monthly')
        contract.action_create_vehicle_payment()
        contract.payment_type = 'quarterly'
        options = self._schedule(contract)
        self.assertEqual(len(options), 8)

    def test_schedule_with_invoices_cannot_be_regenerated(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), payment_type='monthly')
        contract.action_create_vehicle_payment()
        contract.vehicle_payment_option_ids[0].action_create_payment_invoice()
        with self.assertRaises(UserError):
            contract.action_create_vehicle_payment()


@tagged('post_install', '-at_install', 'vehicle_installments')
class TestInstallmentInvoicing(FlexirentCase):

    def setUp(self):
        super().setUp()
        self.contract = self._flexirent_contract(
            datetime(2027, 12, 17, 7, 0), payment_type='monthly',
            use_deposit_from_rule=False, if_any_deposit=True, deposit=750.0)
        self.contract.action_create_vehicle_payment()
        self.contract.status = 'b_in_progress'
        self.options = self.contract.vehicle_payment_option_ids.sorted('payment_date')

    def _invoice_products(self, option):
        return option.invoice_id.invoice_line_ids.mapped('product_id')

    def test_cron_invoices_only_todays_instalment_once(self):
        with freeze_time('2027-10-17 06:00:00'):
            self.env['vehicle.contract'].action_create_rent_payment_invoice()
            self.env['vehicle.contract'].action_create_rent_payment_invoice()
        self.assertFalse(self.options[0].invoice_id, 'past instalments are not caught up')
        self.assertTrue(self.options[1].invoice_id)
        self.assertFalse(self.options[2].invoice_id)
        self.assertEqual(self.env['account.move'].search_count(
            [('vehicle_contract_id', '=', self.contract.id)]), 1)

    def test_an_invoiced_instalment_is_not_invoiced_again(self):
        self.options[0].action_create_payment_invoice()
        with self.assertRaises(UserError):
            self.options[0].action_create_payment_invoice()

    def test_deposit_goes_only_on_the_first_instalment(self):
        deposit = self.env.ref('vehicle_rental.vehicle_rent_deposit')
        self.options[0].action_create_payment_invoice()
        self.options[1].action_create_payment_invoice()
        self.assertIn(deposit, self._invoice_products(self.options[0]))
        self.assertNotIn(deposit, self._invoice_products(self.options[1]))

    def test_rent_line_is_the_instalment_amount(self):
        self.options[1].action_create_payment_invoice()
        rent_line = self.options[1].invoice_id.invoice_line_ids.filtered(
            lambda line: line.product_id == self.contract.invoice_item_id)
        self.assertEqual(rent_line.price_unit, 2180.0)
