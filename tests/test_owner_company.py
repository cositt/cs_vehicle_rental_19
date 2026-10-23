# -*- coding: utf-8 -*-
"""Mails and documents are signed by the company that owns the vehicle.

The staff act as Sunset, but most of the fleet belongs to Pinveco: a contract
for a Pinveco van went out signed "Sunset" (Juan, 2026-10-23: the owner signs).
"""
from datetime import timedelta

from odoo.tests.common import new_test_user, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_owner_company')
class TestOwnerCompany(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = cls.env['res.company'].create({
            'name': 'Dueña Firmante Test', 'phone': '600111222', 'email': 'duena@example.com'})
        cls.vehicle.company_id = cls.owner
        cls.contract.company_id = cls.company

    def _html(self, report, records):
        html, _type = self.env['ir.actions.report']._render_qweb_html(report, records.ids)
        return html.decode()

    def test_owner_is_the_company_of_the_vehicle(self):
        self.assertEqual(self.contract.owner_company_id, self.owner)
        own = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        self.assertEqual(own.owner_company_id, self.company, 'a vehicle of the same company')

    def test_mails_are_signed_by_the_owner(self):
        for xmlid in ('email_template_vehicle_contract', 'vehicle_rental_booking_mail_template'):
            template = self.env.ref(f'vehicle_rental.{xmlid}')
            body = template._render_field('body_html', self.contract.ids)[self.contract.id]
            self.assertIn(self.owner.name, body, xmlid)
            self.assertNotIn(f'equipo de {self.company.name}', body, xmlid)
        booking = self.env.ref('vehicle_rental.vehicle_rental_booking_mail_template')
        self.assertIn('600111222', booking._render_field('body_html', self.contract.ids)[self.contract.id])

    def test_contract_document_is_headed_by_the_owner(self):
        html = self._html('vehicle_rental.vehicle_contract_report_template', self.contract)
        self.assertIn(self.owner.name, html)

    def test_return_report_and_mail_are_signed_by_the_owner(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.action_confirm_return()
        record = self.env['vehicle.contract.return'].search([('contract_id', '=', self.contract.id)])
        html = self._html('vehicle_rental.vehicle_contract_return_report_template', record)
        self.assertIn(self.owner.name, html)
        template = self.env.ref('vehicle_rental.email_template_vehicle_contract_return')
        body = template._render_field('body_html', record.ids)[record.id]
        self.assertIn(f'equipo de {self.owner.name}', body)

    def test_substitution_addendum_is_signed_by_the_owner(self):
        wizard = self.env['vehicle.substitution.wizard'].create({
            'contract_id': self.contract.id,
            'new_vehicle_id': self.spare_vehicle.id,
            'old_vehicle_odometer': 10500,
            'old_vehicle_fuel_level': '2',
            'new_vehicle_fuel_level': '4',
            'step': '4_confirm',
        })
        self.spare_vehicle.company_id = self.owner
        wizard.action_confirm_substitution()
        substitution = self.env['vehicle.contract.substitution'].search([('contract_id', '=', self.contract.id)])
        html = self._html('vehicle_rental.vehicle_substitution_addendum_report_template', substitution)
        self.assertIn(self.owner.name, html)


@tagged('post_install', '-at_install', 'vehicle_owner_company')
class TestOwnerCompanyAsClerk(TestOwnerCompany):
    """The clerk acts as Sunset only: the owner company is not active, yet it signs.

    Reading the owner company as the clerk raised an access error on the
    hand-over mail, the contract mails and the documents.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.clerk = new_test_user(
            cls.env, login='firma_sunset', groups='base.group_user,fleet.fleet_group_manager',
            company_id=cls.company.id, company_ids=[cls.company.id, cls.owner.id])

    def _clerk(self, records):
        return records.with_user(self.clerk).with_context(allowed_company_ids=[self.company.id])

    def test_mails_render_for_the_clerk(self):
        for xmlid in ('email_template_vehicle_contract', 'vehicle_rental_booking_mail_template'):
            template = self._clerk(self.env.ref(f'vehicle_rental.{xmlid}'))
            body = template._render_field('body_html', self.contract.ids)[self.contract.id]
            self.assertIn(self.owner.name, body, xmlid)
        booking = self._clerk(self.env.ref('vehicle_rental.vehicle_rental_booking_mail_template'))
        self.assertEqual(booking._render_field('email_from', self.contract.ids)[self.contract.id],
                         'duena@example.com')

    def test_hand_over_mail_opens_for_the_clerk(self):
        contract = self._create_contract(self.vehicle, self.customer, status='a_draft')
        contract.write({'start_date': self.end_date + timedelta(days=1),
                        'end_date': self.end_date + timedelta(days=3)})
        action = self._clerk(contract).with_context(hand_over_without_driver=True).a_draft_to_b_in_progress()
        self.assertEqual(action['context']['default_email_from'], 'duena@example.com')

    def test_contract_document_prints_for_the_clerk(self):
        html, _type = self._clerk(self.env['ir.actions.report'])._render_qweb_html(
            'vehicle_rental.vehicle_contract_report_template', self.contract.ids)
        self.assertIn(self.owner.name, html.decode())
