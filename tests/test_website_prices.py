# -*- coding: utf-8 -*-
"""Prices and texts shown on the public website.

Found in the Phase 7 regression:
- /pinveco/flota showed "€45/día" for every van: a number written in the
  code, not a tariff;
- the vehicle page showed prices as "€50.0";
- the footer of every page read "Copyright © Company name".
"""
import re

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'vehicle_website_prices')
class TestWebsitePrices(HttpCase):

    def _page(self, url):
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200, url)
        return response.text

    def test_fleet_price_comes_from_the_tariffs(self):
        html = self._page('/pinveco/flota')
        self.assertNotIn('€45/día', html)
        Rule = self.env['vehicle.pricing.rule']
        category = self.env['fleet.vehicle'].search([('category_id', '!=', False)], limit=1).category_id
        cheapest = Rule._website_price_from(category)
        self.assertTrue(cheapest)
        self.assertIn(Rule._format_eur(cheapest), html)

    def test_vehicle_page_prices_are_formatted(self):
        category = self.env['vehicle.pricing.rule'].search([], limit=1).vehicle_category_id
        html = self._page(f'/web/vehicle-detail/{category.id}')
        self.assertFalse(re.search(r'€\d+\.\d\b', html), 'prices like "€50.0"')

    def test_footer_names_the_company(self):
        html = self._page('/')
        self.assertNotIn('Company name', html)
        self.assertIn(self.env['website'].get_current_website().company_id.name, html)

    def test_euro_format(self):
        self.assertEqual(self.env['vehicle.pricing.rule']._format_eur(1234.5), '1.234,50 €')
