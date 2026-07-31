# -*- coding: utf-8 -*-
"""Browser-driven walkthrough of the whole return flow."""
from odoo.tests.common import HttpCase, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_return', 'vehicle_tour')
class TestReturnFlowTour(VehicleRentalCase, HttpCase):

    def test_return_flow_from_the_ui(self):
        """Drive the return exactly as the counter clerk does, in a browser."""
        self.contract.write({'last_odometer': 10000})
        action = self.env.ref('vehicle_rental.action_vehicle_contract')

        self.start_tour(
            '/odoo/action-%s/%s' % (action.id, self.contract.id),
            'vehicle_return_flow_tour',
            login='admin',
        )

        self.assertEqual(self.contract.status, 'c_return')
        self.assertEqual(self.contract.return_count, 1)

        record = self.contract.return_ids
        self.assertEqual(record.odometer, 23500)
        self.assertEqual(record.km_driven, 13500)
        self.assertEqual(record.fuel_level, '3')
        self.assertTrue(record.inspection_done)
        self.assertTrue(record.has_damage)
        self.assertIn('Rayón', record.damage_description)
        self.assertEqual(record.damage_amount, 0.0,
                         'the appraisal is allowed to come later')
        self.assertTrue(record.painted_damage_image,
                        'the drawing must reach the server')
        self.assertTrue(record.acta_generated)
        self.assertEqual(self.vehicle.status, 'available')
