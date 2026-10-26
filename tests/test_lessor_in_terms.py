# -*- coding: utf-8 -*-
"""The contract PDF names the owner of the vehicle as the lessor.

Prod, 2026-10-26: a Pinveco van had Pinveco's letterhead but the terms said
"Málaga Sunset SL, en adelante el arrendador": Pinveco's terms were a copy of
Sunset's. The letterhead and terms already follow the owner of the vehicle.
"""
import importlib.util
from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_contract_company')
class TestLessorInTerms(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sunset = cls.env.company
        cls.sister = cls.env['res.company'].create({'name': 'Hermana Titular Test', 'vat': 'B00000000'})

    def test_migration_fixes_the_lessor_in_copied_terms(self):
        terms = self.env['rental.agreement.terms'].create({
            'name': 'Términos', 'company_id': self.sister.id,
            'rental_terms': '<p>TÉRMINOS Málaga&nbsp;Sunset&nbsp;SL en adelante, “el arrendador”</p>'})
        own = self.env['rental.agreement.terms'].create({
            'name': 'Términos', 'company_id': self.sunset.id,
            'rental_terms': '<p>Málaga Sunset SL en adelante, “el arrendador”</p>'})
        path = file_path('vehicle_rental/migrations/19.0.6.30/post-migrate.py')
        spec = importlib.util.spec_from_file_location('vehicle_lessor_fix', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.fix_lessor_in_terms(self.env, sunset=self.sunset)
        self.assertNotIn('Sunset', terms.rental_terms)
        self.assertIn('Hermana Titular Test', terms.rental_terms)
        self.assertIn('B00000000', terms.rental_terms)
        self.assertIn('Sunset', own.rental_terms, 'the terms of Sunset are left alone')
