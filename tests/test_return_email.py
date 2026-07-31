# -*- coding: utf-8 -*-
"""Closing email sent to the customer when the return is confirmed."""
from odoo.tests.common import tagged

from .common import VehicleRentalCase

TEMPLATE = 'vehicle_rental.email_template_vehicle_contract_return'


@tagged('post_install', '-at_install', 'vehicle_return', 'vehicle_mail')
class TestReturnClosingEmail(VehicleRentalCase):

    def setUp(self):
        super().setUp()
        self.template = self.env.ref(TEMPLATE)
        self.mail_model = self.env['mail.mail']

    def _new_mails(self, before_ids):
        return self.mail_model.sudo().search([('id', 'not in', before_ids)])

    def test_template_does_not_use_the_default_recipient(self):
        """Odoo 19 defaults ``use_default_to`` to True, which empties partner_to."""
        self.assertFalse(self.template.use_default_to)
        self.assertTrue(self.template.partner_to)

    def test_template_resolves_the_contract_customer(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.action_confirm_return()
        record = self.contract.return_ids

        partner_to = self.template._render_field('partner_to', record.ids)[record.id]
        subject = self.template._render_field('subject', record.ids)[record.id]

        self.assertEqual(str(partner_to), str(self.customer.id))
        self.assertIn(self.contract.reference_no, subject)

    def test_confirming_queues_the_email_with_the_acta_attached(self):
        before_ids = self.mail_model.sudo().search([]).ids
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({'send_closing_email': True})

        wizard.action_confirm_return()

        mails = self._new_mails(before_ids)
        self.assertEqual(len(mails), 1)
        mail = mails[0]
        self.assertIn(self.customer, mail.recipient_ids)
        self.assertEqual(mail.state, 'outgoing', 'must be queued, not sent inline')
        self.assertTrue(
            any(att.name.startswith('Acta_Devolución')
                for att in mail.attachment_ids),
            'the acta PDF must travel with the closing email',
        )

    def test_email_body_carries_the_process_summary(self):
        before_ids = self.mail_model.sudo().search([]).ids
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({'send_closing_email': True})

        wizard.action_confirm_return()

        body = self._new_mails(before_ids).body_html
        self.assertIn(self.contract.reference_no, body)
        self.assertIn('devuelto correctamente', body)
        self.assertIn(self.vehicle.license_plate, body)

    def test_no_email_when_the_box_is_unchecked(self):
        before_ids = self.mail_model.sudo().search([]).ids
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({'send_closing_email': False})

        wizard.action_confirm_return()

        self.assertFalse(self._new_mails(before_ids))

    def test_customer_without_email_is_logged_instead_of_failing(self):
        contract = self._create_contract(self.spare_vehicle, self.customer_no_email)
        wizard = self._fill_valid_return(self._open_return_wizard(contract))
        wizard.write({'send_closing_email': True})

        wizard.action_confirm_return()

        self.assertEqual(contract.status, 'c_return')
        bodies = ' '.join(contract.message_ids.mapped('body'))
        self.assertIn('no tiene', bodies)

    def test_action_send_return_email_reports_a_missing_address(self):
        contract = self._create_contract(self.spare_vehicle, self.customer_no_email)
        wizard = self._fill_valid_return(self._open_return_wizard(contract))
        wizard.write({'send_closing_email': False})
        wizard.action_confirm_return()

        self.assertFalse(contract.return_ids.action_send_return_email())

    def test_process_invoices_are_listed_for_the_summary(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({
            'has_damage': True,
            'damage_description': '<p>Golpe</p>',
            'damage_amount': 90.0,
            'invoice_damage_now': True,
        })
        wizard.action_confirm_return()
        record = self.contract.return_ids

        invoices = record.get_process_invoices()

        self.assertIn(record.damage_invoice_id, invoices)

    def test_fuel_label_is_human_readable(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.action_confirm_return()
        record = self.contract.return_ids

        self.assertEqual(record.fuel_label('4'), 'Lleno')
        self.assertEqual(record.fuel_label('3'), '3/4')
        self.assertEqual(record.fuel_label(False), '-')
