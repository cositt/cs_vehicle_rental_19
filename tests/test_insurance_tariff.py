# -*- coding: utf-8 -*-
"""No-excess insurance from the 2026 tariff (V3), per day and VAT included.

There was no insurance tariff at all, so the no-excess insurance was
charged at 0 EUR. The basic insurance is included in the rental and has an
excess of 750 EUR + VAT per impact.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_insurance')
class TestInsuranceTariff(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['vehicle.insurance.pricing'].search([]).write({'active': False})
        cls.company._vehicle_rental_load_insurance_pricing()

    def _price(self, days, special=False):
        return self.env['vehicle.insurance.pricing'].find_insurance_price('no_franchise', days, special)

    def test_prices_per_day_by_duration(self):
        expected = {2: 36, 5: 27, 10: 24, 20: 19, 45: 15, 90: 12, 200: 9}
        for days, price in expected.items():
            self.assertEqual(self._price(days), price, f'{days} days')

    def test_special_driver_prices(self):
        expected = {2: 46, 5: 35, 10: 31, 20: 28, 45: 24, 90: 21, 200: 19}
        for days, price in expected.items():
            self.assertEqual(self._price(days, special=True), price, f'{days} days')

    def test_loading_again_does_not_duplicate(self):
        self.company._vehicle_rental_load_insurance_pricing()
        self.assertEqual(self.env['vehicle.insurance.pricing'].search_count(
            [('company_id', '=', self.company.id), ('insurance_type', '=', 'no_franchise')]), 14)

    def test_contract_with_no_excess_insurance_is_charged(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.insurance_type = 'no_franchise'
        self.assertEqual(contract.insurance_price_per_day, 27.0)

    def test_basic_insurance_states_the_750_excess(self):
        label = dict(self.env['vehicle.contract']._fields['insurance_type'].selection)['basic']
        self.assertIn('750', label)
