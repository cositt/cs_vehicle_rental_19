# -*- coding: utf-8 -*-
"""Each company invoices its own vehicles.

Juan, 2026-10-26: a contract for a Pinveco van stayed in the company the clerk
was acting for (Sunset), so Sunset invoiced a Pinveco van. "Que cada compañía
facture lo suyo": the contract goes to the company that owns the vehicle.
Taxes, journals and accounts of a company are only usable while it is active
in the company switcher, so the staff work with both companies ticked; with
only one ticked they get a clear message instead of an access error.
"""
from odoo.exceptions import UserError
from odoo.tests.common import new_test_user, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_contract_owner')
class TestContractCompanyIsVehicleOwner(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sunset = cls.env.company
        cls.owner = cls.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '!=', cls.sunset.id)], limit=1).company_id
        cls.owner_vehicle = cls._create_vehicle('DUE-0001', odometer=100)
        cls.owner_vehicle.company_id = cls.owner
        cls.clerk = new_test_user(
            cls.env, login='mostrador_sunset',
            groups='base.group_user,fleet.fleet_group_manager,account.group_account_manager,hr_expense.group_hr_expense_manager',
            company_id=cls.sunset.id, company_ids=[cls.sunset.id, cls.owner.id])

    def setUp(self):
        super().setUp()
        self.assertTrue(self.owner, 'needs a second company with a sales journal')

    def _as_clerk(self, model, companies=None):
        companies = companies or [self.sunset.id, self.owner.id]
        return self.env[model].with_user(self.clerk).with_context(allowed_company_ids=companies)

    def _contract_vals(self, vehicle):
        return {'customer_id': self.customer.id, 'vehicle_id': vehicle.id,
                'rent_type': 'days', 'rent': 50.0,
                'start_date': self.start_date, 'end_date': self.end_date}

    def _create_as_clerk(self, vehicle):
        return self._as_clerk('vehicle.contract').create(self._contract_vals(vehicle))

    def test_contract_goes_to_the_owner_of_the_vehicle(self):
        self.assertEqual(self._create_as_clerk(self.owner_vehicle).company_id, self.owner)

    def test_contract_takes_the_vat_of_the_owner(self):
        contract = self._create_as_clerk(self.owner_vehicle)
        self.assertEqual(contract.tax_ids, self.owner._vehicle_rental_sale_tax())

    def test_vehicle_of_the_main_company_stays_there(self):
        self.assertEqual(self._create_as_clerk(self.spare_vehicle).company_id, self.sunset)

    def test_changing_the_vehicle_in_draft_moves_the_contract(self):
        contract = self._create_as_clerk(self.spare_vehicle)
        contract.write({'vehicle_id': self.owner_vehicle.id})
        self.assertEqual(contract.company_id, self.owner)
        self.assertEqual(contract.tax_ids, self.owner._vehicle_rental_sale_tax())

    def test_onchange_shows_the_owner_before_saving(self):
        contract = self._as_clerk('vehicle.contract').new({'customer_id': self.customer.id})
        contract.vehicle_id = self.owner_vehicle
        contract._onchange_vehicle_owner_company()
        self.assertEqual(contract.company_id, self.owner)

    def test_invoice_of_the_contract_is_from_the_owner(self):
        contract = self._create_as_clerk(self.owner_vehicle)
        invoice = self._as_clerk('account.move').create({
            'move_type': 'out_invoice', 'partner_id': self.customer.id,
            'vehicle_contract_id': contract.id,
            'invoice_line_ids': [(0, 0, {'name': 'Cuota', 'price_unit': 10.0, 'tax_ids': False})]})
        self.assertEqual(invoice.company_id, self.owner)

    def test_vehicle_expense_goes_to_the_owner(self):
        expense = self._as_clerk('hr.expense').create({
            'name': 'Lavado', 'fleet_vehicle_id': self.owner_vehicle.id,
            'total_amount_currency': 30.0, 'employee_id': False, 'employee_name': 'Pepe'})
        self.assertEqual(expense.company_id, self.owner)

    def test_with_only_one_company_ticked_the_message_is_clear(self):
        Contract = self._as_clerk('vehicle.contract', [self.sunset.id])
        with self.assertRaisesRegex(UserError, 'selector de compañías'):
            Contract.create(self._contract_vals(self.owner_vehicle))
        contract = Contract.new({'customer_id': self.customer.id, 'status': 'a_draft'})
        contract.vehicle_id = self.owner_vehicle
        warning = contract._onchange_vehicle_owner_company()
        self.assertIn('selector de compañías', warning['warning']['message'])

    def test_website_bookings_go_to_the_owner(self):
        public = self.env.ref('base.public_user')
        contract = self.env['vehicle.contract'].with_user(public).sudo().create(
            self._contract_vals(self.owner_vehicle))
        self.assertEqual(contract.company_id, self.owner)
