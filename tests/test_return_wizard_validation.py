# -*- coding: utf-8 -*-
"""Hybrid validation policy of the vehicle return wizard."""
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import VehicleRentalCase, FUEL_FULL, FUEL_THREE_QUARTERS


@tagged('post_install', '-at_install', 'vehicle_return')
class TestReturnWizardValidation(VehicleRentalCase):

    def test_button_opens_wizard_without_changing_status(self):
        """The Return button opens a modal; it must not close the contract."""
        wizard = self._open_return_wizard()

        self.assertTrue(wizard.exists())
        self.assertEqual(wizard.contract_id, self.contract)
        self.assertEqual(self.contract.status, 'b_in_progress')

    def test_wizard_defaults_come_from_the_contract(self):
        wizard = self._open_return_wizard()

        self.assertEqual(wizard.vehicle_id, self.vehicle)
        self.assertEqual(wizard.odometer_start, self.contract.last_odometer)
        self.assertEqual(wizard.fuel_level_start, FUEL_FULL)
        self.assertEqual(wizard.customer_id, self.customer)

    def test_wizard_uses_current_vehicle_after_substitution(self):
        """A substituted contract must be returned with the substitute vehicle."""
        self.env['vehicle.contract.substitution'].create({
            'contract_id': self.contract.id,
            'reason': 'breakdown',
            'old_vehicle_id': self.vehicle.id,
            'new_vehicle_id': self.spare_vehicle.id,
        })

        wizard = self._open_return_wizard()

        self.assertEqual(wizard.vehicle_id, self.contract.current_vehicle_id)
        self.assertEqual(wizard.vehicle_id, self.spare_vehicle)

    def test_km_driven_is_the_difference(self):
        wizard = self._open_return_wizard()
        wizard.odometer = wizard.odometer_start + 1234

        self.assertEqual(wizard.km_driven, 1234)

    def test_km_driven_never_negative(self):
        wizard = self._open_return_wizard()
        wizard.invalidate_recordset()
        # Bypass the constraint to prove the compute itself clamps at zero.
        self.env.cr.execute(
            'UPDATE vehicle_contract_return_wizard SET odometer = %s WHERE id = %s',
            (wizard.odometer_start - 500, wizard.id),
        )
        wizard.invalidate_recordset()

        self.assertEqual(wizard.km_driven, 0.0)

    def test_odometer_lower_than_delivery_is_rejected_on_write(self):
        wizard = self._open_return_wizard()

        with self.assertRaises(ValidationError):
            wizard.odometer = wizard.odometer_start - 1

    def test_odometer_is_required_to_confirm(self):
        wizard = self._open_return_wizard()
        wizard.write({'fuel_level': FUEL_THREE_QUARTERS, 'inspection_done': True})

        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_fuel_level_is_required_to_confirm(self):
        wizard = self._open_return_wizard()
        wizard.write({
            'odometer': wizard.odometer_start + 100,
            'inspection_done': True,
        })

        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_inspection_checkbox_is_required_to_confirm(self):
        wizard = self._open_return_wizard()
        wizard.write({
            'odometer': wizard.odometer_start + 100,
            'fuel_level': FUEL_THREE_QUARTERS,
        })

        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_damage_requires_a_description(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({'has_damage': True, 'damage_amount': 250.0})

        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_damage_amount_is_optional(self):
        """Appraisal can happen later: zero must not block the return."""
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({
            'has_damage': True,
            'damage_description': '<p>Rayón en el paragolpes</p>',
            'damage_amount': 0.0,
        })

        wizard.action_confirm_return()

        self.assertEqual(self.contract.status, 'c_return')
        self.assertEqual(self.contract.return_ids.damage_amount, 0.0)

    def test_requested_signature_must_be_collected(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({'request_signature': True})

        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_signature_not_requested_confirms_without_it(self):
        wizard = self._fill_valid_return(self._open_return_wizard())

        wizard.action_confirm_return()

        self.assertEqual(self.contract.status, 'c_return')
        self.assertFalse(self.contract.return_ids.customer_signature)

    def test_only_contracts_in_progress_can_be_returned(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        self.contract.write({'status': 'a_draft'})

        with self.assertRaises(UserError):
            wizard.action_confirm_return()

    def test_unchecking_damage_clears_its_data(self):
        wizard = self._open_return_wizard()
        wizard.write({
            'has_damage': True,
            'damage_description': '<p>Golpe</p>',
            'damage_amount': 300.0,
            'invoice_damage_now': True,
        })

        wizard.has_damage = False
        wizard._onchange_has_damage()

        self.assertFalse(wizard.damage_description)
        self.assertEqual(wizard.damage_amount, 0.0)
        self.assertFalse(wizard.invoice_damage_now)
