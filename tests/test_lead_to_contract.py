# -*- coding: utf-8 -*-
"""From an opportunity to a contract.

Found in the Phase 7 regression:
- the web payment of the opportunity was looked up by e-mail among the last
  48 hours only: converted later, the contract lost the price and the payment;
- an opportunity without web payment (a phone call) gave a price of 0, so the
  contract could not be created, and made a confirmed sale order as if paid;
- the lead creation wrote the customer's ID, licence and address to a plain
  file in /tmp.
"""
import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_lead_contract')
class TestLeadToContract(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for km in ('100', '350'):
            cls.env['vehicle.pricing.rule'].create({
                'vehicle_category_id': cls.category.id, 'pricing_type': 'standard', 'km_range': km,
                'duration_range': '3-5d', 'price_per_unit': 70.0, 'valid_from': fields.Date.today()})
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Llamada de cliente', 'partner_id': cls.customer.id, 'type': 'opportunity',
            'email_from': cls.customer.email})

    def _convert(self, lead=None):
        wizard = self.env['lead.rental.contract'].create({
            'crm_lead_id': (lead or self.lead).id, 'partner_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'start_date': self.now + timedelta(days=10), 'end_date': self.now + timedelta(days=14)})
        action = wizard.action_create_rental_contract()
        return self.env['vehicle.contract'].browse(action['res_id'])

    def test_opportunity_without_web_payment(self):
        contract = self._convert()
        self.assertEqual(contract.rent, 70.0, 'the tariff, not 0')
        self.assertFalse(contract.sale_order_id, 'no confirmed sale order without payment')

    def test_web_payment_found_days_later(self):
        provider = self.env['payment.provider'].search([('code', '=', 'redsys')], limit=1)
        if not provider:
            self.skipTest('Redsys provider not installed')
        tx = self.env['payment.transaction'].create({
            'provider_id': provider.id, 'payment_method_id': provider.payment_method_ids[:1].id,
            'reference': 'TEST-LEAD-TX', 'amount': 280.0, 'currency_id': self.company.currency_id.id,
            'partner_id': self.customer.id, 'state': 'done',
            'booking_data_json': json.dumps({'customer_email': self.customer.email, 'selected_price': 65.0,
                                             'total_price': 260.0, 'num_days': 4})})
        self.env.cr.execute("UPDATE payment_transaction SET create_date = %s WHERE id = %s",
                            [fields.Datetime.now() - timedelta(days=4), tx.id])
        self.lead.payment_transaction_id = tx
        contract = self._convert()
        self.assertEqual(contract.rent, 65.0)
        self.assertTrue(contract.sale_order_id)

    def test_no_personal_data_in_tmp_files(self):
        source = open(file_path('vehicle_rental/models/payment_redsys_inherit.py')).read()
        self.assertNotIn('/tmp/', source)


@tagged('post_install', '-at_install', 'vehicle_lead_contract')
class TestSaleOrderToContract(VehicleRentalCase):

    def test_contract_keeps_the_price_agreed_in_the_order(self):
        """The contract ignored the order and took the tariff (or failed without one)."""
        rent = self.env.ref('vehicle_rental.vehicle_rent_charge')
        rent = rent.product_variant_ids[:1] if rent._name == 'product.template' else rent
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id, 'vehicle_id': self.spare_vehicle.id,
            'order_line': [(0, 0, {'product_id': rent.id, 'product_uom_qty': 4, 'price_unit': 55.0})]})
        order.action_confirm()
        wizard = self.env['sale.order.to.vehicle.contract'].create({
            'sale_order_id': order.id, 'partner_id': self.customer.id, 'vehicle_id': self.spare_vehicle.id,
            'start_date': self.now + timedelta(days=10), 'end_date': self.now + timedelta(days=14)})
        wizard.action_create_vehicle_contract()
        self.assertEqual(order.vehicle_contract_id.rent, 55.0)
