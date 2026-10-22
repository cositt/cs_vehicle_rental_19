# -*- coding: utf-8 -*-
"""FLEXIRENT is a monthly package, not a daily rate.

Pinveco sells long rentals as a fee per 30 days with a km package chosen at
the counter (3.000 / 5.000 / 7.500 km per month). Whole calendar months are
charged at the fee; leftover days are prorated (fee x days / 30). Km above the
package are charged at 0,29 EUR + VAT for every package.
"""
from datetime import datetime

from odoo.tests import Form
from odoo.tests.common import tagged

from .common import VehicleRentalCase

START = datetime(2027, 9, 17, 7, 0)
FEES = {'3000': 2180.0, '5000': 2600.0, '7500': 3200.0}
EXTRA_KM = 0.35  # 0,29 EUR + 21 % VAT, prices are stored VAT included


class FlexirentCase(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        for km, fee in FEES.items():
            self.env['vehicle.pricing.rule'].create({
                'vehicle_category_id': self.category.id,
                'pricing_type': 'flexirent',
                'flexirent_duration_days': 30,
                'flexirent_km_total': int(km),
                'price_per_unit': fee,
                'extra_km_price': EXTRA_KM,
                'valid_from': datetime(2026, 1, 1).date(),
            })

    def _flexirent_contract(self, end, package='3000', **values):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write(dict({
            'pricing_type': 'flexirent',
            'flexirent_km_package': package,
            'start_date': START,
            'end_date': end,
        }, **values))
        return contract


@tagged('post_install', '-at_install', 'vehicle_flexirent')
class TestFlexirentPricing(FlexirentCase):

    def test_two_years_are_24_monthly_fees(self):
        """Like contract 77: Tipo Z, 3.000 km, two years from 17/09."""
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0))
        self.assertEqual(contract.rent, 2180.0)
        self.assertEqual(contract.flexirent_months, 24.0)
        self.assertEqual(contract.total_vehicle_rent, 52320.0)
        self.assertEqual(contract.subtotal_vehicle_rent, 52320.0)
        self.assertEqual(contract.flexirent_km_included, 3000)

    def test_the_package_chosen_sets_the_fee(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), package='7500')
        self.assertEqual(contract.rent, 3200.0)
        self.assertEqual(contract.total_vehicle_rent, 24 * 3200.0)
        contract.flexirent_km_package = '5000'
        self.assertEqual(contract.rent, 2600.0)

    def test_leftover_days_are_prorated(self):
        """17/09/2027 + 12 months and 13 days = 30/09/2028."""
        contract = self._flexirent_contract(datetime(2028, 9, 30, 7, 0))
        self.assertAlmostEqual(contract.flexirent_months, 12 + 13 / 30, places=4)
        self.assertEqual(contract.total_vehicle_rent, round(2180.0 * (12 + 13 / 30), 2))

    def test_km_above_the_package_are_extra(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0),
                                            total_km=24 * 3000 + 100)
        self.assertEqual(contract.extra_km_used, 100)
        self.assertEqual(contract.extra_km_price_unit, EXTRA_KM)
        self.assertAlmostEqual(contract.extra_km_cost, 35.0)
        self.assertAlmostEqual(contract.subtotal_vehicle_rent, 52320.0 + 35.0)

    def test_km_within_the_package_are_not_extra(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), total_km=24 * 3000)
        self.assertEqual(contract.extra_km_used, 0)

    def test_standard_contracts_keep_the_daily_rate(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        self.assertEqual(contract.pricing_type, 'standard')
        self.assertEqual(contract.total_vehicle_rent, 50.0 * contract.total_days)
        self.assertFalse(contract.flexirent_months)


@tagged('post_install', '-at_install', 'vehicle_flexirent')
class TestFlexirentReport(FlexirentCase):

    def _render(self, contract):
        html, _dummy = self.env['ir.actions.report']._render_qweb_html(
            'vehicle_rental.vehicle_contract_report_template', contract.ids)
        return html.decode()

    def test_contract_pdf_shows_the_fee_and_the_schedule(self):
        contract = self._flexirent_contract(datetime(2029, 9, 17, 7, 0), payment_type='monthly')
        html = self._render(contract)
        self.assertIn('Calendario de Cuotas', html)
        self.assertIn('24 / 24', html)
        self.assertIn('17/08/2029 – 16/09/2029', html)
        self.assertIn('720', html)
        self.assertNotIn('25 / 25', html)

    def test_leftover_days_are_shown(self):
        contract = self._flexirent_contract(datetime(2028, 9, 30, 7, 0), payment_type='monthly')
        html = self._render(contract)
        self.assertIn('12 y 13 días', html)
        self.assertIn('13 / 13', html)


@tagged('post_install', '-at_install', 'vehicle_flexirent')
class TestFlexirentBookingWizard(FlexirentCase):

    def test_booking_wizard_opens_with_flexirent_tariffs(self):
        """FLEXIRENT tariffs have no km band: the wizard km options must skip it."""
        options = self.env['rental.contract.booking']._get_km_options()
        self.assertNotIn(False, [value for value, _label in options])
        Form(self.env['rental.contract.booking'])
