# -*- coding: utf-8 -*-
"""Authorized driver: optional, a contact of the customer, warned at hand-over.

The driver is not required to book or to save a contract and no longer has to
be an employee. A driver created from the contract becomes a child contact of
the customer company and brings its licence data to the contract. Handing the
vehicle over without a driver asks for confirmation first.
"""
from datetime import date

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import tagged

from .common import VehicleRentalCase


class DriverCase(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_customer = cls.env['res.partner'].create({
            'name': 'Construcciones Prueba SL', 'is_company': True, 'vat': 'ESB00000000'})
        cls.driver = cls.env['res.partner'].create({
            'name': 'Pedro Conductor', 'parent_id': cls.company_customer.id,
            'driver_identity_number': '00000000T', 'driver_license_number': 'B-123456',
            'driver_license_issue_date': date(2010, 5, 1),
            'driver_license_expiry_date': date(2030, 5, 1),
        })

    def _draft(self, **values):
        contract = self._create_contract(self.spare_vehicle, self.company_customer, status='a_draft')
        if values:
            contract.write(values)
        return contract


@tagged('post_install', '-at_install', 'vehicle_driver')
class TestDriverIsOptional(DriverCase):

    def test_contract_saves_without_driver(self):
        contract = self._draft()
        self.assertFalse(contract.authorized_driver_id)

    def test_vehicle_driver_need_not_be_an_employee(self):
        self.assertFalse(self.driver.employee_ids)
        self.spare_vehicle.driver_id = self.driver
        self.assertEqual(self.spare_vehicle.driver_id, self.driver)


@tagged('post_install', '-at_install', 'vehicle_driver')
class TestDriverIsACustomerContact(DriverCase):

    def test_driver_choice_is_limited_to_the_customer_and_its_contacts(self):
        stranger = self.env['res.partner'].create({'name': 'Persona Ajena'})
        contract = self._draft()
        allowed = self.env['res.partner'].search(contract._authorized_driver_domain())
        self.assertIn(self.driver, allowed)
        self.assertIn(self.company_customer, allowed)
        self.assertNotIn(stranger, allowed)

    def test_driver_created_from_the_contract_is_a_child_of_the_customer(self):
        contract = self._draft()
        context = contract._authorized_driver_creation_context()
        new_driver = self.env['res.partner'].with_context(**context).create({'name': 'Ana Nueva'})
        self.assertEqual(new_driver.parent_id, self.company_customer)
        self.assertFalse(new_driver.is_company)
        self.assertIn(new_driver, self.company_customer.child_ids)

    def test_form_offers_quick_creation_under_the_customer(self):
        arch = self.env['vehicle.contract'].get_view(view_type='form')['arch']
        self.assertIn('name="authorized_driver_id"', arch)
        self.assertIn('default_parent_id', arch)

    def test_choosing_the_driver_brings_its_licence(self):
        form = Form(self._draft())
        form.authorized_driver_id = self.driver
        self.assertEqual(form.driver_license_number, 'B-123456')
        self.assertEqual(form.driver_license_issue_date, date(2010, 5, 1))
        self.assertEqual(form.driver_license_expiry_date, date(2030, 5, 1))

    def test_driver_written_by_code_also_brings_its_licence(self):
        contract = self._draft(authorized_driver_id=self.driver.id)
        self.assertEqual(contract.driver_license_number, 'B-123456')

    def test_licence_typed_in_the_contract_is_kept(self):
        contract = self._draft(driver_license_number='TECLEADO')
        contract.authorized_driver_id = self.driver
        self.assertEqual(contract.driver_license_number, 'TECLEADO')


@tagged('post_install', '-at_install', 'vehicle_driver')
class TestHandOverWithoutDriver(DriverCase):

    def test_hand_over_without_driver_asks_first(self):
        contract = self._draft()
        action = contract.a_draft_to_b_in_progress()
        self.assertEqual(action['res_model'], 'vehicle.contract.driver.confirm')
        self.assertEqual(contract.status, 'a_draft')

    def test_confirming_hands_the_vehicle_over(self):
        contract = self._draft()
        action = contract.a_draft_to_b_in_progress()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        self.assertEqual(wizard.contract_ids, contract)
        wizard.action_confirm()
        self.assertEqual(contract.status, 'b_in_progress')

    def test_hand_over_with_driver_does_not_ask(self):
        contract = self._draft(authorized_driver_id=self.driver.id)
        action = contract.a_draft_to_b_in_progress()
        self.assertNotEqual(action.get('res_model'), 'vehicle.contract.driver.confirm')
        self.assertEqual(contract.status, 'b_in_progress')

    def test_blocking_errors_come_before_the_driver_warning(self):
        contract = self._draft()
        contract.rent_type = False
        with self.assertRaises(UserError):
            contract.a_draft_to_b_in_progress()


@tagged('post_install', '-at_install', 'vehicle_driver')
class TestDriverInContractPdf(DriverCase):

    def _html(self, contract):
        html, _type = self.env['ir.actions.report']._render_qweb_html(
            'vehicle_rental.vehicle_contract_report_template', contract.ids)
        return html.decode()

    def test_pdf_shows_the_driver_and_licence(self):
        html = self._html(self._draft(authorized_driver_id=self.driver.id))
        for value in ('Conductor autorizado', 'Pedro Conductor', '00000000T', 'B-123456'):
            self.assertIn(value, html)

    def test_pdf_uses_the_driver_dni_not_the_company_vat(self):
        self.assertEqual(self.driver.vat, 'ESB00000000', 'a company contact inherits the company VAT')
        html = self._html(self._draft(authorized_driver_id=self.driver.id))
        driver_row = html[html.index('Conductor autorizado'):]
        self.assertIn('00000000T', driver_row[:3000])

    def test_pdf_without_driver_says_so(self):
        html = self._html(self._draft())
        self.assertIn('Conductor autorizado', html)
        self.assertIn('Sin asignar', html)
