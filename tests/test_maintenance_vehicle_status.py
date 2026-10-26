# -*- coding: utf-8 -*-
"""The maintenance stage drives the vehicle status.

Prod, 2026-10-26: a request moved to "En proceso" left the vehicle
"Operacional", bookable while in the workshop.
"""
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_maintenance_status')
class TestMaintenanceVehicleStatus(VehicleRentalCase):

    def _request(self, vehicle):
        return self.env['maintenance.request'].create({
            'name': 'Revisión', 'fleet_vehicle_id': vehicle.id})

    def test_in_progress_puts_the_vehicle_in_maintenance(self):
        request = self._request(self.spare_vehicle)
        request.stage_id = self.env.ref('maintenance.stage_1')
        self.assertEqual(self.spare_vehicle.status, 'in_maintenance')

    def test_repaired_makes_it_available_again(self):
        request = self._request(self.spare_vehicle)
        request.stage_id = self.env.ref('maintenance.stage_1')
        request.stage_id = self.env.ref('maintenance.stage_3')
        self.assertEqual(self.spare_vehicle.status, 'available')

    def test_scrapped_request_also_frees_the_vehicle(self):
        request = self._request(self.spare_vehicle)
        request.stage_id = self.env.ref('maintenance.stage_1')
        request.stage_id = self.env.ref('maintenance.stage_4')
        self.assertEqual(self.spare_vehicle.status, 'available')

    def test_vehicle_stays_in_maintenance_while_another_request_is_open(self):
        first, second = self._request(self.spare_vehicle), self._request(self.spare_vehicle)
        (first | second).stage_id = self.env.ref('maintenance.stage_1')
        first.stage_id = self.env.ref('maintenance.stage_3')
        self.assertEqual(self.spare_vehicle.status, 'in_maintenance')

    def test_rented_vehicle_cannot_go_to_the_workshop(self):
        request = self._request(self.vehicle)  # self.contract is in progress on it
        with self.assertRaises(UserError):
            request.stage_id = self.env.ref('maintenance.stage_1')
