# -*- coding: utf-8 -*-
"""Contracts can start in the past; the form only warns.

Juan, 2026-10-23, on prod: "Asegúrese de que la fecha de inicio sea mayor o
igual a la fecha de hoy" blocked recording a contract already running or
finished. It has to be a warning, not an error.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import Form, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_past_contracts')
class TestPastContracts(VehicleRentalCase):

    def test_contract_can_start_in_the_past(self):
        start = fields.Datetime.now() - timedelta(days=40)
        contract = self.env['vehicle.contract'].create({
            'customer_id': self.customer.id, 'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days', 'rent': 50.0, 'start_date': start,
            'end_date': start + timedelta(days=5), 'date': start.date()})
        self.assertEqual(contract.start_date, start.replace(microsecond=0))
        self.assertEqual(contract.date, start.date())

    def test_past_start_shows_a_warning(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.start_date = fields.Datetime.now() - timedelta(days=3)
        result = contract._onchange_past_start_date()
        self.assertIn('pasado', result['warning']['message'])

    def test_future_start_has_no_warning(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.start_date = fields.Datetime.now() + timedelta(days=3)
        self.assertFalse(contract._onchange_past_start_date())

    def test_past_contract_is_handed_over_and_returned(self):
        start = fields.Datetime.now() - timedelta(days=40)
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'start_date': start, 'end_date': start + timedelta(days=5)})
        contract.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
        self.assertEqual(contract.status, 'b_in_progress')
        self._fill_valid_return(self._open_return_wizard(contract)).action_confirm_return()
        self.assertEqual(contract.status, 'c_return')

    def test_changing_the_vehicle_keeps_the_chosen_driver(self):
        """The driver was replaced by the fleet driver of the vehicle, usually empty."""
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'is_driver_required': True, 'driver_id': self.customer.id})
        contract.vehicle_id = self.vehicle
        contract.onchange_vehicle_details()
        self.assertEqual(contract.driver_id, self.customer)
