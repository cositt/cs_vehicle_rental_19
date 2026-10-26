# -*- coding: utf-8 -*-
"""The driver of the contract ("Conductor requerido") can be anyone.

Juan, 2026-10-23, on prod: saving a contract with the renting company as its
own driver failed with "El conductor seleccionado debe ser uno de los
empleados permitidos". Any contact may drive; one typed in that does not
exist is created as a contact of the customer.
"""
from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_required_driver')
class TestRequiredDriver(VehicleRentalCase):

    def _contract(self):
        return self._create_contract(self.spare_vehicle, self.customer, status='a_draft')

    def test_customer_can_be_the_driver(self):
        contract = self._contract()
        contract.write({'is_driver_required': True, 'driver_id': self.customer.id,
                        'driver_charge_type': 'including', 'driver_charge': 0.0})
        self.assertEqual(contract.driver_id, self.customer)

    def test_any_person_can_be_the_driver(self):
        person = self.env['res.partner'].create({'name': 'Conductor Cualquiera Test'})
        contract = self._contract()
        contract.write({'is_driver_required': True, 'driver_id': person.id,
                        'driver_charge_type': 'including'})
        self.assertEqual(contract.driver_id, person)

    def test_charge_only_required_when_not_included(self):
        contract = self._contract()
        with self.assertRaisesRegex(ValidationError, 'cargo del conductor'):
            contract.write({'is_driver_required': True, 'driver_id': self.customer.id,
                            'driver_charge_type': 'excluding', 'driver_charge': 0.0})

    def test_new_driver_is_created_as_contact_of_the_customer(self):
        arch = self.env['vehicle.contract'].get_view(view_type='form')['arch']
        field = etree.fromstring(arch).xpath("//field[@name='driver_id']")[0]
        self.assertNotIn('no_create', field.get('options', ''))
        self.assertIn('default_parent_id', field.get('context', ''))

    def test_labels_are_spanish(self):
        fields = self.env['vehicle.contract'].with_context(lang='es_ES').fields_get(
            ['driver_id', 'is_driver_required', 'is_any_trip_expense'], ['string'])
        self.assertEqual(fields['driver_id']['string'], 'Conductor')
        # «Conductor requerido» se confundía con el conductor autorizado (Jesús Muñoz, 2026-10-22)
        self.assertEqual(fields['is_driver_required']['string'], 'Con chófer de la empresa')
        self.assertEqual(fields['is_any_trip_expense']['string'], 'Gastos de viaje')
