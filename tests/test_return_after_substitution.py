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
