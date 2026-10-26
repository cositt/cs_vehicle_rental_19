# -*- coding: utf-8 -*-
"""Handing over several contracts mails each customer.

Jesús Muñoz, 2026-10-22: «estoy mandando los contratos... y no llegan». In
production the 3 mails of a group handed over with «Entregar todos»
(2026-10-26) failed with «mail_email_missing»: the mass mail had no recipient.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_hand_over_mail')
class TestGroupHandOverMail(VehicleRentalCase):

    def _draft(self, vehicle):
        return self.env['vehicle.contract'].create({
            'customer_id': self.customer.id, 'vehicle_id': vehicle.id,
            'rent_type': 'days', 'rent': 50.0,
            'start_date': self.start_date, 'end_date': self.end_date})

    def test_each_contract_mails_its_customer(self):
        self.contract.write({'status': 'c_return'})
        contracts = self._draft(self.vehicle) | self._draft(self.spare_vehicle)
        action = contracts.with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
        composer = self.env['mail.compose.message'].with_context(action['context']).create({})
        composer.action_send_mail()
        mails = self.env['mail.mail'].sudo().search([
            ('model', '=', 'vehicle.contract'), ('res_id', 'in', contracts.ids)])
        self.assertEqual(len(mails), 2)
        for mail in mails:
            with self.subTest(contract=mail.res_id):
                self.assertTrue(self.customer in mail.recipient_ids
                                or self.customer.email in (mail.email_to or ''),
                                'the mail has no recipient')
