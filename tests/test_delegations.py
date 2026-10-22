# -*- coding: utf-8 -*-
"""Delegations: where vehicles are picked up and dropped off.

The customer creates its own delegations (nothing is preloaded). Every vehicle
has a company and a delegation; one without them can still be rented and gets
them when it is handed over (company of the contract, pick-up delegation).
Returning moves it to the drop-off delegation. Searching covers every
delegation: if the vehicle is elsewhere, the pick-up becomes its delegation.
"""
from datetime import timedelta

from odoo.tests import Form
from odoo.tests.common import tagged

from .common import VehicleRentalCase


class DelegationCase(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Delegation = cls.env['vehicle.rental.delegation']
        cls.cordoba = Delegation.create({
            'name': 'Córdoba', 'street': 'C/ Imprenta de la Alborada, nave 2',
            'zip': '14014', 'city': 'Córdoba', 'phone': '957 322 664',
            'email': 'cordoba@empresa.test', 'schedule': 'L-V 8-14 y 16-19',
        })
        cls.malaga = Delegation.create({
            'name': 'Málaga', 'street': 'C/ Marea Baja, 51, nave 2',
            'zip': '29006', 'city': 'Málaga', 'phone': '951 334 559',
            'email': 'malaga@empresa.test', 'schedule': 'L-V 7-19',
        })
        cls.other_company = cls.env['res.company'].create({'name': 'Otra Compañía Test'})
        cls.env.user.company_ids |= cls.other_company


@tagged('post_install', '-at_install', 'vehicle_delegation')
class TestDelegationModel(DelegationCase):

    def test_archived_delegation_is_not_offered(self):
        self.malaga.active = False
        offered = self.env['vehicle.rental.delegation'].search([])
        self.assertIn(self.cordoba, offered)
        self.assertNotIn(self.malaga, offered)

    def test_delegation_has_no_company(self):
        self.assertNotIn('company_id', self.env['vehicle.rental.delegation']._fields)

    def test_vehicle_form_shows_company_and_delegation(self):
        arch = self.env['fleet.vehicle'].get_view(view_type='form')['arch']
        self.assertIn('name="delegation_id"', arch)
        self.assertIn('name="company_id"', arch)

    def test_choosing_a_delegation_fills_the_address(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        form = Form(contract)
        form.pick_up_delegation_id = self.cordoba
        form.drop_off_delegation_id = self.malaga
        self.assertEqual(form.pick_up_street, 'C/ Imprenta de la Alborada, nave 2')
        self.assertEqual(form.pick_up_zip, '14014')
        self.assertEqual(form.pick_up_city, 'Córdoba')
        self.assertEqual(form.drop_off_city, 'Málaga')
        form.pick_up_street = 'Recogida en la obra'  # still editable
        self.assertEqual(form.pick_up_street, 'Recogida en la obra')

    def test_vehicle_sets_the_default_pick_up(self):
        self.spare_vehicle.delegation_id = self.cordoba
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        self.assertEqual(contract.pick_up_delegation_id, self.cordoba)
        self.assertEqual(contract.pick_up_city, 'Córdoba')


@tagged('post_install', '-at_install', 'vehicle_delegation')
class TestDelegationBookingWizard(DelegationCase):

    def setUp(self):
        super().setUp()
        start = self.now + timedelta(days=30)
        self.at_cordoba = self._create_vehicle('DEL-CORD')
        self.at_cordoba.delegation_id = self.cordoba
        self.at_malaga = self._create_vehicle('DEL-MALA')
        self.at_malaga.delegation_id = self.malaga
        self.nowhere = self._create_vehicle('DEL-NONE')
        self.nowhere.company_id = False
        self.other = self._create_vehicle('DEL-OTRA')
        self.other.company_id = self.other_company
        self.env['vehicle.pricing.rule'].create({
            'vehicle_category_id': self.category.id, 'pricing_type': 'standard',
            'km_range': '350', 'duration_range': '3-5d', 'price_per_unit': 75.0,
            'valid_from': (self.now - timedelta(days=1)).date(),
        })
        self.wizard = self.env['rental.contract.booking'].with_context(
            allowed_company_ids=(self.company | self.other_company).ids,
        ).create({
            'customer_id': self.customer.id,
            'selected_category_id': self.category.id,
            'start_date': start,
            'end_date': start + timedelta(days=3),
            'delegation_id': self.malaga.id,
            'duration_range': '3-5d',
            'km_range': '350',
        })

    def _offered(self, **values):
        self.wizard.write(values)
        self.wizard._onchange_available_vehicle()
        return self.wizard.fleet_vehicle_ids

    def test_search_covers_every_delegation_and_company(self):
        offered = self._offered()
        for vehicle in (self.at_cordoba, self.at_malaga, self.nowhere, self.other):
            self.assertIn(vehicle, offered)

    def test_only_this_delegation_keeps_vehicles_without_delegation(self):
        offered = self._offered(only_delegation=True)
        self.assertIn(self.at_malaga, offered)
        self.assertIn(self.nowhere, offered)
        self.assertNotIn(self.at_cordoba, offered)

    def test_vehicle_elsewhere_moves_the_pick_up(self):
        action = self.wizard.action_create_contract_for_vehicle(self.at_cordoba.id)
        contract = self.env['vehicle.contract'].browse(action['res_id'])
        self.assertEqual(contract.pick_up_delegation_id, self.cordoba)
        self.assertEqual(contract.drop_off_delegation_id, self.malaga)
        self.assertEqual(contract.pick_up_city, 'Córdoba')

    def test_vehicle_without_delegation_is_picked_up_where_asked(self):
        action = self.wizard.action_create_contract_for_vehicle(self.nowhere.id)
        contract = self.env['vehicle.contract'].browse(action['res_id'])
        self.assertEqual(contract.pick_up_delegation_id, self.malaga)


@tagged('post_install', '-at_install', 'vehicle_delegation')
class TestDelegationHandOverAndReturn(DelegationCase):

    def setUp(self):
        super().setUp()
        self.bare = self._create_vehicle('DEL-BARE')
        self.bare.company_id = False
        self.draft = self._create_contract(self.bare, self.customer, status='a_draft')
        self.draft.write({'pick_up_delegation_id': self.cordoba.id,
                          'drop_off_delegation_id': self.malaga.id})

    def test_hand_over_gives_company_and_delegation(self):
        self.draft.a_draft_to_b_in_progress()
        self.assertEqual(self.draft.status, 'b_in_progress')
        self.assertEqual(self.bare.company_id, self.draft.company_id)
        self.assertEqual(self.bare.delegation_id, self.cordoba)

    def test_hand_over_keeps_what_the_vehicle_already_has(self):
        self.bare.write({'company_id': self.other_company.id, 'delegation_id': self.malaga.id})
        self.draft.a_draft_to_b_in_progress()
        self.assertEqual(self.bare.company_id, self.other_company)
        self.assertEqual(self.bare.delegation_id, self.malaga)

    def test_return_moves_the_vehicle_to_the_drop_off(self):
        self.draft.write({'status': 'b_in_progress'})
        self.draft._apply_return()
        self.assertEqual(self.bare.delegation_id, self.malaga)
        self.assertEqual(self.bare.company_id, self.draft.company_id)
        self.assertEqual(self.bare.location, 'Málaga')
