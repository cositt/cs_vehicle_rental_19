# -*- coding: utf-8 -*-
"""Damage painter: regression tests for the bugs fixed on 2026-07-30.

Covers the return painter and, where the same bug existed, the substitution
painter too.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase, PNG_1PX


@tagged('post_install', '-at_install', 'vehicle_return', 'damage_painter')
class TestReturnDamagePainter(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        self.wizard = self._fill_valid_return(self._open_return_wizard())

    def _open_painter(self):
        action = self.wizard.action_open_damage_painter()
        self.assertEqual(
            action['res_model'], 'vehicle.contract.return.damage.painter')
        return self.env['vehicle.contract.return.damage.painter'].browse(
            action['res_id'])

    def test_painter_is_created_linked_to_the_wizard(self):
        painter = self._open_painter()

        self.assertEqual(painter.return_wizard_id, self.wizard)
        self.assertEqual(painter.vehicle_id, self.wizard.vehicle_id)

    def test_painter_ref_carries_model_and_id(self):
        """The JS reads this from the DOM: a dialog does not change the URL."""
        painter = self._open_painter()

        self.assertEqual(
            painter.painter_ref,
            'vehicle.contract.return.damage.painter,%s' % painter.id,
        )

    def test_saving_writes_the_image_and_flags_damage(self):
        painter = self._open_painter()

        result = painter.save_image_to_wizard(PNG_1PX.decode())

        self.assertTrue(result['success'])
        self.assertTrue(self.wizard.painted_damage_image)
        self.assertTrue(self.wizard.has_damage)

    def test_saving_an_empty_image_is_rejected(self):
        painter = self._open_painter()

        result = painter.save_image_to_wizard(False)

        self.assertFalse(result['success'])
        self.assertFalse(self.wizard.painted_damage_image)

    def test_base_image_is_empty_before_any_drawing(self):
        """With no marks the JS falls back to the default diagram."""
        painter = self._open_painter()

        self.assertFalse(painter.get_base_image())

    def test_reopening_returns_the_existing_marks(self):
        painter = self._open_painter()
        painter.save_image_to_wizard(PNG_1PX.decode())

        reopened = self._open_painter()

        self.assertEqual(reopened.get_base_image(), PNG_1PX.decode())

    def test_clearing_removes_the_marks_and_reopens_the_wizard(self):
        painter = self._open_painter()
        painter.save_image_to_wizard(PNG_1PX.decode())

        action = self.wizard.action_clear_damage_image()

        self.assertFalse(self.wizard.painted_damage_image)
        self.assertEqual(action['res_model'], 'vehicle.contract.return.wizard')
        self.assertEqual(action['res_id'], self.wizard.id)

    def test_closing_the_painter_returns_to_the_same_return_wizard(self):
        """Closing must not drop the return: the dialog replaces, not stacks."""
        painter = self._open_painter()

        action = painter.action_back_to_wizard()

        self.assertEqual(action['res_model'], 'vehicle.contract.return.wizard')
        self.assertEqual(action['res_id'], self.wizard.id)
        self.assertEqual(action['target'], 'new')

    def test_data_survives_the_round_trip_to_the_painter(self):
        self.wizard.write({'notes': 'Revisado en el mostrador'})
        painter = self._open_painter()
        painter.save_image_to_wizard(PNG_1PX.decode())
        painter.action_back_to_wizard()

        self.assertEqual(self.wizard.notes, 'Revisado en el mostrador')
        self.assertEqual(self.wizard.fuel_level, '3')
        self.assertTrue(self.wizard.inspection_done)
        self.assertTrue(self.wizard.painted_damage_image)

    def test_painted_image_reaches_the_return_record(self):
        painter = self._open_painter()
        painter.save_image_to_wizard(PNG_1PX.decode())
        self.wizard.write({'damage_description': '<p>Arañazo</p>'})

        self.wizard.action_confirm_return()

        self.assertTrue(self.contract.return_ids.painted_damage_image)


@tagged('post_install', '-at_install', 'damage_painter')
class TestSubstitutionDamagePainter(VehicleRentalCase):
    """The substitution painter got the same fixes; keep them from regressing."""

    def setUp(self):
        super().setUp()
        action = self.contract.action_open_substitution_wizard()
        self.substitution_wizard = self.env['vehicle.substitution.wizard'].browse(
            action['res_id'])
        self.substitution_wizard.write({'new_vehicle_id': self.spare_vehicle.id})

    def _open_painter(self, target='old'):
        opener = (self.substitution_wizard.action_open_old_damage_painter
                  if target == 'old'
                  else self.substitution_wizard.action_open_new_damage_painter)
        action = opener()
        return self.env['vehicle.substitution.damage.painter'].browse(
            action['res_id'])

    def test_painter_ref_carries_model_and_id(self):
        painter = self._open_painter()

        self.assertEqual(
            painter.painter_ref,
            'vehicle.substitution.damage.painter,%s' % painter.id,
        )

    def test_saving_writes_the_image_on_the_substitution_wizard(self):
        painter = self._open_painter()

        result = painter.save_image_to_wizard(PNG_1PX.decode())

        self.assertTrue(result['success'])
        self.assertTrue(self.substitution_wizard.old_vehicle_painted_damage_image)
        self.assertTrue(self.substitution_wizard.old_vehicle_has_damage)

    def test_old_and_new_vehicle_marks_are_kept_apart(self):
        self._open_painter('old').save_image_to_wizard(PNG_1PX.decode())

        self.assertTrue(self.substitution_wizard.old_vehicle_painted_damage_image)
        self.assertFalse(self.substitution_wizard.new_vehicle_painted_damage_image)

    def test_reopening_returns_the_existing_marks(self):
        painter = self._open_painter()
        painter.save_image_to_wizard(PNG_1PX.decode())

        reopened = self._open_painter()

        self.assertEqual(reopened.get_base_image(), PNG_1PX.decode())

    def test_closing_returns_to_the_substitution_wizard(self):
        painter = self._open_painter()

        action = painter.action_back_to_wizard()

        self.assertEqual(action['res_model'], 'vehicle.substitution.wizard')
        self.assertEqual(action['res_id'], self.substitution_wizard.id)
