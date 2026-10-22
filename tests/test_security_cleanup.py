# -*- coding: utf-8 -*-
"""Debug endpoints are gone and the print menu has no duplicates."""
from odoo.tests.common import HttpCase, TransactionCase, tagged

REMOVED_ROUTES = (
    '/debug/domain',
    '/test/vehicles',
    '/test/trigger-lead',
    '/test/endpoint',
    '/web/booking-enquiry-debug',
    '/web/booking-enquiry-test',
    '/sunset/contacto-test',
    '/test/flota',
    '/simple/flota',
    '/web/test-lead-creation',
    '/web/test-lead-no-html',
    '/web/test-direct-sql',
    '/test/rental-endpoint',
    '/rental/payment/test',
    '/rental/payment-test',
    '/rental/debug',
    '/rental/payment-form-debug',
    '/web/rental/payment',
)


@tagged('post_install', '-at_install', 'vehicle_security')
class TestDebugRoutesRemoved(HttpCase):

    def test_debug_and_test_routes_are_not_served(self):
        """None of the old debugging endpoints may answer on the public site."""
        for route in REMOVED_ROUTES:
            with self.subTest(route=route):
                response = self.url_open(route, allow_redirects=False)
                self.assertEqual(
                    response.status_code, 404,
                    f"{route} sigue respondiendo ({response.status_code})")


PUBLIC_PAGES = (
    '/',
    '/sunset',
    '/sunset/flota',
    '/sunset/seguros',
    '/our-services',
    '/contactus',
    '/pinveco',
    '/pinveco/flota',
    '/web/booking-enquiry',
)


@tagged('post_install', '-at_install', 'vehicle_security')
class TestPublicPagesRender(HttpCase):

    def test_public_pages_answer(self):
        """Every page of the public site renders for an anonymous visitor."""
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                response = self.url_open(page)
                self.assertEqual(response.status_code, 200,
                                 f"{page} devuelve {response.status_code}")

    def test_no_view_carries_an_xml_declaration(self):
        """Odoo 19 cannot parse an arch starting with <?xml ... encoding?>."""
        broken = self.env['ir.ui.view'].with_context(active_test=False).search([
            ('arch_db', 'like', '<?xml'),
        ])
        self.assertFalse(broken, f"Vistas con declaración XML: {broken.mapped('key')}")


@tagged('post_install', '-at_install', 'vehicle_security')
class TestContractPrintMenu(TransactionCase):

    def test_contract_report_is_offered_once(self):
        """The print menu lists the contract a single time."""
        bound = self.env['ir.actions.report'].search([
            ('model', '=', 'vehicle.contract'),
            ('report_name', '=', 'vehicle_rental.vehicle_contract_report_template'),
            ('binding_model_id', '!=', False),
        ])
        self.assertEqual(len(bound), 1)

    def test_both_report_xmlids_still_resolve(self):
        """The print button and the email action keep working."""
        for xmlid in ('vehicle_rental.vehicle_contract_report',
                      'vehicle_rental.action_vehicle_contract_report'):
            with self.subTest(xmlid=xmlid):
                self.assertTrue(self.env.ref(xmlid, raise_if_not_found=False))
