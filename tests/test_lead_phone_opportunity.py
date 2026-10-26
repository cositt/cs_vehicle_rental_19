# -*- coding: utf-8 -*-
"""A phone opportunity becomes a contract.

Prod, 2026-10-26: an opportunity created in the pipeline with a vehicle lost
the "Ganado" button and "Crear Contrato" only showed at 100 % probability;
the wizard had no kilometre package, the contract took "100 km" (a 4-hour
tariff only) and failed with "El precio por día debe ser mayor que cero".
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_lead_phone')
class TestLeadPhoneOpportunity(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Rule = cls.env['vehicle.pricing.rule']
        today = fields.Date.today()
        Rule.create({'vehicle_category_id': cls.category.id, 'pricing_type': 'standard', 'km_range': '100',
                     'duration_range': '4h', 'price_per_unit': 40.0, 'valid_from': today})
        Rule.create({'vehicle_category_id': cls.category.id, 'pricing_type': 'standard', 'km_range': '350',
                     'duration_range': '1-2d', 'price_per_unit': 75.0, 'valid_from': today})
        Rule.create({'vehicle_category_id': cls.category.id, 'pricing_type': 'standard', 'km_range': '500',
                     'duration_range': '1-2d', 'price_per_unit': 85.0, 'valid_from': today})
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Llamada', 'partner_id': cls.customer.id, 'type': 'opportunity',
            'probability': 10, 'vehicle_id': cls.spare_vehicle.id,
            'start_date': (cls.now + timedelta(days=20)).date(),
            'end_date': (cls.now + timedelta(days=22)).date()})

    def _wizard(self):
        return self.env['lead.rental.contract'].with_context(active_id=self.lead.id).create({})

    def test_contract_button_does_not_need_100_percent(self):
        self.assertTrue(self.lead.can_create_contract)

    def test_wizard_shows_the_vehicle_category(self):
        self.assertEqual(self._wizard().selected_category_id, self.category)

    def test_wizard_proposes_a_km_package_with_tariff(self):
        self.assertEqual(self._wizard().km_range, '350')

    def test_phone_opportunity_becomes_a_contract_with_tariff_price(self):
        wizard = self._wizard()
        action = wizard.action_create_rental_contract()
        contract = self.env['vehicle.contract'].browse(action['res_id'])
        self.assertEqual(contract.km_range, '350')
        self.assertEqual(contract.rent, 75.0)
        self.assertEqual(self.lead.contract_id, contract)
        self.assertEqual(self.lead.probability, 100)
        self.assertFalse(self.lead.can_create_contract)

    def test_chosen_km_package_is_kept(self):
        wizard = self._wizard()
        wizard.km_range = '500'
        contract = self.env['vehicle.contract'].browse(wizard.action_create_rental_contract()['res_id'])
        self.assertEqual(contract.rent, 85.0)
