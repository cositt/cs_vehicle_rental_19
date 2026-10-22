# -*- coding: utf-8 -*-
"""Rental prices include VAT (21 %).

The Pinveco tariff says so on every page, so invoices keep the total the
customer was quoted and break the VAT down inside it: instalments used to go
out without any VAT and extensions added 21 % on top. The deposit is not a
sale and carries no VAT; damages stay as they are for now.
"""
from datetime import timedelta

from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_vat')
class TestVatIncluded(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax = cls.company._vehicle_rental_ensure_sale_tax()

    def test_company_has_a_21_percent_tax_included_in_price(self):
        self.assertEqual(self.tax.amount, 21.0)
        self.assertEqual(self.tax.type_tax_use, 'sale')
        self.assertEqual(self.tax.price_include_override, 'tax_included')
        self.assertEqual(self.company._vehicle_rental_ensure_sale_tax(), self.tax,
                         'asking again reuses the same tax')

    def test_new_contract_carries_the_tax_of_its_company(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        self.assertEqual(contract.tax_ids, self.tax)

    def test_instalment_total_is_the_quoted_price_with_vat_inside(self):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'payment_type': 'full_payment', 'use_deposit_from_rule': False,
                        'if_any_deposit': True, 'deposit': 300.0})
        contract.action_create_vehicle_payment()
        option = contract.vehicle_payment_option_ids[0]
        option.action_create_payment_invoice()
        invoice = option.invoice_id
        rent = invoice.invoice_line_ids.filtered(lambda l: l.product_id == contract.invoice_item_id)
        deposit = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == self.env.ref('vehicle_rental.vehicle_rent_deposit'))
        self.assertEqual(rent.price_total, contract.total_vehicle_rent)
        self.assertAlmostEqual(rent.price_subtotal, round(contract.total_vehicle_rent / 1.21, 2))
        self.assertFalse(deposit.tax_ids, 'the deposit carries no VAT')
        self.assertEqual(deposit.price_total, 300.0)

    def test_extension_total_is_days_by_rate_with_vat_inside(self):
        contract = self._create_contract(self.spare_vehicle, self.customer)
        extension = self.env['vehicle.contract.extension'].create({
            'contract_id': contract.id,
            'new_end_date': contract.end_date + timedelta(days=3),
            'daily_rate': 50.0,
        })
        extension.action_mark_signed()
        extension.action_create_extension_invoice()
        invoice = extension.extension_invoice_id
        self.assertEqual(invoice.amount_total, 150.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 123.97)

    def test_applying_sets_the_tax_on_rental_products_and_open_contracts(self):
        open_contract = self._create_contract(self.spare_vehicle, self.customer)
        returned = self._create_contract(self.spare_vehicle, self.customer, status='c_return')
        (open_contract | returned).write({'tax_ids': [(5, 0, 0)]})

        self.company._vehicle_rental_apply_sale_tax()

        rent_product = self.env.ref('vehicle_rental.vehicle_rent_charge')
        sale_taxes = rent_product.taxes_id.filtered(lambda t: t.company_id == self.company)
        self.assertEqual(sale_taxes, self.tax)
        self.assertFalse(self.env.ref('vehicle_rental.vehicle_rent_deposit').taxes_id)
        self.assertFalse(self.env.ref('vehicle_rental.vehicle_damage_amount').taxes_id,
                         'damages stay as they are')
        self.assertEqual(open_contract.tax_ids, self.tax)
        self.assertFalse(returned.tax_ids, 'closed contracts are left alone')
