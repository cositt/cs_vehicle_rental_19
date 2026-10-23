# -*- coding: utf-8 -*-
"""Return of a contract whose vehicle was swapped.

The delivery data of the return (fuel, kilometres) is that of the vehicle the
customer has now, handed over in the substitution. The return report said
"No registrado" for the fuel and wrote "18,000 km" in English format.
"""
from odoo.tests.common import tagged

from .common import FUEL_FULL, VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_return')
class TestReturnAfterSubstitution(VehicleRentalCase):

    def _substitute(self, fuel):
        self.spare_vehicle.odometer = 18000
        wizard = self.env['vehicle.substitution.wizard'].create({
            'contract_id': self.contract.id,
            'new_vehicle_id': self.spare_vehicle.id,
            'old_vehicle_odometer': 10500,
            'old_vehicle_fuel_level': '2',
            'new_vehicle_fuel_level': fuel,
            'step': '4_confirm',
        })
        wizard.action_confirm_substitution()

    def test_return_starts_from_the_fuel_of_the_substitute(self):
        self.contract.initial_fuel_level = '1'
        self._substitute(FUEL_FULL)
        self.assertEqual(self.contract.initial_fuel_level, FUEL_FULL)
        wizard = self._open_return_wizard()
        self.assertEqual(wizard.fuel_level_start, FUEL_FULL)

    def test_return_report_shows_fuel_and_spanish_thousands(self):
        self._substitute(FUEL_FULL)
        wizard = self._fill_valid_return(self._open_return_wizard(), odometer=19200)
        wizard.action_confirm_return()
        record = self.env['vehicle.contract.return'].search([('contract_id', '=', self.contract.id)])
        html, _type = self.env['ir.actions.report']._render_qweb_html(
            'vehicle_rental.vehicle_contract_return_report_template', record.ids)
        html = html.decode()
        self.assertNotIn('No registrado', html)
        self.assertIn('18.000', html)
        self.assertIn('19.200', html)
        self.assertIn('1.200', html)
        self.assertNotIn('18,000', html)


@tagged('post_install', '-at_install', 'vehicle_substitution')
class TestSubstitutionAddendum(VehicleRentalCase):
    """The addendum box produces the document and dates are only those that happened."""

    def _substitute(self, **values):
        wizard = self.env['vehicle.substitution.wizard'].create(dict({
            'contract_id': self.contract.id,
            'new_vehicle_id': self.spare_vehicle.id,
            'old_vehicle_odometer': 10500,
            'old_vehicle_fuel_level': '2',
            'new_vehicle_fuel_level': FUEL_FULL,
            'step': '4_confirm',
        }, **values))
        wizard.action_confirm_substitution()
        return self.env['vehicle.contract.substitution'].search([('contract_id', '=', self.contract.id)])

    def test_generate_addendum_stores_the_document(self):
        substitution = self._substitute(generate_addendum=True)
        self.assertTrue(substitution.addendum_pdf)
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'vehicle.contract'), ('res_id', '=', self.contract.id),
            ('name', 'ilike', 'Addendum')])
        self.assertTrue(attachments, 'the addendum is attached to the contract')

    def test_no_signature_date_without_signatures(self):
        self.assertFalse(self._substitute().signature_date)

    def test_addendum_shows_the_contract_date(self):
        substitution = self._substitute()
        html, _type = self.env['ir.actions.report']._render_qweb_html(
            'vehicle_rental.vehicle_substitution_addendum_report_template', substitution.ids)
        html = html.decode()
        row = html[html.index('Fecha del Contrato'):][:300]
        self.assertIn(self.contract.create_date.strftime('%d/%m/%Y'), row)

    def test_vehicle_without_category_is_not_offered(self):
        uncategorised = self._create_vehicle('SIN-0001')
        uncategorised.category_id = False
        wizard = self.env['vehicle.substitution.wizard'].create({'contract_id': self.contract.id})
        self.assertIn(self.spare_vehicle, wizard.available_vehicle_ids)
        self.assertNotIn(uncategorised, wizard.available_vehicle_ids,
                         'a contract cannot hold a vehicle without category')
