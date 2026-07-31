# -*- coding: utf-8 -*-
"""Refused actions must raise, not flash a toast that dismisses itself.

Every case here aborts the operation and needs the user to fix something. A
`display_notification` made the buttons look broken: the reason vanished after
a few seconds and could not be re-read.
"""
from datetime import timedelta

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_errors')
class TestContractBlockingErrors(VehicleRentalCase):

    def _draft_contract(self, **overrides):
        values = {
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        values.update(overrides)
        return self.env['vehicle.contract'].create(values)

    def test_activating_without_rent_type_explains_it(self):
        contract = self._draft_contract()
        contract.rent_type = False

        with self.assertRaises(UserError) as caught:
            contract.a_draft_to_b_in_progress()

        self.assertIn('unidad de alquiler', str(caught.exception))
        self.assertEqual(contract.status, 'a_draft')

    def test_activating_without_dates_explains_it(self):
        contract = self._draft_contract()
        contract.write({'start_date': False, 'end_date': False})

        with self.assertRaises(UserError) as caught:
            contract.a_draft_to_b_in_progress()

        self.assertIn('fechas', str(caught.exception))
        self.assertEqual(contract.status, 'a_draft')

    def test_overlapping_contract_names_the_conflict(self):
        """The clash detail is the whole value of this message."""
        overlapping = self._draft_contract(vehicle_id=self.vehicle.id)

        with self.assertRaises(UserError) as caught:
            overlapping.a_draft_to_b_in_progress()

        message = str(caught.exception)
        self.assertIn(self.contract.reference_no, message)
        self.assertEqual(overlapping.status, 'a_draft')

    def test_deposit_without_amount_is_refused(self):
        self.contract.write({'if_any_deposit': True, 'deposit': 0.0})

        with self.assertRaises(UserError) as caught:
            self.contract.action_vehicle_rent_deposit()

        self.assertIn('depósito', str(caught.exception).lower())

    def test_odometer_must_move_forward(self):
        self.contract.last_odometer = self.vehicle.odometer

        with self.assertRaises(UserError) as caught:
            self.contract.vehicle_details_update()

        self.assertIn('kilometraje', str(caught.exception).lower())

    def test_installment_without_payment_type_is_refused(self):
        self.contract.write({'payment_type': False, 'total_vehicle_rent': 250.0})

        with self.assertRaises(UserError) as caught:
            self.contract.action_create_vehicle_payment()

        self.assertIn('forma de pago', str(caught.exception).lower())

    def test_installment_without_amount_is_refused(self):
        self.contract.write({'payment_type': 'full_payment',
                             'total_vehicle_rent': 0.0})

        with self.assertRaises(UserError) as caught:
            self.contract.action_create_vehicle_payment()

        self.assertIn('cargos', str(caught.exception).lower())

    def test_installment_is_created_when_everything_is_set(self):
        self.contract.write({'payment_type': 'full_payment',
                             'total_vehicle_rent': 250.0})

        self.contract.action_create_vehicle_payment()

        self.assertTrue(self.contract.vehicle_payment_option_ids)


@tagged('post_install', '-at_install', 'vehicle_errors')
class TestWizardBlockingErrors(VehicleRentalCase):

    def test_payment_option_without_amount_is_refused(self):
        option = self.env['vehicle.payment.option'].create({
            'vehicle_contract_id': self.contract.id,
            'name': 'Cuota de prueba',
            'payment_date': self.now.date(),
            'payment_amount': 0.0,
            'invoice_item_id': self.contract.invoice_item_id.id,
        })

        with self.assertRaises(UserError) as caught:
            option.action_create_payment_invoice()

        self.assertIn('importe', str(caught.exception).lower())

    def test_return_deposit_without_amount_is_refused(self):
        wizard = self.env['return.deposit'].create({
            'contract_id': self.contract.id,
            'return_deposit': 0.0,
        })

        with self.assertRaises(UserError) as caught:
            wizard.create_return_deposit_invoice()

        self.assertIn('fianza', str(caught.exception).lower())

    def test_damage_invoice_without_amount_is_refused(self):
        wizard = self.env['vehicle.damage'].with_context(
            active_id=self.contract.id).create({'damage_amount': 0.0})

        with self.assertRaises(UserError) as caught:
            wizard.vehicle_damage_amount()

        self.assertIn('importe', str(caught.exception).lower())


@tagged('post_install', '-at_install', 'vehicle_errors')
class TestInformativeNotifications(VehicleRentalCase):
    """These two are not refusals; they stay as toasts."""

    def test_nothing_to_submit_stays_a_notification(self):
        result = self.contract.create_contract_trip_expense_report()

        self.assertEqual(result.get('tag'), 'display_notification')
        self.assertEqual(result['params']['type'], 'info')

    def test_successful_submission_is_green(self):
        category = self.env['product.product'].create({
            'name': 'Peaje',
            'type': 'service',
            'can_be_expensed': True,
        })
        employee = self.env.user.employee_id or self.env['hr.employee'].create({
            'name': 'Empleado de prueba',
        })
        expense = self.env['hr.expense'].create({
            'name': 'Peaje de prueba',
            'product_id': category.id,
            'employee_id': employee.id,
            'total_amount': 12.0,
            'vehicle_contract_id': self.contract.id,
        })
        self.assertEqual(expense.state, 'draft')

        result = self.contract.create_contract_trip_expense_report()

        self.assertEqual(result['params']['type'], 'success')
