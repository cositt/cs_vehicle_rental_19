# -*- coding: utf-8 -*-
"""Screens, messages and placeholders are in Spanish.

Juan, 2026-10-23: labels such as "Is Any Trip Expense", "Start Date" or
"Extra Charge per Day" showed in English in prod.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase

ENGLISH = {
    'Start Date', 'End Date', 'Return Date', 'Category', 'Contract', 'Reference',
    'Extra Charge per Day', 'Extra Charge per KM', 'Total Deposit', 'Return Deposit',
    'Vehicle Category', 'Booking', 'Expenses', 'Employees', 'Is Any Trip Expense',
    'Payment Transaction', 'Pricing Type', 'Seats Number', 'Extension Count', 'Line Count',
    'Rental Agreement Terms', 'Amount to Return', 'Any Damage', 'Is Grouped', 'Driver',
}


@tagged('post_install', '-at_install', 'vehicle_spanish_labels')
class TestSpanishLabels(VehicleRentalCase):

    def test_no_english_field_labels(self):
        data = self.env['ir.model.data'].search([
            ('module', '=', 'vehicle_rental'), ('model', '=', 'ir.model.fields')])
        fields = self.env['ir.model.fields'].with_context(lang='es_ES').browse(data.mapped('res_id'))
        english = sorted({f'{f.model}.{f.name}: {f.field_description}'
                          for f in fields if f.field_description in ENGLISH})
        self.assertFalse(english, '\n'.join(english))

    def test_flexirent_note_explains_the_debit_rule(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'pricing_type': 'flexirent', 'deposit_card_type': 'credit'})
        self.assertIn('la misma con débito, crédito o efectivo', contract.deposit_rule_note)
