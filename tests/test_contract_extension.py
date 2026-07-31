# -*- coding: utf-8 -*-
"""Contract extension: frozen original date and traceability in the contract."""
from datetime import timedelta

from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_extension')
class TestContractExtension(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        self.original_end_date = self.contract.end_date
        self.extension = self.env['vehicle.contract.extension'].create({
            'contract_id': self.contract.id,
            'new_end_date': self.original_end_date + timedelta(days=3),
            'daily_rate': 50.0,
        })

    def test_original_end_date_is_frozen_at_creation(self):
        self.assertEqual(self.extension.original_end_date, self.original_end_date)

    def test_default_get_proposes_the_contract_end_date(self):
        defaults = self.env['vehicle.contract.extension'].with_context(
            default_contract_id=self.contract.id
        ).default_get(['original_end_date', 'contract_id'])

        self.assertEqual(defaults.get('original_end_date'), self.original_end_date)

    def test_days_and_amount_are_computed_from_the_frozen_date(self):
        self.assertEqual(self.extension.extension_days, 3.0)
        self.assertEqual(self.extension.extension_amount, 150.0)

    def test_history_survives_the_contract_end_date_moving(self):
        """Invoicing rewrites contract.end_date; the extension must not follow."""
        self.contract.write({'end_date': self.extension.new_end_date})

        self.assertEqual(self.extension.original_end_date, self.original_end_date)
        self.assertEqual(self.extension.extension_days, 3.0)
        self.assertEqual(self.extension.extension_amount, 150.0)

    def test_signing_posts_to_the_contract_chatter(self):
        before = len(self.contract.message_ids)

        self.extension.action_mark_signed()

        self.assertEqual(self.extension.state, 'signed')
        self.assertGreater(len(self.contract.message_ids), before)
        self.assertIn('Ampliación de Contrato Firmada', self.contract.message_ids[0].body)

    def test_invoicing_updates_the_contract_and_leaves_the_addendum(self):
        self.extension.action_mark_signed()

        self.extension.action_create_extension_invoice()

        self.assertEqual(self.extension.state, 'invoiced')
        self.assertTrue(self.extension.extension_invoice_id)
        self.assertEqual(self.contract.end_date, self.extension.new_end_date)

        # The history is still intact after the contract date moved.
        self.assertEqual(self.extension.original_end_date, self.original_end_date)
        self.assertEqual(self.extension.extension_days, 3.0)
        self.assertEqual(self.extension.extension_amount, 150.0)

        addendum = self.env['ir.attachment'].search([
            ('res_model', '=', 'vehicle.contract'),
            ('res_id', '=', self.contract.id),
            ('name', 'like', 'Addendum_Ampliacion%'),
        ])
        self.assertTrue(addendum)
        self.assertEqual(addendum[0].mimetype, 'application/pdf')

        self.assertIn('Ampliación de Contrato Facturada',
                      self.contract.message_ids[0].body)

    def test_invoice_carries_the_extension_days_and_rate(self):
        self.extension.action_mark_signed()
        self.extension.action_create_extension_invoice()

        line = self.extension.extension_invoice_id.invoice_line_ids[0]
        self.assertEqual(line.quantity, 3.0)
        self.assertEqual(line.price_unit, 50.0)

    def test_cannot_invoice_an_unsigned_extension(self):
        from odoo.exceptions import UserError

        with self.assertRaises(UserError):
            self.extension.action_create_extension_invoice()

    def test_cannot_invoice_twice(self):
        from odoo.exceptions import UserError

        self.extension.action_mark_signed()
        self.extension.action_create_extension_invoice()

        with self.assertRaises(UserError):
            self.extension.action_create_extension_invoice()

    def test_new_end_date_must_be_after_the_original(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env['vehicle.contract.extension'].create({
                'contract_id': self.contract.id,
                'new_end_date': self.original_end_date - timedelta(days=1),
                'daily_rate': 50.0,
            })
