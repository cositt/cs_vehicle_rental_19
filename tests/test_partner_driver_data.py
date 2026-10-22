# -*- coding: utf-8 -*-
"""Customers keep their birth date and driving licence on the contact.

Pinveco's customer list carries them for ~27.000 people; the contract and the
authorised driver (phase 6) read them from the contact.
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

DRIVER_FIELDS = ('birth_date', 'driver_license_number',
                 'driver_license_issue_date', 'driver_license_expiry_date')


@tagged('post_install', '-at_install', 'vehicle_partner')
class TestPartnerDriverData(TransactionCase):

    def test_contact_stores_birth_date_and_licence(self):
        partner = self.env['res.partner'].create({
            'name': 'Conductor Prueba',
            'birth_date': date(1980, 5, 17),
            'driver_license_number': 'B-12345678',
            'driver_license_issue_date': date(1999, 1, 10),
            'driver_license_expiry_date': date(2029, 1, 10),
        })
        self.assertEqual(partner.birth_date, date(1980, 5, 17))
        self.assertEqual(partner.driver_license_number, 'B-12345678')

    def test_licence_cannot_expire_before_it_is_issued(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Carnet imposible',
                'driver_license_issue_date': date(2020, 1, 1),
                'driver_license_expiry_date': date(2010, 1, 1),
            })

    def test_fields_are_on_the_contact_form(self):
        arch = self.env['res.partner'].get_view(view_type='form')['arch']
        for field in DRIVER_FIELDS:
            with self.subTest(field=field):
                self.assertIn(f'name="{field}"', arch)
