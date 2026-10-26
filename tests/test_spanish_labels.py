# -*- coding: utf-8 -*-
"""Screens, messages and placeholders are in Spanish.

Juan, 2026-10-23: labels such as "Is Any Trip Expense", "Start Date" or
"Extra Charge per Day" showed in English in prod.
"""
import importlib.util
from datetime import timedelta

from odoo.tests.common import tagged
from odoo.tools.misc import file_path

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

    def test_booking_wizard_km_options_show_the_tariff_labels(self):
        """Prod, 2026-10-26: the booking wizard offered «unlimited»."""
        self.env['vehicle.pricing.rule'].search([('km_range', '=', 'unlimited')], limit=1) or \
            self.env['vehicle.pricing.rule'].create({
                'name': 'Sin límite test', 'vehicle_category_id': self.contract.vehicle_category_id.id,
                'km_range': 'unlimited', 'duration_range': '1-2d', 'price': 100.0})
        labels = dict(self.env['rental.contract.booking'].with_context(lang='es_ES')._get_km_options())
        self.assertEqual(labels.get('unlimited'), 'Sin límite')

    def test_minimum_duration_message_is_in_spanish(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        with self.assertRaisesRegex(Exception, 'requiere una duración mínima de 7 días'):
            contract.write({'rent_type': 'week', 'end_date': contract.start_date + timedelta(days=2)})

    def test_damage_sketch_report_name_is_in_spanish(self):
        path = file_path('vehicle_rental/migrations/19.0.6.30/post-migrate.py')
        spec = importlib.util.spec_from_file_location('vehicle_report_names_fix', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.fix_damage_report_names(self.env)
        report = self.env.ref('vehicle_rental.action_scratch_report_template').with_context(lang='es_ES')
        self.assertEqual(report.name, 'Informe de daños')
        action = self.env.ref('vehicle_rental.action_vehicle_scratch_report').with_context(lang='es_ES')
        self.assertEqual(action.name, 'Informes de daños')
