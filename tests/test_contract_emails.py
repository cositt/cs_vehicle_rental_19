# -*- coding: utf-8 -*-
"""Mails of the contract read like the documents of the office.

They showed the dates in UTC and raw ("2026-12-01 08:00:00" for 9:00 in
Málaga), the total as "225.0 €" and loose commas in incomplete addresses.
"""
from datetime import datetime

from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_emails')
class TestContractEmails(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.booked = cls._create_contract(cls.spare_vehicle, cls.customer, status='a_draft')
        cls.booked.write({
            # 8:00 UTC is 9:00 in Madrid in December
            'start_date': datetime(2026, 12, 1, 8, 0),
            'end_date': datetime(2026, 12, 4, 8, 0),
            'rent': 75.0,
            'pick_up_street': 'Calle Marea Baja, 51', 'pick_up_street2': False,
            'pick_up_city': 'Málaga', 'pick_up_zip': '29006', 'pick_up_state_id': False,
        })

    def _body(self, xmlid):
        template = self.env.ref(f'vehicle_rental.{xmlid}').with_context(lang='es_ES')
        return template._render_field('body_html', self.booked.ids)[self.booked.id]

    def _check_formats(self, body):
        self.assertIn('01/12/2026 09:00', body)
        self.assertNotIn('2026-12-01', body)
        self.assertNotIn(', ,', body)

    def test_contract_mail_shows_local_dates_and_formatted_total(self):
        body = self._body('email_template_vehicle_contract')
        self._check_formats(body)
        self.assertIn('225,00', body)
        self.assertNotIn('225.0 ', body)
        self.assertIn(self.booked.company_id.name, body)

    def test_booking_mail_is_in_spanish_with_local_dates(self):
        body = self._body('vehicle_rental_booking_mail_template')
        self._check_formats(body)
        self.assertIn('Calle Marea Baja, 51', body)
        self.assertIn('29006 Málaga', body)
        self.assertNotIn('Dear', body)
