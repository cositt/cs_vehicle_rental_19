# -*- coding: utf-8 -*-
"""Booking sees every vehicle of the companies the user works with.

The company switcher only says which company the user is acting for: a user
of Sunset and Pinveco acting for Sunset still sees and rents the vehicles of
Pinveco, and a Pinveco contract still keeps its vehicle busy.
"""
from datetime import timedelta

from odoo.tests.common import new_test_user, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_cross_company')
class TestCrossCompanyBooking(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sunset = cls.env.company
        cls.sister = cls.env['res.company'].create({'name': 'Hermana Reservas Test'})
        cls.user = new_test_user(
            cls.env, login='reservas_multi', groups='base.group_user,fleet.fleet_group_manager',
            company_id=cls.sunset.id, company_ids=[cls.sunset.id, cls.sister.id])
        cls.sister_vehicle = cls._create_vehicle('HER-0001')
        cls.sister_vehicle.company_id = cls.sister
        cls.busy_sister_vehicle = cls._create_vehicle('HER-0002')
        cls.busy_sister_vehicle.company_id = cls.sister
        cls.start = cls.now + timedelta(days=60)
        contract = cls.env['vehicle.contract'].create({
            'customer_id': cls.customer.id, 'vehicle_id': cls.busy_sister_vehicle.id,
            'rent_type': 'days', 'rent': 50.0, 'company_id': cls.sister.id,
            'start_date': cls.start, 'end_date': cls.start + timedelta(days=3),
        })
        contract.write({'status': 'b_in_progress'})

    def _as_sunset_only(self, model):
        return self.env[model].with_user(self.user).with_context(allowed_company_ids=[self.sunset.id])

    def _wizard(self):
        wizard = self._as_sunset_only('rental.contract.booking').new({
            'selected_category_id': self.category.id,
            'start_date': self.start,
            'end_date': self.start + timedelta(days=3),
        })
        wizard._onchange_available_vehicle()
        return wizard

    def test_wizard_offers_vehicles_of_the_other_company(self):
        self.assertIn(self.sister_vehicle.id, self._wizard().fleet_vehicle_ids.ids)

    def test_contract_of_the_other_company_keeps_its_vehicle_busy(self):
        self.assertNotIn(self.busy_sister_vehicle.id, self._wizard().fleet_vehicle_ids.ids)

    def test_vehicles_of_the_other_company_are_readable(self):
        vehicle = self._as_sunset_only('fleet.vehicle').browse(self.sister_vehicle.id)
        self.assertEqual(vehicle.license_plate, 'HER-0001')
        self.assertIn(vehicle, self._as_sunset_only('fleet.vehicle').search([('license_plate', '=', 'HER-0001')]))

    def test_company_outside_the_user_stays_hidden(self):
        foreign = self.env['res.company'].create({'name': 'Ajena Test'})
        hidden = self._create_vehicle('AJE-0001')
        hidden.company_id = foreign
        found = self._as_sunset_only('fleet.vehicle').search([('license_plate', '=', 'AJE-0001')])
        self.assertFalse(found)


@tagged('post_install', '-at_install', 'vehicle_cross_company')
class TestBookingWizardCarriesChoices(VehicleRentalCase):
    """What is chosen in the booking assistant reaches the contract."""

    def test_contract_keeps_category_and_km_band(self):
        start = self.now + timedelta(days=70)
        self.env['vehicle.pricing.rule'].create({
            'vehicle_category_id': self.category.id, 'pricing_type': 'standard',
            'km_range': '350', 'duration_range': '3-5d', 'price_per_unit': 75.0,
            'valid_from': start.date() - timedelta(days=100),
        })
        wizard = self.env['rental.contract.booking'].create({
            'customer_id': self.customer.id, 'selected_category_id': self.category.id,
            'start_date': start, 'end_date': start + timedelta(days=3),
            'duration_range': '3-5d', 'km_range': '350', 'pricing_type': 'standard',
        })
        action = wizard.action_create_contract_for_vehicle(self.spare_vehicle.id)
        contract = self.env['vehicle.contract'].browse(action['res_id'])
        self.assertEqual(contract.vehicle_category_id, self.category)
        self.assertEqual(contract.km_range, '350')
        self.assertEqual(contract.rent, 75.0)
