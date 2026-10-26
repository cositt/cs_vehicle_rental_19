# -*- coding: utf-8 -*-
"""New customers are created as a person.

The «Clientes» menu used the Contacts action, whose context creates companies.
Most customers are private people, so staff left them as companies
(production, 2026-10-26: a person with a DNI created as a company).
"""
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged('post_install', '-at_install', 'vehicle_customers_menu')
class TestCustomersMenu(TransactionCase):

    def test_customers_menu_creates_people(self):
        action = self.env.ref('vehicle_rental.menu_fleet_vehicle_customer').action
        self.assertEqual(action.res_model, 'res.partner')
        context = safe_eval(action.context or '{}')
        self.assertFalse(context.get('default_is_company', False))

    def test_new_contact_from_the_menu_is_a_person(self):
        action = self.env.ref('vehicle_rental.menu_fleet_vehicle_customer').action
        context = safe_eval(action.context or '{}')
        partner = self.env['res.partner'].with_context(**context).create({'name': 'Particular Menú'})
        self.assertFalse(partner.is_company)
