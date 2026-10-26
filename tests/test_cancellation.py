# -*- coding: utf-8 -*-
"""Cancelling a contract and charging for it.

Found in the Phase 7 regression:
- the status read "Cancelar" (the verb) on the status bar and in the chatter;
- the contract was cancelled at once, without asking;
- a booking still in draft could not be cancelled;
- the cancellation charge asked for a policy, and there is none to choose;
- a charge of 0 made an empty invoice;
- the deposit of a cancelled contract could not be given back.
"""
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_cancellation')
class TestCancellation(VehicleRentalCase):

    def _form_arch(self):
        return self.env['vehicle.contract'].get_view(view_type='form')['arch']

    def _button(self, marker):
        arch = self._form_arch()
        position = arch.index(marker)
        return arch[arch.rindex('<button', 0, position):arch.index('>', position)]

    def test_cancelled_status_reads_cancelado(self):
        labels = dict(self.env['vehicle.contract'].with_context(lang='es_ES')._fields['status']
                      ._description_selection(self.env['vehicle.contract'].with_context(lang='es_ES').env))
        self.assertEqual(labels['d_cancel'], 'Cancelado')

    def test_cancel_asks_first_and_works_on_bookings(self):
        button = self._button('name="c_return_to_d_cancel"')
        self.assertIn('confirm=', button)
        self.assertNotIn("status != 'b_in_progress'", button)
        booking = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        booking.c_return_to_d_cancel()
        self.assertEqual(booking.status, 'd_cancel')

    def test_returned_contract_cannot_be_cancelled(self):
        self.contract.status = 'c_return'
        with self.assertRaises(UserError):
            self.contract.c_return_to_d_cancel()

    def test_charge_without_policy(self):
        self.contract.c_return_to_d_cancel()
        self.assertNotIn("required=\"status == 'd_cancel'\"", self._form_arch())
        self.contract.cancellation_charge = 80.0
        self.contract.cancellation_charge_invoice()
        invoice = self.contract.cancellation_invoice_id
        self.assertEqual(invoice.amount_untaxed, 80.0)
        self.assertTrue(invoice.invoice_line_ids.name)

    def test_charge_of_zero_makes_no_invoice(self):
        self.contract.c_return_to_d_cancel()
        with self.assertRaises(UserError):
            self.contract.cancellation_charge_invoice()
        self.assertFalse(self.contract.cancellation_invoice_id)

    def test_deposit_can_be_returned_after_cancelling(self):
        self.assertIn('can_return_deposit', self._button('string="Devolver fianza"'))
        self.contract.write({'use_deposit_from_rule': False, 'if_any_deposit': True, 'deposit': 300.0})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.customer.id,
            'vehicle_contract_id': self.contract.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.env.ref('vehicle_rental.vehicle_rent_deposit').id,
                'name': 'Depósito de Seguridad', 'quantity': 1, 'price_unit': 300.0,
                'tax_ids': [(6, 0, [])]})]})
        invoice.action_post()
        self.contract.status = 'd_cancel'
        self.assertTrue(self.contract.can_return_deposit)
