# -*- coding: utf-8 -*-
"""Deposit by payment method, as in the general conditions of the tariff.

Credit card 300 EUR; debit card 750 EUR, or 300 EUR with the no-excess
insurance; cash 750 EUR and the no-excess insurance is compulsory; FLEXIRENT
750 EUR whatever the payment. Until now no rule had a deposit, so every
contract (and the website) asked for 0 EUR.
"""
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_deposit')
class TestDepositRules(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company._vehicle_rental_load_deposit_rules()

    def _contract(self, card_type, **values):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write(dict({'deposit_card_type': card_type, 'use_deposit_from_rule': True}, **values))
        return contract

    def test_credit_card_is_300(self):
        self.assertEqual(self._contract('credit').calculated_deposit, 300.0)

    def test_debit_card_is_750(self):
        self.assertEqual(self._contract('debit').calculated_deposit, 750.0)

    def test_debit_card_with_no_excess_insurance_is_300(self):
        contract = self._contract('debit', insurance_type='no_franchise')
        self.assertEqual(contract.calculated_deposit, 300.0)

    def test_cash_is_750(self):
        contract = self._contract('cash', insurance_type='no_franchise')
        self.assertEqual(contract.calculated_deposit, 750.0)

    def test_flexirent_is_750_whatever_the_payment(self):
        contract = self._contract('credit', pricing_type='flexirent')
        self.assertEqual(contract.calculated_deposit, 750.0)

    def test_the_contract_keeps_the_deposit(self):
        contract = self._contract('credit')
        self.assertTrue(contract.if_any_deposit)
        self.assertEqual(contract.deposit, 300.0)

    def test_cash_without_no_excess_insurance_cannot_be_handed_over(self):
        contract = self._contract('cash', insurance_type='basic')
        with self.assertRaises(UserError):
            contract._check_hand_over_ready()

    def test_loading_again_does_not_duplicate_and_fixes_amounts(self):
        Rule = self.env['vehicle.deposit.rule']
        domain = [('vehicle_category_id', '=', self.category.id), ('company_id', '=', self.company.id)]
        Rule.search(domain + [('card_type', '=', 'debit')]).deposit_fixed = 123.0
        self.company._vehicle_rental_load_deposit_rules()
        self.assertEqual(Rule.search_count(domain), 3)
        self.assertEqual(Rule.search(domain + [('card_type', '=', 'debit')]).deposit_fixed, 750.0)


@tagged('post_install', '-at_install', 'vehicle_deposit')
class TestDepositOnScreen(VehicleRentalCase):
    """What the clerk sees while editing, before saving."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company._vehicle_rental_load_deposit_rules()

    def test_deposit_follows_the_rule_before_saving(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'deposit_card_type': 'debit', 'use_deposit_from_rule': True})
        with Form(contract) as form:
            form.deposit_card_type = 'credit'
            self.assertEqual(form.deposit, 300.0)
            form.deposit_card_type = 'debit'
            self.assertEqual(form.deposit, 750.0)

    def test_debit_with_no_excess_insurance_says_why_the_credit_rule_applies(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'deposit_card_type': 'debit', 'insurance_type': 'no_franchise'})
        self.assertIn('sin franquicia', contract.deposit_rule_note)
        contract.insurance_type = 'basic'
        self.assertFalse(contract.deposit_rule_note)

    def test_deposit_can_change_in_progress_until_it_is_charged(self):
        contract = self._create_contract(self.spare_vehicle, self.customer)
        contract.write({'deposit_card_type': 'debit', 'use_deposit_from_rule': True})
        with Form(contract) as form:
            form.deposit_card_type = 'credit'
        self.assertEqual(contract.deposit, 300.0)
