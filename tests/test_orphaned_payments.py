# -*- coding: utf-8 -*-
"""Paid web bookings whose opportunity was not created are recovered.

Found in the Phase 7 regression: the recovery method existed ("every 30
minutes") but no scheduled action ran it, and it did not mark the payment as
processed, so once scheduled it would have created the opportunity again on
every run.
"""
import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_orphaned_payments')
class TestOrphanedPayments(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env['payment.provider'].search([('code', '=', 'redsys')], limit=1)

    def _paid_booking(self, email):
        start = fields.Date.today() + timedelta(days=20)
        return self.env['payment.transaction'].create({
            'provider_id': self.provider.id, 'payment_method_id': self.provider.payment_method_ids[:1].id,
            'reference': f'ORPHAN-{email}', 'amount': 200.0, 'currency_id': self.company.currency_id.id,
            'partner_id': self.customer.id, 'state': 'done', 'booking_created': False,
            'booking_data_json': json.dumps({
                'customer_name': 'Cliente Huérfano', 'customer_email': email,
                'start_date': str(start), 'end_date': str(start + timedelta(days=3)),
                'category_id': self.category.id, 'company_id': self.company.id,
                'selected_price': 50.0, 'total_price': 150.0})})

    def test_cron_is_scheduled(self):
        cron = self.env.ref('vehicle_rental.cron_process_orphaned_transactions', raise_if_not_found=False)
        # Active on install; whether it stays active is an admin decision (it is off in dev)
        self.assertTrue(cron)
        self.assertEqual((cron.interval_number, cron.interval_type), (30, 'minutes'))

    def test_orphan_gets_one_opportunity(self):
        if not self.provider:
            self.skipTest('Redsys provider not installed')
        tx = self._paid_booking('huerfano@example.com')
        Tx = self.env['payment.transaction']
        Tx._cron_process_orphaned_transactions()
        Tx._cron_process_orphaned_transactions()
        leads = self.env['crm.lead'].search([('email_from', '=', 'huerfano@example.com')])
        self.assertEqual(len(leads), 1)
        self.assertTrue(tx.booking_created)
        self.assertEqual(leads.payment_transaction_id, tx)

    def test_one_failing_payment_does_not_stop_the_others(self):
        if not self.provider:
            self.skipTest('Redsys provider not installed')
        broken = self._paid_booking('roto@example.com')
        broken.booking_data_json = json.dumps({'customer_email': 'roto@example.com'})  # missing fields
        good = self._paid_booking('bueno@example.com')
        self.env['payment.transaction']._cron_process_orphaned_transactions()
        self.assertTrue(good.booking_created)
        self.assertFalse(broken.booking_created)
