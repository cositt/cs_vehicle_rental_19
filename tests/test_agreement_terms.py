# -*- coding: utf-8 -*-
"""Every contract carries the general terms of the company that signs it.

Found in the Phase 7 regression: the terms were only filled when someone
picked the agreement by hand, so most contracts were printed without general
terms. The vehicle owner signs (Juan, 2026-10-23), so its terms apply.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_agreement_terms')
class TestAgreementTerms(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = cls.env['res.company'].create({'name': 'Dueña Términos'})
        Terms = cls.env['rental.agreement.terms']
        cls.own_terms = Terms.create({'name': 'Condiciones propias', 'company_id': cls.company.id,
                                      'rental_terms': '<p>Condiciones de la compañía del contrato</p>'})
        cls.owner_terms = Terms.create({'name': 'Condiciones dueña', 'company_id': cls.owner.id,
                                        'rental_terms': '<p>Condiciones de la dueña</p>'})

    def _new_contract(self, vehicle):
        return self._create_contract(vehicle, self.customer, status='a_draft')

    def test_contract_takes_the_terms_of_the_vehicle_owner(self):
        self.spare_vehicle.company_id = self.owner
        contract = self._new_contract(self.spare_vehicle)
        self.assertEqual(contract.rental_agreement_terms_id, self.owner_terms)
        self.assertIn('Condiciones de la dueña', contract.rental_terms)

    def test_own_vehicle_takes_the_terms_of_the_company(self):
        contract = self._new_contract(self.spare_vehicle)
        self.assertEqual(contract.rental_agreement_terms_id.company_id, self.company)
        self.assertTrue(contract.rental_terms)

    def test_terms_chosen_by_hand_are_kept(self):
        contract = self.env['vehicle.contract'].create({
            'customer_id': self.customer.id, 'vehicle_id': self.spare_vehicle.id, 'rent_type': 'days',
            'rent': 50.0, 'start_date': self.start_date, 'end_date': self.end_date,
            'rental_agreement_terms_id': self.owner_terms.id, 'rental_terms': '<p>Pactadas</p>'})
        self.assertEqual(contract.rental_agreement_terms_id, self.owner_terms)
        self.assertIn('Pactadas', contract.rental_terms)

    def test_printed_contract_has_the_terms(self):
        contract = self._new_contract(self.spare_vehicle)
        html, _type = self.env['ir.actions.report']._render_qweb_html(
            'vehicle_rental.vehicle_contract_report_template', contract.ids)
        self.assertIn('Términos y Condiciones', html.decode())

    def test_migration_fills_the_existing_contracts(self):
        import importlib.util
        from odoo.tools.misc import file_path
        contract = self._new_contract(self.spare_vehicle)
        self.env.cr.execute("UPDATE vehicle_contract SET rental_agreement_terms_id = NULL, rental_terms = NULL"
                            " WHERE id = %s", [contract.id])
        self.env.invalidate_all()
        path = file_path('vehicle_rental/migrations/19.0.6.21/post-migrate.py')
        spec = importlib.util.spec_from_file_location('terms_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, '19.0.6.20')
        self.env.invalidate_all()
        self.assertEqual(contract.rental_agreement_terms_id.company_id, self.company)
        self.assertTrue(contract.rental_terms)
