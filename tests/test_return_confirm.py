# -*- coding: utf-8 -*-
"""The eight effects triggered when a return is confirmed."""
from odoo.tests.common import tagged

from .common import VehicleRentalCase, PNG_1PX, FUEL_FULL, FUEL_THREE_QUARTERS


@tagged('post_install', '-at_install', 'vehicle_return')
class TestReturnConfirm(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        self.wizard = self._fill_valid_return(self._open_return_wizard())

    def test_creates_the_return_record_with_the_captured_state(self):
        odometer_at_delivery = self.contract.last_odometer

        self.wizard.action_confirm_return()

        self.assertEqual(self.contract.return_count, 1)
        record = self.contract.return_ids
        self.assertEqual(record.vehicle_id, self.vehicle)
        self.assertEqual(record.odometer, self.wizard.odometer)
        self.assertEqual(record.odometer_start, odometer_at_delivery)
        self.assertEqual(record.fuel_level, FUEL_THREE_QUARTERS)
        self.assertEqual(record.fuel_level_start, FUEL_FULL)
        self.assertTrue(record.inspection_done)
        self.assertEqual(record.km_driven, 1200)

    def test_registers_the_reading_in_the_vehicle_odometer_history(self):
        odometer_model = self.env['fleet.vehicle.odometer']
        before = odometer_model.search_count([('vehicle_id', '=', self.vehicle.id)])

        self.wizard.action_confirm_return()

        readings = odometer_model.search(
            [('vehicle_id', '=', self.vehicle.id)], order='id desc')
        self.assertEqual(len(readings) - before, 1)
        self.assertEqual(readings[0].value, self.wizard.odometer)

    def test_releases_the_vehicle(self):
        """Whatever state the vehicle was left in, the return puts it back in service."""
        self.vehicle.write({'status': 'in_maintenance'})

        self.wizard.action_confirm_return()

        self.assertEqual(self.vehicle.status, 'available')

    def test_updates_the_contract_odometer(self):
        expected = self.wizard.odometer

        self.wizard.action_confirm_return()

        self.assertEqual(self.contract.last_odometer, expected)

    def test_moves_the_contract_to_returned(self):
        self.wizard.action_confirm_return()

        self.assertEqual(self.contract.status, 'c_return')

    def test_generates_the_acta_and_attaches_it_to_the_contract(self):
        self.wizard.action_confirm_return()

        record = self.contract.return_ids
        self.assertTrue(record.acta_generated)
        self.assertTrue(record.acta_pdf)

        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'vehicle.contract'),
            ('res_id', '=', self.contract.id),
            ('name', '=', record.acta_filename),
        ])
        self.assertEqual(len(attachment), 1)
        self.assertEqual(attachment.mimetype, 'application/pdf')

    def test_posts_the_summary_in_the_contract_chatter(self):
        before = len(self.contract.message_ids)

        self.wizard.action_confirm_return()

        messages = self.contract.message_ids
        self.assertGreater(len(messages), before)
        body = messages[0].body
        self.assertIn('Vehículo Devuelto', body)
        self.assertIn('Inspeccionado — sin daños', body)
        self.assertTrue(messages[0].attachment_ids)

    def test_chatter_says_pending_appraisal_when_amount_is_zero(self):
        self.wizard.write({
            'has_damage': True,
            'damage_description': '<p>Rayón lateral</p>',
            'damage_amount': 0.0,
        })

        self.wizard.action_confirm_return()

        body = self.contract.message_ids[0].body
        self.assertIn('importe pendiente de valorar', body)

    def test_chatter_shows_the_amount_when_appraised(self):
        self.wizard.write({
            'has_damage': True,
            'damage_description': '<p>Rayón lateral</p>',
            'damage_amount': 150.0,
        })

        self.wizard.action_confirm_return()

        body = self.contract.message_ids[0].body
        self.assertIn('150.00', body)
        self.assertNotIn('importe pendiente de valorar', body)

    def test_chatter_records_the_collected_signature(self):
        self.wizard.write({
            'request_signature': True,
            'customer_signature': PNG_1PX,
        })

        self.wizard.action_confirm_return()

        self.assertIn('Firma del cliente', self.contract.message_ids[0].body)
        self.assertTrue(self.contract.return_ids.signature_date)

    def test_invoices_the_damage_when_requested(self):
        self.wizard.write({
            'has_damage': True,
            'damage_description': '<p>Espejo roto</p>',
            'damage_amount': 200.0,
            'invoice_damage_now': True,
        })

        self.wizard.action_confirm_return()

        invoice = self.contract.return_ids.damage_invoice_id
        self.assertTrue(invoice)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(invoice.amount_untaxed, 200.0)

    def test_does_not_invoice_when_not_requested(self):
        self.wizard.write({
            'has_damage': True,
            'damage_description': '<p>Espejo roto</p>',
            'damage_amount': 200.0,
            'invoice_damage_now': False,
        })

        self.wizard.action_confirm_return()

        self.assertFalse(self.contract.return_ids.damage_invoice_id)

    def test_damage_can_be_invoiced_later_from_the_return_record(self):
        self.wizard.write({
            'has_damage': True,
            'damage_description': '<p>Golpe trasero</p>',
            'damage_amount': 0.0,
        })
        self.wizard.action_confirm_return()
        record = self.contract.return_ids

        # The appraisal arrives afterwards.
        record.damage_amount = 320.0
        record.action_create_damage_invoice()

        self.assertTrue(record.damage_invoice_id)
        self.assertEqual(record.damage_invoice_id.amount_untaxed, 320.0)

    def test_invoicing_twice_is_refused(self):
        self.wizard.write({
            'has_damage': True,
            'damage_description': '<p>Golpe</p>',
            'damage_amount': 100.0,
            'invoice_damage_now': True,
        })
        self.wizard.action_confirm_return()
        record = self.contract.return_ids
        first_invoice = record.damage_invoice_id

        result = record.action_create_damage_invoice()

        self.assertEqual(result.get('tag'), 'display_notification')
        self.assertEqual(record.damage_invoice_id, first_invoice)

    def test_returns_to_the_contract_form(self):
        action = self.wizard.action_confirm_return()

        self.assertEqual(action['res_model'], 'vehicle.contract')
        self.assertEqual(action['res_id'], self.contract.id)
        self.assertEqual(action['target'], 'current')
