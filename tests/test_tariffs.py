# -*- coding: utf-8 -*-
"""Tariffs, insurance prices and deposit rules.

Found in the Phase 7 regression:
- Odoo 19 ignores ``_sql_constraints``: the "no duplicate tariff" rules of the
  three models never reached the database, so the same tariff could be
  entered twice and the price applied depended on which one came first.
"""
from datetime import date, timedelta

from psycopg2 import IntegrityError

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_tariffs')
class TestTariffUniqueness(VehicleRentalCase):

    def _assert_duplicate_refused(self, model, values):
        self.env[model].create(values)
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'), self.env.cr.savepoint():
            self.env[model].create(values)
            self.env.flush_all()

    def _standard(self, **values):
        return dict({'vehicle_category_id': self.category.id, 'pricing_type': 'standard',
                     'km_range': '350', 'duration_range': '3-5d', 'price_per_unit': 60.0,
                     'valid_from': date(2031, 1, 1)}, **values)

    def test_standard_tariff_twice(self):
        self._assert_duplicate_refused('vehicle.pricing.rule', self._standard())

    def test_flexirent_tariff_twice(self):
        self._assert_duplicate_refused('vehicle.pricing.rule', {
            'vehicle_category_id': self.category.id, 'pricing_type': 'flexirent',
            'flexirent_km_total': 2500, 'flexirent_duration_days': 30, 'price_per_unit': 900.0,
            'valid_from': date(2031, 1, 1)})

    def test_standard_tariffs_of_one_category_coexist(self):
        """The FLEXIRENT key must not catch standard tariffs (same 0 km / 30 days)."""
        self.env['vehicle.pricing.rule'].create(self._standard())
        self.env['vehicle.pricing.rule'].create(self._standard(km_range='500'))
        self.env.flush_all()

    def test_insurance_price_twice(self):
        self._assert_duplicate_refused('vehicle.insurance.pricing', {
            'insurance_type': 'no_franchise', 'duration_range': '1_3', 'driver_type': 'normal',
            'price_per_day': 12.0, 'valid_from': date(2031, 1, 1)})

    def test_deposit_rule_twice(self):
        self._assert_duplicate_refused('vehicle.deposit.rule', {
            'vehicle_category_id': self.category.id, 'card_type': 'debit', 'deposit_fixed': 300.0,
            'valid_from': date(2031, 1, 1)})



@tagged('post_install', '-at_install', 'vehicle_tariffs')
class TestTariffCompany(VehicleRentalCase):
    """Insurance prices and deposit rules are per company: the contract's.

    The insurance price was taken from any company (whichever came first) and
    the deposit rule from the company the user had active, not the contract's.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other = cls.env['res.company'].create({'name': 'Otra Tarifas'})
        Insurance = cls.env['vehicle.insurance.pricing']
        Insurance.search([('insurance_type', '=', 'no_franchise'), ('duration_range', '=', '4_7')]).active = False
        for company, price in ((cls.other, 99.0), (cls.company, 27.0)):
            for driver_type in ('normal', 'special'):
                Insurance.create({
                    'company_id': company.id, 'insurance_type': 'no_franchise', 'duration_range': '4_7',
                    'driver_type': driver_type, 'price_per_day': price, 'valid_from': date(2020, 1, 1)})
        Deposit = cls.env['vehicle.deposit.rule']
        for company, amount in ((cls.company, 300.0), (cls.other, 999.0)):
            Deposit.create({'company_id': company.id, 'vehicle_category_id': cls.category.id,
                            'card_type': 'credit', 'deposit_fixed': amount, 'valid_from': date(2020, 1, 1)})

    def test_insurance_price_of_the_contract_company(self):
        self.contract.write({'insurance_type': 'no_franchise', 'end_date': self.start_date + timedelta(days=5)})
        self.assertEqual(self.contract.insurance_price_per_day, 27.0)

    def test_deposit_rule_of_the_contract_company(self):
        # a contract of the other company, handled while the user has this one active
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'company_id': self.other.id, 'deposit_card_type': 'credit'})
        contract._compute_deposit_rule()
        self.assertEqual(contract.deposit_rule_id.company_id, self.other)
