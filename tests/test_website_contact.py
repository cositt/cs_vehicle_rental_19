# -*- coding: utf-8 -*-
"""The public contact page shows the real company and its form is protected."""
import re

from odoo.tests.common import HttpCase, tagged

PLACEHOLDERS = ('Calle Principal', '123 45 67', 'sunsetrentacar.com',
                'Madrid', 'Barcelona', 'Valencia')


@tagged('post_install', '-at_install', 'vehicle_website')
class TestWebsiteContact(HttpCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['website'].get_current_website().company_id
        self.company.partner_id.write({
            'street': 'C/ Marea Baja, 51', 'zip': '29006', 'city': 'Málaga',
            'phone': '+34 600 000 000', 'email': 'contacto@empresa.test',
        })

    def _csrf_from(self, html):
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        self.assertTrue(match, "El formulario no lleva csrf_token")
        return match.group(1)

    def test_page_shows_the_company_data(self):
        html = self.url_open('/contactus').text
        for value in ('C/ Marea Baja, 51', '+34 600 000 000', 'contacto@empresa.test'):
            self.assertIn(value, html)
        for fake in PLACEHOLDERS:
            self.assertNotIn(fake, html, f"Dato inventado en la página: {fake}")

    def test_form_without_csrf_is_rejected(self):
        leads_before = self.env['crm.lead'].sudo().search_count([])
        response = self.url_open('/contactus/enviar', data={
            'name': 'Spam', 'email': 'spam@bot.test',
            'subject': 'Consulta General', 'message': 'hola',
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(self.env['crm.lead'].sudo().search_count([]), leads_before)

    def test_form_with_csrf_creates_the_lead(self):
        token = self._csrf_from(self.url_open('/contactus').text)
        response = self.url_open('/contactus/enviar', data={
            'csrf_token': token, 'name': 'Ana Cliente', 'email': 'ana@cliente.test',
            'phone': '600111222', 'subject': 'Consulta General', 'message': 'Quiero una furgoneta',
        })
        self.assertEqual(response.status_code, 200)
        lead = self.env['crm.lead'].sudo().search([('email_from', '=', 'ana@cliente.test')])
        self.assertEqual(len(lead), 1)
        self.assertEqual(lead.contact_name, 'Ana Cliente')
        for fake in PLACEHOLDERS:
            self.assertNotIn(fake, response.text)
