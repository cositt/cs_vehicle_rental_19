# -*- coding: utf-8 -*-
from odoo.addons.website.controllers.main import Website
from odoo import http
from odoo.http import request

class TestEndpoint(Website):
    @http.route('/test/endpoint', auth='public', website=True, type='http')
    def test_endpoint(self):
        return "TEST ENDPOINT WORKS"
