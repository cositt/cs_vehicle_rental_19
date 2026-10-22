# -*- coding: utf-8 -*-
"""Both websites offer every vehicle, whatever company owns it.

Sunset can rent Pinveco vehicles and the other way round, so the availability
of a category counts the vehicles of all companies. Occupied vehicles are only
those of the category asked for.
"""
import json
from datetime import date, timedelta

from odoo import fields
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'vehicle_website')
class TestWebsiteOffersAllCompanies(HttpCase):

    def setUp(self):
        super().setUp()
        self.env['vehicle.rental.delegation'].search([]).write({'active': False})
        sunset = self.env['res.company'].browse(1)
        other = self.env['res.company'].create({'name': 'Compañía Hermana Test'})
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'AllCompBrand'})

        def category_with_model(name):
            category = self.env['fleet.vehicle.model.category'].create({'name': name})
            model = self.env['fleet.vehicle.model'].create({
                'name': name, 'brand_id': brand.id, 'category_id': category.id})
            return category, model

        self.category, model = category_with_model('Tipo A - Todas las compañías')
        other_category, other_model = category_with_model('Tipo B - Todas las compañías')
        Vehicle = self.env['fleet.vehicle']
        for plate, company in (('ALL-S1', sunset), ('ALL-O1', other), ('ALL-O2', other)):
            Vehicle.create({'model_id': model.id, 'category_id': self.category.id,
                            'license_plate': plate, 'status': 'available', 'company_id': company.id})
        busy_elsewhere = Vehicle.create({
            'model_id': other_model.id, 'category_id': other_category.id,
            'license_plate': 'ALL-B1', 'status': 'available', 'company_id': sunset.id})
        self.start = date.today() + timedelta(days=40)
        customer = self.env['res.partner'].create({'name': 'Cliente Todas Compañías'})
        self.env['vehicle.contract'].create({
            'customer_id': customer.id, 'vehicle_id': busy_elsewhere.id, 'rent_type': 'days',
            'rent': 50.0,
            'start_date': fields.Datetime.to_datetime(self.start) + timedelta(hours=9),
            'end_date': fields.Datetime.to_datetime(self.start) + timedelta(days=2, hours=9),
        })

    def _available(self):
        response = self.url_open('/web/get-available-vehicles', data={
            'category_id': self.category.id, 'location': '',
            'start_date': self.start.isoformat(),
            'end_date': (self.start + timedelta(days=2)).isoformat(),
        })
        return json.loads(response.text)

    def test_counts_vehicles_of_every_company(self):
        result = self._available()
        self.assertEqual(result.get('total'), 3, result)

    def test_occupied_only_counts_the_category_asked_for(self):
        result = self._available()
        self.assertEqual(result.get('occupied'), 0, result)
        self.assertEqual(result.get('available'), 3, result)
