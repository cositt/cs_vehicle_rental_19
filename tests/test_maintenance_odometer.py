# -*- coding: utf-8 -*-
"""Odometer reading recorded on each maintenance intervention."""
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_maintenance')
class TestMaintenanceOdometer(VehicleRentalCase):

    def _new_request(self, **values):
        vals = {
            'name': 'Revisión de prueba',
            'fleet_vehicle_id': self.vehicle.id,
        }
        vals.update(values)
        return self.env['maintenance.request'].create(vals)

    def test_request_starts_with_the_current_vehicle_odometer(self):
        """The counter reading is prefilled so the mechanic only corrects it."""
        request = self._new_request()

        self.assertEqual(request.vehicle_odometer, self.vehicle.odometer)

    def test_reading_can_be_overridden(self):
        request = self._new_request(vehicle_odometer=15250)

        self.assertEqual(request.vehicle_odometer, 15250)

    def test_unit_comes_from_the_vehicle(self):
        request = self._new_request()

        self.assertEqual(request.odometer_unit, self.vehicle.odometer_unit)

    def test_reading_is_optional(self):
        """Appraisal of km may be unknown when the request is opened."""
        request = self._new_request(vehicle_odometer=0.0)

        self.assertEqual(request.vehicle_odometer, 0.0)

    def test_negative_reading_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._new_request(vehicle_odometer=-5)

    def test_reading_without_vehicle_stays_empty(self):
        """Maintenance also covers non-fleet equipment."""
        request = self.env['maintenance.request'].create({'name': 'Equipo de taller'})

        self.assertEqual(request.vehicle_odometer, 0.0)
        self.assertFalse(request.odometer_unit)

    def test_changing_the_vehicle_refreshes_the_reading(self):
        request = self._new_request()
        request.fleet_vehicle_id = self.spare_vehicle

        request._onchange_fleet_vehicle_odometer()

        self.assertEqual(request.vehicle_odometer, self.spare_vehicle.odometer)

    def test_reading_does_not_alter_the_vehicle_odometer(self):
        """Recording km on a request must not rewrite the vehicle's own counter."""
        original = self.vehicle.odometer

        self._new_request(vehicle_odometer=original + 4000)

        self.assertEqual(self.vehicle.odometer, original)
