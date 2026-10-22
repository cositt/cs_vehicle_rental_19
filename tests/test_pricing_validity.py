# -*- coding: utf-8 -*-
"""Only the tariff in force today is offered.

When the 2026 prices are loaded the 2025 rows stay, closed with valid_until,
so signed contracts keep their price. Every place that reads a tariff has to
skip the closed ones; the booking wizard and the web price endpoint did not.
"""
import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import HttpCase, TransactionCase, tagged

OLD_PRICE = 75.0
NEW_PRICE = 83.0


def _make_tariffs(env):
    today = fields.Date.today()
    category = env['fleet.vehicle.model.category'].create({'name': 'Tipo Test - Vigencia'})
    rule = env['vehicle.pricing.rule']
    common = {
        'vehicle_category_id': category.id,
        'pricing_type': 'standard',
        'km_range': '350',
        'duration_range': '1-2d',
    }
    old = rule.create(dict(common, price_per_unit=OLD_PRICE,
                           valid_from=today - timedelta(days=400),
                           valid_until=today - timedelta(days=1)))
    new = rule.create(dict(common, price_per_unit=NEW_PRICE, valid_from=today))
    return category, old, new


@tagged('post_install', '-at_install', 'vehicle_pricing')
class TestTariffValidity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category, cls.old, cls.new = _make_tariffs(cls.env)

    def test_lookup_returns_the_tariff_in_force(self):
        found = self.env['vehicle.pricing.rule'].find_pricing_rule(
            category_id=self.category.id, total_km=300, total_days=2)
        self.assertEqual(found, self.new)

    def test_booking_wizard_prices_with_the_tariff_in_force(self):
        wizard = self.env['rental.contract.booking'].new({
            'selected_category_id': self.category.id,
            'duration_range': '1-2d',
            'km_range': '350',
            'pricing_type': 'standard',
        })
        self.assertEqual(wizard.calculated_price, NEW_PRICE)


@tagged('post_install', '-at_install', 'vehicle_pricing')
class TestWebTariffValidity(HttpCase):

    def test_web_price_endpoint_uses_the_tariff_in_force(self):
        category, _old, _new = _make_tariffs(self.env)
        response = self.url_open('/web/get-dynamic-pricing', data={
            'category_id': category.id, 'duration': '1-2d', 'km_range': '350',
        })
        self.assertEqual(json.loads(response.text).get('price'), NEW_PRICE)
