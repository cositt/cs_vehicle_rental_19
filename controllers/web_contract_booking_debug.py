# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class WebsiteContractBookingDebug(http.Controller):
    
    @http.route('/web/booking-enquiry-debug', auth='public', website=True, type='http')
    def contract_booking_enquiry_debug(self, **kw):
        """Debug Booking Enquiry"""
        try:
            # Obtener categorías de vehículos
            categories = request.env['fleet.vehicle.model.category'].sudo().search([], limit=5)
            
            values = {
                'vehicle_categories': categories,
            }
            
            return request.render('vehicle_rental.booking_enquiry_simple', values)
        except Exception as e:
            return f"<h1>Error: {str(e)}</h1>"
