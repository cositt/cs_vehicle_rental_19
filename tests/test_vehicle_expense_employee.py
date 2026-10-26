# -*- coding: utf-8 -*-
"""A vehicle expense does not need an hr.employee.

Prod, 2026-10-26: the companies have no employees, so a vehicle expense could
not be saved ("Empleado" required). Juan: the employee can be typed by hand
and is only recorded.
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_expense_employee')
class TestVehicleExpenseEmployee(VehicleRentalCase):

    def _expense(self, **vals):
        values = {'name': 'Lavado', 'fleet_vehicle_id': self.spare_vehicle.id,
                  'total_amount_currency': 50.0, 'employee_id': False}
        values.update(vals)
        return self.env['hr.expense'].create(values)

    def test_vehicle_expense_with_typed_employee(self):
        expense = self._expense(employee_name='Pepe del taller')
        self.assertFalse(expense.employee_id)
        self.assertEqual(expense.employee_name, 'Pepe del taller')
        self.assertEqual(expense.total_amount_currency, 50.0)

    def test_vehicle_expense_without_any_employee(self):
        self.assertTrue(self._expense())

    def test_other_expenses_still_need_an_employee(self):
        with self.assertRaises(ValidationError):
            self.env['hr.expense'].create({'name': 'Comida', 'total_amount_currency': 10.0,
                                           'employee_id': False})
