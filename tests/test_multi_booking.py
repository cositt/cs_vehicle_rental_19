# -*- coding: utf-8 -*-
"""Booking several vehicles for one customer and handing them over together.

Found in the Phase 7 regression:
- handing over several contracts at once only handed over the first one;
- each "Añadir vehículo" started empty instead of with the previous dates,
  category and km;
- a vehicle already added was still offered, so it could be booked twice;
- activating a group skipped the hand-over checks and did not see contracts
  of the other company.
"""
from datetime import timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import new_test_user, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_multi_booking')
class TestMultiBooking(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.start = cls.now + timedelta(days=60)
        cls.end = cls.start + timedelta(days=3)
        cls.booking = cls.env['rental.multi.booking'].create({'customer_id': cls.customer.id})

    def _wizard(self):
        action = self.booking.action_add_vehicle()
        return self.env['rental.contract.booking'].with_context(action['context']).new({})

    def _add(self, vehicle):
        wizard = self._wizard()
        wizard.update({'start_date': self.start, 'end_date': self.end,
                       'selected_category_id': self.category.id, 'km_range': '350'})
        wizard._onchange_available_vehicle()
        self.assertIn(vehicle, wizard.fleet_vehicle_ids._origin)
        wizard._add_to_multi_booking(vehicle)

    def test_next_vehicle_starts_from_the_previous_line(self):
        self._add(self.spare_vehicle)
        wizard = self._wizard()
        self.assertEqual(wizard.start_date, self.start)
        self.assertEqual(wizard.end_date, self.end)
        self.assertEqual(wizard.selected_category_id, self.category)
        self.assertEqual(wizard.km_range, '350')

    def test_adding_a_vehicle_closes_the_dialog(self):
        """Reopening the booking form stacked one breadcrumb per vehicle."""
        wizard = self._wizard()
        wizard.update({'start_date': self.start, 'end_date': self.end,
                       'selected_category_id': self.category.id, 'km_range': '350'})
        action = wizard._add_to_multi_booking(self.spare_vehicle)
        self.assertEqual(action['type'], 'ir.actions.act_window_close')

    def test_vehicle_already_added_is_not_offered_again(self):
        self._add(self.spare_vehicle)
        wizard = self._wizard()
        wizard._onchange_available_vehicle()
        self.assertNotIn(self.spare_vehicle, wizard.fleet_vehicle_ids._origin)
        with self.assertRaises(UserError):
            wizard._add_to_multi_booking(self.spare_vehicle)


@tagged('post_install', '-at_install', 'vehicle_multi_booking')
class TestHandOverSeveral(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.third_vehicle = cls._create_vehicle('TEST-0003', odometer=100)
        cls.first = cls._create_contract(cls.spare_vehicle, cls.customer, status='a_draft')
        cls.second = cls._create_contract(cls.third_vehicle, cls.customer, status='a_draft')
        cls.both = cls.first | cls.second

    def test_handing_over_several_hands_over_all(self):
        action = self.both.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
        self.assertEqual(set(self.both.mapped('status')), {'b_in_progress'})
        self.assertEqual(action['res_model'], 'mail.compose.message')
        self.assertEqual(action['context']['default_composition_mode'], 'mass_mail')
        self.assertEqual(action['context']['default_res_ids'], self.both.ids)

    def test_mail_comes_from_the_owner_of_the_vehicle(self):
        owner = self.env['res.company'].create({'name': 'Dueña Correo Test', 'email': 'flota@duena.example.com'})
        self.spare_vehicle.company_id = owner
        action = self.first.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
        self.assertEqual(action['context']['default_email_from'], 'flota@duena.example.com')

    def test_overlap_of_the_other_company_blocks_the_hand_over(self):
        other = self.env['res.company'].create({'name': 'Otra Compañía Solape'})
        clerk = new_test_user(
            self.env, login='entrega_multi', groups='base.group_user,fleet.fleet_group_manager',
            company_id=self.company.id, company_ids=[self.company.id, other.id])
        busy = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        busy.write({'company_id': other.id, 'start_date': self.first.start_date, 'end_date': self.first.end_date})
        busy.status = 'b_in_progress'
        contract = self.first.with_user(clerk).with_context(allowed_company_ids=[self.company.id])
        with self.assertRaisesRegex(UserError, 'solapan'):
            contract.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()

    def test_group_activation_applies_the_hand_over_checks(self):
        group = self.env['vehicle.contract.group'].create({
            'customer_id': self.customer.id, 'start_date': self.first.start_date,
            'end_date': self.first.end_date})
        self.both.group_id = group
        self.first.write({'deposit_card_type': 'cash', 'insurance_type': 'basic'})
        with self.assertRaises(UserError):
            group.action_activate_all()
        self.assertEqual(self.second.status, 'a_draft', 'nothing is handed over when one fails')

    def test_group_hands_over_all_from_its_form(self):
        group = self.env['vehicle.contract.group'].create({
            'customer_id': self.customer.id, 'start_date': self.first.start_date,
            'end_date': self.first.end_date})
        self.both.group_id = group
        arch = self.env['vehicle.contract.group'].get_view(view_type='form')['arch']
        self.assertIn('name="action_activate_all"', arch)
        action = group.action_activate_all()
        self.assertEqual(set(self.both.mapped('status')), {'b_in_progress'})
        self.assertEqual(action['context']['default_res_ids'], self.both.ids)
        self.assertEqual(group.contract_tax_ids, self.both.tax_ids)

    def test_hand_over_leaves_a_trace_in_the_chatter(self):
        self.env.cr.precommit.run()  # end the creation of the fixtures: no tracking while creating
        self.first.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
        self.env.cr.precommit.run()  # tracking is written on commit
        self.first.invalidate_recordset(['message_ids'])
        tracked = self.first.message_ids.tracking_value_ids.filtered(
            lambda t: t.field_id.name == 'status')
        self.assertEqual(tracked.new_value_char, 'In Progress')


@tagged('post_install', '-at_install', 'vehicle_multi_booking')
class TestContractDetails(VehicleRentalCase):

    def test_contract_takes_the_odometer_of_its_vehicle(self):
        """Contracts made from a web lead or a sale order came with "Último odómetro" 0."""
        contract = self.env['vehicle.contract'].create({
            'customer_id': self.customer.id, 'vehicle_id': self.vehicle.id, 'rent_type': 'days',
            'rent': 50.0, 'start_date': self.start_date, 'end_date': self.end_date})
        self.assertEqual(contract.last_odometer, self.vehicle.odometer)

    def test_rent_without_price_is_explained_in_spanish(self):
        with self.assertRaisesRegex(ValidationError, 'El precio por día debe ser mayor que cero'):
            self.env['vehicle.contract'].create({
                'customer_id': self.customer.id, 'vehicle_id': self.vehicle.id, 'rent_type': 'days',
                'rent': 0.0, 'start_date': self.start_date, 'end_date': self.end_date})

    def test_extension_has_a_readable_name(self):
        extension = self.env['vehicle.contract.extension'].create({
            'contract_id': self.contract.id,
            'new_end_date': self.contract.end_date + timedelta(days=2),
            'daily_rate': 50.0,
        })
        self.assertIn(self.contract.reference_no, extension.display_name)
        self.assertNotIn('vehicle.contract.extension', extension.display_name)
