# -*- coding: utf-8 -*-
"""Fleet data as the office knows it.

Odoo 19 creates vehicle models as electric by default, so the imported vans
were all "Eléctrica". The website showed a blank card for a category without
picture.
"""
import importlib.util
import os

from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase

PICTURE_LETTERS = 'ABCDEFKTVWXZ'


@tagged('post_install', '-at_install', 'vehicle_fleet_data')
class TestFleetFuel(VehicleRentalCase):

    def test_new_model_is_diesel_by_default(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Marca Combustible'})
        model = self.env['fleet.vehicle.model'].create({'name': 'Furgón', 'brand_id': brand.id})
        self.assertEqual(model.default_fuel_type, 'diesel')

    def test_migration_fixes_imported_fuel_and_the_golf(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Marca Migración'})
        Model = self.env['fleet.vehicle.model']
        van = Model.create({'name': 'VITO FURGON 110CDI', 'brand_id': brand.id, 'default_fuel_type': 'electric'})
        petrol = Model.create({'name': 'FOCUS GASOLINA', 'brand_id': brand.id, 'default_fuel_type': 'electric'})
        hybrid = Model.create({'name': 'KUGA HIBRIDO', 'brand_id': brand.id, 'default_fuel_type': 'electric'})
        golf = Model.create({'name': 'GOLF', 'brand_id': brand.id, 'default_fuel_type': 'electric'})
        Category = self.env['fleet.vehicle.model.category']
        car_category = (Category.search([('name', '=like', 'Tipo G1%')], order='id', limit=1)
                        or Category.create({'name': 'Tipo G1 - Turismo'}))
        Vehicle = self.env['fleet.vehicle']
        vehicles = {
            model: Vehicle.create({'model_id': model.id, 'category_id': self.category.id,
                                   'license_plate': plate})
            for model, plate in ((van, 'MIG-0001'), (petrol, 'MIG-0002'), (hybrid, 'MIG-0003'),
                                 (golf, '4717MCJ'))
        }
        self.assertEqual(vehicles[van].fuel_type, 'electric')

        path = file_path('vehicle_rental/migrations/19.0.6.12/post-migrate.py')
        spec = importlib.util.spec_from_file_location('fleet_data_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.env.flush_all()
        migration.migrate(self.env.cr, '19.0.6.11')
        self.env.invalidate_all()

        self.assertEqual(van.default_fuel_type, 'diesel')
        self.assertEqual(vehicles[van].fuel_type, 'diesel')
        self.assertEqual(vehicles[petrol].fuel_type, 'gasoline')
        self.assertEqual(vehicles[hybrid].fuel_type, 'full_hybrid')
        self.assertEqual(vehicles[golf].category_id, car_category)


@tagged('post_install', '-at_install', 'vehicle_fleet_data')
class TestCategoryPictures(TransactionCase):

    def test_both_websites_have_every_picture_they_ask_for(self):
        for folder in ('tipos', 'tipos_pinveco'):
            directory = os.path.dirname(file_path(f'vehicle_rental/static/description/img/{folder}/tipoA.png'))
            names = set(os.listdir(directory))
            for letter in PICTURE_LETTERS:
                self.assertIn(f'tipo{letter}.png', names, f'{folder} misses tipo{letter}.png')


@tagged('post_install', '-at_install', 'vehicle_fleet_data')
class TestCategoryCardWithoutPicture(HttpCase):

    def test_category_without_picture_shows_an_icon(self):
        self.env['fleet.vehicle.model.category'].create({'name': 'Tipo Q - Sin foto'})
        html = self.url_open('/web/booking-enquiry').text
        card = html[:html.index('Tipo Q - Sin foto')]
        card = card[card.rindex('category-card'):]
        self.assertNotIn('<img', card)
        self.assertIn('fa-car', card)
        self.assertNotIn('display: none', card)
