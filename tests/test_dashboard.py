# -*- coding: utf-8 -*-
"""The figures of the rental dashboard.

Found in the Phase 7 regression:
- "Todos los Clientes" counted every contact of the database (34.733);
- "Facturas Pendientes" counted drafts and invoices already paid in the bank;
- "Ingresos mensuales" added deposits, drafts and VAT, and only for returned
  contracts.
"""
from odoo import fields
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_dashboard')
class TestDashboard(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env['vehicle.rental.dashboard']
        cls.deposit = cls.env.ref('vehicle_rental.vehicle_rent_deposit')

    def _invoice(self, rent, deposit=0.0, post=True, move_type='out_invoice'):
        lines = [(0, 0, {'name': 'Alquiler', 'price_unit': rent, 'tax_ids': False})]
        if deposit:
            lines.append((0, 0, {'product_id': self.deposit.id, 'price_unit': deposit, 'tax_ids': False}))
        invoice = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.customer.id,
            'vehicle_contract_id': self.contract.id, 'invoice_date': fields.Date.today(),
            'invoice_line_ids': lines})
        if post:
            invoice.action_post()
        return invoice

    def _month_income(self):
        months, values = self.dashboard.get_rent_invoice_month()
        return values[fields.Date.today().month - 1]

    def test_customers_are_those_who_rented(self):
        data = self.dashboard.get_vehicle_rental_dashboard()
        self.assertEqual(data['customers'], len(self.env['vehicle.contract'].search([]).customer_id))
        self.assertEqual(self.env['res.partner'].search_count(data['domains']['customers']), data['customers'])

    def test_pending_invoices_are_posted_and_unpaid(self):
        before = self.dashboard.get_vehicle_rental_dashboard()['pending_invoices']
        self._invoice(100.0)
        self._invoice(100.0, post=False)
        data = self.dashboard.get_vehicle_rental_dashboard()
        self.assertEqual(data['pending_invoices'], before + 1)
        self.assertEqual(self.env['account.move'].search_count(data['domains']['pending_invoices']),
                         data['pending_invoices'])

    def test_income_is_untaxed_rent_without_deposits_or_drafts(self):
        before = self._month_income()
        self._invoice(100.0, deposit=300.0)
        self._invoice(50.0, post=False)
        self.assertAlmostEqual(self._month_income() - before, 100.0)

    def test_income_counts_contracts_in_progress_and_refunds(self):
        self.assertEqual(self.contract.status, 'b_in_progress')
        before = self._month_income()
        self._invoice(100.0)
        self._invoice(30.0, move_type='out_refund')
        self.assertAlmostEqual(self._month_income() - before, 70.0)

    def test_labels_are_in_spanish(self):
        arch = open(__file__.replace('tests/test_dashboard.py', 'static/src/xml/template.xml')).read()
        english = [label for label in ('Total Vehicles', '>Contracts<', '>In Progress<', '>Cancelled<')
                   if label in arch]
        self.assertFalse(english)
