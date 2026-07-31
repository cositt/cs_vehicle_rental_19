# -*- coding: utf-8 -*-
"""Shared fixtures for the contract traceability test suite.

Every test builds its own customer, vehicle and contract so the suite can run
against any database without depending on pre-existing business records.
"""
import base64
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase

# 1x1 transparent PNG, used wherever a Binary field needs a valid image.
PNG_1PX = base64.b64encode(base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
))

FUEL_FULL = '4'
FUEL_THREE_QUARTERS = '3'


class VehicleRentalCase(TransactionCase):
    """Base case with a contract already in progress, ready to be returned."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.now = fields.Datetime.now()
        cls.start_date = cls.now + timedelta(hours=1)
        cls.end_date = cls.now + timedelta(days=5)

        cls.customer = cls.env['res.partner'].create({
            'name': 'Cliente de Pruebas Devolución',
            'email': 'cliente.devolucion@example.com',
        })
        cls.customer_no_email = cls.env['res.partner'].create({
            'name': 'Cliente sin Correo',
        })

        cls.brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'TestBrand'})
        cls.category = cls.env['fleet.vehicle.model.category'].create({
            'name': 'TestCategory',
        })
        cls.model = cls.env['fleet.vehicle.model'].create({
            'name': 'TestModel',
            'brand_id': cls.brand.id,
            'category_id': cls.category.id,
        })

        cls.vehicle = cls._create_vehicle('TEST-0001', odometer=10000)
        cls.spare_vehicle = cls._create_vehicle('TEST-0002', odometer=500)

        cls.contract = cls._create_contract(cls.vehicle, cls.customer)

    @classmethod
    def _create_vehicle(cls, plate, odometer=0.0):
        return cls.env['fleet.vehicle'].create({
            'model_id': cls.model.id,
            'category_id': cls.category.id,
            'license_plate': plate,
            'odometer': odometer,
            'status': 'available',
        })

    @classmethod
    def _create_contract(cls, vehicle, customer, status='b_in_progress'):
        """Create a contract and move it to the requested status.

        The status is written after creation on purpose: going through
        ``a_draft_to_b_in_progress`` opens a mail composer wizard, which is not
        what these tests are exercising.
        """
        contract = cls.env['vehicle.contract'].create({
            'customer_id': customer.id,
            'vehicle_id': vehicle.id,
            'license_plate': vehicle.license_plate,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': cls.start_date,
            'end_date': cls.end_date,
            'last_odometer': vehicle.odometer,
            'odometer_unit': 'kilometers',
            'initial_fuel_level': FUEL_FULL,
        })
        contract.write({'status': status})
        return contract

    def _open_return_wizard(self, contract=None):
        """Open the return wizard exactly like the contract button does."""
        contract = contract or self.contract
        action = contract.b_in_progress_to_c_return()
        self.assertEqual(action['res_model'], 'vehicle.contract.return.wizard')
        self.assertEqual(action['target'], 'new')
        return self.env['vehicle.contract.return.wizard'].browse(action['res_id'])

    def _fill_valid_return(self, wizard, **overrides):
        """Minimum set of values that passes ``_validate_return``."""
        values = {
            'odometer': wizard.odometer_start + 1200,
            'fuel_level': FUEL_THREE_QUARTERS,
            'inspection_done': True,
            'send_closing_email': False,
        }
        values.update(overrides)
        wizard.write(values)
        return wizard
