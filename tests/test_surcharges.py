# -*- coding: utf-8 -*-
"""Surcharges of the general conditions of the tariff, as extra services.

Delivery at another branch 60 EUR + VAT, pick-up or return out of business
hours 20 EUR, tank not full 20 EUR VAT included (plus the missing fuel) and
lost beacon 35 EUR + VAT. Extra services take the tax of their product in
the contract's company; a product without tax takes the VAT-included tax of
the contract, like the rent.
"""
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_surcharges')
class TestSurcharges(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.included = cls.company._vehicle_rental_ensure_sale_tax()
        cls.company._vehicle_rental_load_surcharges()

    def _product(self, name):
        return self.env.ref(f'vehicle_rental.{name}')

    def _taxes(self, product):
        return product.taxes_id.filtered(lambda t: t.company_id == self.company)

    def test_prices_and_vat_of_the_tariff(self):
        expected = {
            'surcharge_other_branch': (60.0, 'tax_excluded'),
            'surcharge_out_of_hours': (20.0, 'tax_included'),
            'surcharge_fuel_not_full': (20.0, 'tax_included'),
            'surcharge_lost_beacon': (35.0, 'tax_excluded'),
        }
        for name, (price, vat) in expected.items():
            product = self._product(name)
            taxes = self._taxes(product)
            self.assertEqual(product.lst_price, price, name)
            self.assertEqual(len(taxes), 1, name)
            self.assertEqual(taxes.amount, 21.0, name)
            self.assertEqual(taxes.price_include_override or 'tax_excluded', vat, name)

    def _invoice_with(self, product):
        contract = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        contract.write({'payment_type': 'full_payment', 'extra_service_ids': [(0, 0, {
            'product_id': product.id, 'product_qty': 1, 'amount': product.lst_price})]})
        contract.action_create_vehicle_payment()
        option = contract.vehicle_payment_option_ids[0]
        option.action_create_payment_invoice()
        return option.invoice_id.invoice_line_ids.filtered(lambda l: l.product_id == product)

    def test_surcharge_plus_vat_adds_21_percent(self):
        line = self._invoice_with(self._product('surcharge_other_branch'))
        self.assertEqual(line.price_subtotal, 60.0)
        self.assertEqual(line.price_total, 72.6)

    def test_surcharge_vat_included_keeps_its_price(self):
        line = self._invoice_with(self._product('surcharge_out_of_hours'))
        self.assertEqual(line.price_total, 20.0)

    def test_extra_service_invoice_uses_the_product_vat(self):
        product = self._product('surcharge_lost_beacon')
        contract = self._create_contract(self.spare_vehicle, self.customer)
        contract.write({'extra_service_ids': [(0, 0, {
            'product_id': product.id, 'product_qty': 1, 'amount': product.lst_price})]})
        contract.action_create_extra_service_charge_invoice()
        self.assertAlmostEqual(contract.extra_service_invoice_id.amount_total, 42.35)

    def test_loading_again_does_not_duplicate_taxes(self):
        self.company._vehicle_rental_load_surcharges()
        self.assertEqual(len(self._taxes(self._product('surcharge_other_branch'))), 1)
