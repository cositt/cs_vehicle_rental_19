# -*- coding: utf-8 -*-
"""The end date follows from the number of days, in contracts and bookings.

Pinveco rents for long, odd periods (e.g. 379 days). Typing the days is how
they think about it; the end date keeps the pick-up time. Up to 29 days the
standard band is chosen from the days; above that the rental is FLEXIRENT.
"""
from datetime import datetime, timedelta

from odoo.tests import Form
from odoo.tests.common import tagged

from .common import VehicleRentalCase

START = datetime(2027, 11, 17, 9, 0)


@tagged('post_install', '-at_install', 'vehicle_days')
class TestContractRentalDays(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        # A FLEXIRENT tariff must exist for the category, otherwise the
        # contract falls back to standard (no FLEXIRENT rule = not available).
        self.env['vehicle.pricing.rule'].create({
            'vehicle_category_id': self.category.id,
            'pricing_type': 'flexirent',
            'flexirent_duration_days': 30,
            'flexirent_km_total': 3000,
            'price_per_unit': 2180.0,
            'valid_from': START.date() - timedelta(days=400),
        })
        self.draft = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        self.draft.write({'start_date': START, 'end_date': START + timedelta(days=3)})

    def test_days_set_the_end_date_keeping_the_time(self):
        """17/11/2027 09:00 + 379 days = 30/11/2028 09:00 (2028 is a leap year)."""
        self.draft.rental_days = 379
        self.assertEqual(self.draft.end_date, datetime(2028, 11, 30, 9, 0))
        self.assertEqual(self.draft.end_date, START + timedelta(days=379))

    def test_editing_the_end_date_recomputes_the_days(self):
        self.draft.end_date = START + timedelta(days=45)
        self.assertEqual(self.draft.rental_days, 45)

    def test_days_drive_the_tariff_band(self):
        for days, band in ((2, '1-2d'), (5, '3-5d'), (10, '6-10d'), (20, '11-20d'), (29, '21-29d')):
            with self.subTest(days=days):
                self.draft.rental_days = days
                self.assertEqual(self.draft.duration_range, band)
                self.assertFalse(self.draft.needs_flexirent)
        self.draft.rental_days = 30
        self.assertTrue(self.draft.needs_flexirent)

    def test_more_than_29_days_switches_to_flexirent_in_the_form(self):
        form = Form(self.draft)  # onchange behaviour only, not saved
        form.rental_days = 379
        self.assertEqual(form.end_date, START + timedelta(days=379))
        self.assertEqual(form.pricing_type, 'flexirent')
        form.rental_days = 10
        self.assertEqual(form.pricing_type, 'standard')


@tagged('post_install', '-at_install', 'vehicle_days')
class TestBookingWizardRentalDays(VehicleRentalCase):

    def _wizard(self):
        form = Form(self.env['rental.contract.booking'])
        form.start_date = START
        return form

    def test_days_set_the_end_date_and_band(self):
        form = self._wizard()
        form.rental_days = 7
        self.assertEqual(form.end_date, START + timedelta(days=7))
        self.assertEqual(form.duration_range, '6-10d')
        self.assertEqual(form.pricing_type, 'standard')

    def test_long_rental_is_flexirent(self):
        form = self._wizard()
        form.rental_days = 379
        self.assertEqual(form.end_date, START + timedelta(days=379))
        self.assertEqual(form.pricing_type, 'flexirent')

    def test_editing_the_end_date_recomputes_the_days(self):
        form = self._wizard()
        form.end_date = START + timedelta(days=12)
        self.assertEqual(form.rental_days, 12)
        self.assertEqual(form.duration_range, '11-20d')

    def test_options_use_tariff_labels_in_order(self):
        wizard = self.env['rental.contract.booking']
        durations = [value for value, _label in wizard._get_duration_options()]
        order = ['4h', '1-2d', '3-5d', '6-10d', '11-20d', '21-29d']
        self.assertEqual(durations, [d for d in order if d in durations])
        self.assertIn(('flexirent', 'Flexirent - Larga Temporada'), wizard._get_pricing_type_options())
        self.assertIn(('1-2d', '1-2 días'), wizard._get_duration_options())
