# -*- coding: utf-8 -*-
"""Coming back from Redsys never confirms a payment.

Only the Redsys notification (``/payment/redsys/webhook``, signature checked
by ``payment_redsys``) may move a transaction to ``done``. The pages the
customer is redirected to just show the state.
"""
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'vehicle_security')
class TestPaymentReturnPages(HttpCase):

    def setUp(self):
        super().setUp()
        provider = self.env['payment.provider'].create({
            'name': 'Redsys (test)',
            'code': 'redsys',
            'state': 'test',
            'company_id': self.env.company.id,
            # Dummy values: the provider only has to exist, nothing is sent.
            'redsys_merchant_code': '000000001',
            'redsys_merchant_terminal': '1',
            'redsys_secret_key': 'ZHVtbXktdGVzdC1rZXktMDAwMDAwMDA=',
        })
        method = self.env['payment.method'].search([('code', '=', 'card')], limit=1)
        self.tx = self.env['payment.transaction'].create({
            'provider_id': provider.id,
            'payment_method_id': method.id,
            'amount': 900.0,
            'currency_id': self.env.ref('base.EUR').id,
            'partner_id': self.env.ref('base.public_partner').id,
            'reference': 'TEST-RETURN-0001',
            'booking_data_json': '{"customer_name": "Cliente Pendiente"}',
        })

    def _leads(self):
        return self.env['crm.lead'].sudo().search_count([('partner_name', '=', 'Cliente Pendiente')])

    def test_success_page_does_not_confirm_a_pending_payment(self):
        """Anyone opening /rental/success must not turn someone's payment into paid."""
        for method in ('GET', 'POST'):
            with self.subTest(method=method):
                if method == 'GET':
                    response = self.url_open('/rental/success')
                else:
                    response = self.url_open('/rental/success', data={'Ds_Order': self.tx.reference})
                self.assertEqual(response.status_code, 200)
                self.tx.invalidate_recordset()
                self.assertEqual(self.tx.state, 'draft')
                self.assertFalse(self.tx.booking_created)
                self.assertEqual(self._leads(), 0)

    def test_success_page_does_not_claim_payment_without_confirmation(self):
        """The visitor is told the payment is being confirmed, not that it is done."""
        html = self.url_open('/rental/success').text
        self.assertNotIn('Pago realizado', html)

    def test_error_page_answers(self):
        response = self.url_open('/rental/error')
        self.assertEqual(response.status_code, 200)
        self.tx.invalidate_recordset()
        self.assertEqual(self.tx.state, 'draft')

    def test_manual_webhook_is_not_served(self):
        response = self.url_open('/rental/manual-webhook', allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        self.tx.invalidate_recordset()
        self.assertEqual(self.tx.state, 'draft')
