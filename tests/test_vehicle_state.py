# -*- coding: utf-8 -*-
"""Rental vehicles are registered vehicles.

Fleet puts every new vehicle in "Nueva solicitud" (a car still to be ordered),
so the whole imported fleet showed as requested although it is registered and
on the road (Juan, 2026-10-23: "todos los carros están matriculados").
"""
import importlib.util

from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_state')
class TestVehicleState(VehicleRentalCase):

    def test_new_vehicle_is_registered(self):
        vehicle = self._create_vehicle('TEST-STATE-1', odometer=10)
        self.assertEqual(vehicle.state_id, self.env.ref('fleet.fleet_vehicle_state_registered'))

    def test_migration_registers_the_requested_vehicles(self):
        requested = self.env.ref('fleet.fleet_vehicle_state_new_request')
        downgraded = self.env.ref('fleet.fleet_vehicle_state_downgraded')
        vehicle = self._create_vehicle('TEST-STATE-2', odometer=10)
        other = self._create_vehicle('TEST-STATE-3', odometer=10)
        vehicle.state_id = requested
        other.state_id = downgraded
        self.env.flush_all()

        path = file_path('vehicle_rental/migrations/19.0.6.26/post-migrate.py')
        spec = importlib.util.spec_from_file_location('vehicle_state_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, '19.0.6.25')
        self.env.invalidate_all()

        self.assertEqual(vehicle.state_id, self.env.ref('fleet.fleet_vehicle_state_registered'))
        self.assertEqual(other.state_id, downgraded, 'other stages are left alone')
