# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class WebsiteContractBookingTest(http.Controller):
    
    @http.route('/web/booking-enquiry-test', auth='public', website=True, type='http')
    def contract_booking_enquiry_test(self, **kw):
        """Test Booking Enquiry"""
        return "<h1>Test Booking Enquiry - Funcionando</h1>"
