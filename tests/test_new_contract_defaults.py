# -*- coding: utf-8 -*-
"""What a new contract fills on its own.

Feedback from the counter (Jesús Muñoz, 2026-10-22): choosing the customer left
DNI and address empty, an expired licence went unnoticed, the payment type and
the fuel had to be ticked by hand although they are always the same.
"""
from datetime import date, timedelta

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import tagged

from .common import FUEL_FULL, VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_new_contract')
class TestNewContractDefaults(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.person = cls.env['res.partner'].create({
            'name': 'Cliente Particular Pruebas',
            'vat': '12345678Z',
            'street': 'C/ Mayor, 1',
            'zip': '29001',
            'city': 'Málaga',
            'driver_license_number': 'B-998877',
            'driver_license_issue_date': date(2005, 3, 1),
            'driver_license_expiry_date': date(2035, 3, 1),
        })
        cls.firm = cls.env['res.partner'].create({
            'name': 'Empresa Cliente Pruebas SL', 'is_company': True,
            'vat': 'B12345674', 'street': 'Pol. Ind. Sur, 4', 'zip': '41001', 'city': 'Sevilla',
        })

    def _contract_vals(self, customer, **extra):
        return dict({'customer_id': customer.id, 'vehicle_id': self.spare_vehicle.id,
                     'rent_type': 'days', 'rent': 50.0,
                     'start_date': self.start_date, 'end_date': self.end_date}, **extra)

    # Punto 1: los datos del cliente
    def test_choosing_the_customer_fills_dni_address_and_licence(self):
        contract = self.env['vehicle.contract'].new({})
        contract.customer_id = self.person
        contract.onchange_customer_details()
        self.assertEqual(contract.customer_dni, '12345678Z')
        self.assertEqual(contract.customer_address, 'C/ Mayor, 1, 29001 Málaga')
        self.assertEqual(contract.driver_license_number, 'B-998877')
        self.assertEqual(contract.driver_license_expiry_date, date(2035, 3, 1))

    def test_company_customer_fills_its_cif_and_address(self):
        contract = self.env['vehicle.contract'].new({})
        contract.customer_id = self.firm
        contract.onchange_customer_details()
        self.assertEqual(contract.customer_dni, 'B12345674')
        self.assertEqual(contract.customer_address, 'Pol. Ind. Sur, 4, 41001 Sevilla')

    def test_driver_dni_wins_over_the_inherited_company_vat(self):
        employee = self.env['res.partner'].create({
            'name': 'Empleado Pruebas', 'parent_id': self.firm.id,
            'driver_identity_number': '87654321X'})
        contract = self.env['vehicle.contract'].new({})
        contract.customer_id = employee
        contract.onchange_customer_details()
        self.assertEqual(contract.customer_dni, '87654321X')

    def test_contract_created_without_the_form_also_gets_them(self):
        """The booking wizard creates the contract straight away, without onchange."""
        contract = self.env['vehicle.contract'].create(self._contract_vals(self.person))
        self.assertEqual(contract.customer_dni, '12345678Z')
        self.assertEqual(contract.customer_address, 'C/ Mayor, 1, 29001 Málaga')
        self.assertEqual(contract.driver_license_number, 'B-998877')

    def test_what_the_clerk_typed_is_kept(self):
        contract = self.env['vehicle.contract'].create(
            self._contract_vals(self.person, customer_dni='OTRO-DNI', customer_address='Otra calle'))
        self.assertEqual(contract.customer_dni, 'OTRO-DNI')
        self.assertEqual(contract.customer_address, 'Otra calle')

    # Punto 3: aviso de carnet o DNI caducado
    def test_licence_expiring_before_the_return_is_flagged(self):
        contract = self.env['vehicle.contract'].create(self._contract_vals(
            self.customer, driver_license_expiry_date=fields.Date.today() + timedelta(days=2)))
        self.assertTrue(contract.driver_license_expired)
        self.assertFalse(contract.customer_dni_expired)

    def test_valid_licence_is_not_flagged(self):
        contract = self.env['vehicle.contract'].create(self._contract_vals(self.person))
        self.assertFalse(contract.driver_license_expired)

    def test_expired_dni_is_flagged(self):
        contract = self.env['vehicle.contract'].create(self._contract_vals(
            self.customer, customer_dni_expiry_date=fields.Date.today() - timedelta(days=1)))
        self.assertTrue(contract.customer_dni_expired)

    def test_onchange_warns_about_the_expired_licence(self):
        contract = self.env['vehicle.contract'].new(self._contract_vals(self.customer))
        contract.driver_license_expiry_date = fields.Date.today() - timedelta(days=30)
        warning = contract._onchange_document_expiry()
        self.assertIn('carnet', warning['warning']['message'])

    def test_form_shows_the_expiry_alerts(self):
        arch = self.env['vehicle.contract'].get_view(view_type='form')['arch']
        self.assertIn('driver_license_expired', arch)
        self.assertIn('customer_dni_expired', arch)

    # Punto 9: tipo de pago
    def test_payment_type_defaults_to_full_payment(self):
        contract = self.env['vehicle.contract'].create(self._contract_vals(self.customer))
        self.assertEqual(contract.payment_type, 'full_payment')

    def test_flexirent_proposes_monthly_payment(self):
        contract = self.env['vehicle.contract'].new(self._contract_vals(self.customer))
        contract.pricing_type = 'flexirent'
        contract._onchange_pricing_type_payment()
        self.assertEqual(contract.payment_type, 'monthly')

    # Punto 24: combustible
    def test_fuel_is_handed_over_full_by_default(self):
        contract = self.env['vehicle.contract'].create(self._contract_vals(self.customer))
        self.assertEqual(contract.initial_fuel_level, FUEL_FULL)

    # Punto 6: «Conductor requerido» es un chófer de la empresa
    def test_driver_required_label_says_chauffeur(self):
        field = self.env['vehicle.contract']._fields['is_driver_required']
        self.assertIn('chófer', field._description_string(self.env).lower())

    # Punto 8: el seguro básico va incluido en la tarifa (alquilerpinveco.com)
    def test_basic_insurance_is_shown_as_included(self):
        arch = self.env['vehicle.contract'].get_view(view_type='form')['arch']
        self.assertIn('Incluido en la tarifa', arch)
