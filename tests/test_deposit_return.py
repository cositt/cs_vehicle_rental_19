# -*- coding: utf-8 -*-
"""The deposit is given back from the vehicle return.

The deposit is charged in the first installment (or in the consolidated
invoice of a group), never in ``deposit_invoice_id``, so the old "Return
Deposit Invoice" button never showed up and the deposit could not be given
back (prod, 2026-10-26). The return wizard now shows the deposit charged,
the damages and the net amount, and creates the deposit credit note.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_deposit_return')
class TestDepositReturn(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        self.deposit_product = self.env.ref('vehicle_rental.vehicle_rent_deposit')

    def _charge_deposit(self, contract, amount=300.0, post=True):
        contract.write({'use_deposit_from_rule': False, 'if_any_deposit': True, 'deposit': amount})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': contract.customer_id.id,
            'vehicle_contract_id': contract.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.deposit_product.id, 'name': 'Depósito de Seguridad',
                'quantity': 1, 'price_unit': amount, 'tax_ids': [(6, 0, [])]})],
        })
        if post:
            invoice.action_post()
        return invoice

    def test_deposit_charged_comes_from_the_installment_invoice(self):
        self._charge_deposit(self.contract, 300.0)
        self.assertEqual(self.contract.deposit_charged, 300.0)

    def test_draft_or_cancelled_invoice_is_not_a_charged_deposit(self):
        self._charge_deposit(self.contract, 300.0, post=False)
        self.assertEqual(self.contract.deposit_charged, 0.0)

    def test_wizard_shows_deposit_damages_and_net(self):
        self._charge_deposit(self.contract, 300.0)
        wizard = self._fill_valid_return(self._open_return_wizard(),
                                         has_damage=True, damage_description='<p>Golpe</p>',
                                         damage_amount=120.0)
        self.assertEqual(wizard.deposit_charged, 300.0)
        self.assertTrue(wizard.refund_deposit)
        self.assertEqual(wizard.deposit_to_refund, 300.0)
        self.assertEqual(wizard.deposit_net_to_customer, 180.0)

    def test_return_creates_the_deposit_credit_note(self):
        self._charge_deposit(self.contract, 300.0)
        self._fill_valid_return(self._open_return_wizard()).action_confirm_return()
        refund = self.contract.return_deposit_invoice_id
        self.assertTrue(refund)
        self.assertEqual(refund.move_type, 'out_refund')
        self.assertEqual(refund.state, 'draft')
        self.assertEqual(refund.partner_id, self.customer)
        self.assertEqual(refund.vehicle_contract_id, self.contract)
        self.assertEqual(refund.invoice_line_ids.product_id, self.deposit_product)
        self.assertEqual(refund.amount_total, 300.0)

    def test_part_of_the_deposit_can_be_kept(self):
        self._charge_deposit(self.contract, 300.0)
        wizard = self._fill_valid_return(self._open_return_wizard(), deposit_to_refund=250.0)
        wizard.action_confirm_return()
        self.assertEqual(self.contract.return_deposit_invoice_id.amount_total, 250.0)

    def test_no_credit_note_when_unticked(self):
        self._charge_deposit(self.contract, 300.0)
        self._fill_valid_return(self._open_return_wizard(), refund_deposit=False).action_confirm_return()
        self.assertFalse(self.contract.return_deposit_invoice_id)
        self.assertTrue(self.contract.can_return_deposit)

    def test_no_deposit_charged_means_nothing_to_refund(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        self.assertEqual(wizard.deposit_charged, 0.0)
        self.assertFalse(wizard.refund_deposit)
        wizard.action_confirm_return()
        self.assertFalse(self.contract.return_deposit_invoice_id)
        self.assertFalse(self.contract.can_return_deposit)

    def test_deposit_from_the_group_invoice_counts(self):
        group = self.env['vehicle.contract.group'].create({'customer_id': self.customer.id})
        self.contract.write({'group_id': group.id, 'use_deposit_from_rule': False,
                             'if_any_deposit': True, 'deposit': 200.0})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.customer.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.deposit_product.id,
                'name': '[%s] Depósito de Seguridad' % self.contract.vehicle_id.name,
                'quantity': 1, 'price_unit': 200.0, 'tax_ids': [(6, 0, [])]})]})
        invoice.action_post()
        group.invoice_ids = [(4, invoice.id)]
        self.assertEqual(self.contract.deposit_charged, 200.0)

    def test_contract_button_after_return_without_refund(self):
        """Refund later from the contract: the wizard proposes the charged deposit."""
        self._charge_deposit(self.contract, 300.0)
        self._fill_valid_return(self._open_return_wizard(), refund_deposit=False).action_confirm_return()
        wizard = self.env['return.deposit'].with_context(active_id=self.contract.id).create({})
        self.assertEqual(wizard.return_deposit, 300.0)
        wizard.create_return_deposit_invoice()
        self.assertEqual(self.contract.return_deposit_invoice_id.amount_total, 300.0)
        self.assertFalse(self.contract.can_return_deposit)
