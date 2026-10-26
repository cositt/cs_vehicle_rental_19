# -*- coding: utf-8 -*-
"""An extension re-prices the whole rental with the tariff of the new length.

Jesús Muñoz, 2026-10-22 (VC2026/10/00070): a 2-day rental at 97 €/day extended
to a 3rd day. The 3-5 day band costs 85 €/day, so the rental is 255 € and only
61 € are missing. The extension kept 97 €/day and charged 86,90 € for the
21,5 hours between 10:30 and 08:00 of the next day.
"""
from datetime import datetime

from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_extension_tariff')
class TestExtensionReprices(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Rule = cls.env['vehicle.pricing.rule']
        for band, price in (('1-2d', 97.0), ('3-5d', 85.0)):
            Rule.create({'vehicle_category_id': cls.category.id, 'pricing_type': 'standard',
                         'km_range': '350', 'duration_range': band, 'price_per_unit': price,
                         'valid_from': '2026-01-01', 'company_id': cls.env.company.id})
        cls.spare_vehicle.category_id = cls.category
        cls.two_days = cls.env['vehicle.contract'].create({
            'customer_id': cls.customer.id, 'vehicle_id': cls.spare_vehicle.id,
            'rent_type': 'days', 'rent': 97.0, 'km_range': '350',
            'start_date': datetime(2026, 10, 28, 10, 30), 'end_date': datetime(2026, 10, 30, 10, 30)})

    def _extension(self, new_end, **vals):
        extension = self.env['vehicle.contract.extension'].new(dict(
            {'contract_id': self.two_days.id, 'original_end_date': self.two_days.end_date,
             'daily_rate': self.two_days.rent}, new_end_date=new_end, **vals))
        extension._onchange_new_end_date_tariff()
        return extension

    def test_extension_counts_calendar_days_like_the_contract(self):
        self.assertEqual(self._extension(datetime(2026, 10, 31, 8, 0)).extension_days, 1.0)

    def test_new_length_takes_the_rate_of_its_band(self):
        self.assertEqual(self._extension(datetime(2026, 10, 31, 8, 0)).daily_rate, 85.0)

    def test_only_the_missing_amount_is_charged(self):
        extension = self._extension(datetime(2026, 10, 31, 8, 0))
        self.assertAlmostEqual(extension.extension_amount, 3 * 85.0 - 2 * 97.0)

    def test_same_band_charges_the_extra_days_at_the_same_rate(self):
        contract = self.two_days.copy({'end_date': datetime(2026, 10, 31, 10, 30), 'rent': 85.0})
        extension = self.env['vehicle.contract.extension'].new({
            'contract_id': contract.id, 'original_end_date': contract.end_date,
            'daily_rate': 85.0, 'new_end_date': datetime(2026, 11, 1, 10, 30)})
        extension._onchange_new_end_date_tariff()
        self.assertEqual(extension.daily_rate, 85.0)
        self.assertAlmostEqual(extension.extension_amount, 85.0)

    def test_rate_typed_by_hand_is_used_for_the_whole_rental(self):
        extension = self._extension(datetime(2026, 10, 31, 8, 0))
        extension.daily_rate = 80.0
        self.assertAlmostEqual(extension.extension_amount, 3 * 80.0 - 2 * 97.0)

    def test_without_tariff_the_contract_rate_is_kept(self):
        self.two_days.km_range = False
        extension = self._extension(datetime(2026, 10, 31, 8, 0))
        self.assertEqual(extension.daily_rate, 97.0)
        self.assertAlmostEqual(extension.extension_amount, 97.0)

    def test_invoice_charges_the_missing_amount_and_the_contract_the_new_rate(self):
        extension = self.env['vehicle.contract.extension'].create({
            'contract_id': self.two_days.id, 'new_end_date': datetime(2026, 10, 31, 8, 0),
            'daily_rate': 85.0})
        extension.action_mark_signed()
        extension.action_create_extension_invoice()
        line = extension.extension_invoice_id.invoice_line_ids
        self.assertAlmostEqual(line.quantity * line.price_unit, 61.0)
        self.assertEqual(self.two_days.rent, 85.0)
        self.assertAlmostEqual(self.two_days.total_vehicle_rent, 255.0)
