# -*- coding: utf-8 -*-
"""Public pages list the active delegations of the model, nothing invented."""
import json
from datetime import date, timedelta

from odoo.tests.common import HttpCase, tagged

INVENTED = ('Madrid', 'Barcelona', 'Valencia', 'Alcalá, 200', 'Diagonal, 500')


@tagged('post_install', '-at_install', 'vehicle_website')
class TestWebsiteDelegations(HttpCase):

    def setUp(self):
        super().setUp()
        Delegation = self.env['vehicle.rental.delegation']
        Delegation.search([]).write({'active': False})  # only the delegations of the test
        self.cordoba = Delegation.create({
            'name': 'Córdoba', 'street': 'Pol. Ind. Las Quemadas, nave 2', 'zip': '14014',
            'city': 'Córdoba', 'phone': '957 322 664', 'email': 'cordoba@empresa.test',
            'schedule': 'L-V 8-14 y 16-19 · S 9-13',
        })
        self.sevilla = Delegation.create({
            'name': 'Sevilla', 'street': 'Av. Fernández Morube, 36 B', 'zip': '41007',
            'city': 'Sevilla', 'phone': '955 521 051', 'email': 'sevilla@empresa.test',
        })

    def test_pinveco_home_lists_the_active_delegations(self):
        self.sevilla.active = False
        html = self.url_open('/pinveco').text
        for value in ('Córdoba', '957 322 664', 'cordoba@empresa.test', 'L-V 8-14 y 16-19'):
            self.assertIn(value, html)
        self.assertNotIn('955 521 051', html, 'an archived delegation is not shown')
        for fake in INVENTED:
            self.assertNotIn(fake, html)

    def test_old_delegation_links_do_not_break(self):
        response = self.url_open('/pinveco/delegacion/madrid', allow_redirects=False)
        self.assertIn(response.status_code, (301, 302, 303, 404))

    def test_contact_page_lists_the_delegations(self):
        html = self.url_open('/contactus').text
        self.assertIn('957 322 664', html)
        self.assertIn('955 521 051', html)


@tagged('post_install', '-at_install', 'vehicle_website')
class TestWebsiteAvailabilityByDelegation(HttpCase):

    def setUp(self):
        super().setUp()
        company = self.env['res.company'].browse(1)
        self.category = self.env['fleet.vehicle.model.category'].create({'name': 'Tipo A - Prueba delegaciones web'})
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'WebDelegBrand'})
        model = self.env['fleet.vehicle.model'].create({
            'name': 'WebDelegModel', 'brand_id': brand.id, 'category_id': self.category.id})
        Delegation = self.env['vehicle.rental.delegation']
        Delegation.search([]).write({'active': False})  # only the delegations of the test
        self.cordoba = Delegation.create({'name': 'Córdoba', 'city': 'Córdoba'})
        self.malaga = Delegation.create({'name': 'Málaga', 'city': 'Málaga'})
        for plate, delegation in (('WEB-C1', self.cordoba), ('WEB-C2', self.cordoba),
                                  ('WEB-M1', self.malaga), ('WEB-N1', False)):
            self.env['fleet.vehicle'].create({
                'model_id': model.id, 'category_id': self.category.id, 'license_plate': plate,
                'status': 'available', 'company_id': company.id,
                'delegation_id': delegation and delegation.id,
            })

    def _available(self, location):
        start = date.today() + timedelta(days=40)
        response = self.url_open('/web/get-available-vehicles', data={
            'category_id': self.category.id, 'location': location,
            'start_date': start.isoformat(), 'end_date': (start + timedelta(days=2)).isoformat(),
        })
        return json.loads(response.text)

    def test_location_options_are_the_delegations(self):
        html = self.url_open('/web/vehicle-detail/%s' % self.category.id).text
        self.assertIn('<option value="Córdoba">Córdoba</option>', html)
        self.assertIn('<option value="Málaga">Málaga</option>', html)

    def test_counts_use_the_delegation_and_vehicles_without_one(self):
        result = self._available('Córdoba')
        self.assertEqual(result.get('total'), 3, result)
        result = self._available('Málaga')
        self.assertEqual(result.get('total'), 2, result)
