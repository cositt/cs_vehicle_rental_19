# -*- coding: utf-8 -*-
"""Maintenance buttons on the vehicle form must state why they refuse.

Both used to return a self-dismissing toast, which reads as "the button does
nothing": the precondition was never seen by the user.
"""
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_maintenance')
class TestVehicleMaintenanceButtons(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        self.schedule = self.env['maintenance.schedule'].create({
            'name': 'Revisión de prueba',
            'maintenance_days': 30,
        })

    # --- Crear Solicitud de Mantenimiento -------------------------------

    def test_creating_without_a_schedule_explains_what_is_missing(self):
        self.spare_vehicle.maintenance_schedule_id = False

        with self.assertRaises(UserError) as caught:
            self.spare_vehicle.action_create_maintenance_request()

        message = str(caught.exception)
        self.assertIn('Horario de Mantenimiento', message)
        self.assertIn(self.spare_vehicle.license_plate, message)

    def test_creating_with_a_schedule_opens_the_new_request(self):
        self.spare_vehicle.maintenance_schedule_id = self.schedule

        action = self.spare_vehicle.action_create_maintenance_request()

        self.assertEqual(action['res_model'], 'maintenance.request')
        request = self.env['maintenance.request'].browse(action['res_id'])
        self.assertEqual(request.fleet_vehicle_id, self.spare_vehicle)
        self.assertEqual(request.maintenance_schedule_id, self.schedule)

    def test_the_new_request_inherits_the_vehicle_odometer(self):
        self.spare_vehicle.maintenance_schedule_id = self.schedule

        action = self.spare_vehicle.action_create_maintenance_request()

        request = self.env['maintenance.request'].browse(action['res_id'])
        self.assertEqual(request.vehicle_odometer, self.spare_vehicle.odometer)

    # --- En mantenimiento -----------------------------------------------

    def test_a_rented_vehicle_cannot_go_into_maintenance(self):
        """The contract fixture leaves this vehicle in progress."""
        with self.assertRaises(UserError) as caught:
            self.vehicle.available_to_in_maintenance()

        message = str(caught.exception)
        self.assertIn(self.contract.reference_no, message)
        self.assertEqual(self.vehicle.status, 'available',
                         'the status must not change when it is refused')

    def test_a_free_vehicle_goes_into_maintenance(self):
        self.spare_vehicle.available_to_in_maintenance()

        self.assertEqual(self.spare_vehicle.status, 'in_maintenance')

    def test_a_returned_contract_no_longer_blocks_maintenance(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.action_confirm_return()

        self.vehicle.available_to_in_maintenance()

        self.assertEqual(self.vehicle.status, 'in_maintenance')

    def test_coming_back_from_maintenance(self):
        self.spare_vehicle.available_to_in_maintenance()

        self.spare_vehicle.in_maintenance_to_available()

        self.assertEqual(self.spare_vehicle.status, 'available')
