# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SunsetContactTestController(http.Controller):
    """Controlador de prueba para la página de contacto de Sunset"""

    @http.route('/sunset/contacto-test', type='http', auth='public', website=True)
    def sunset_contact_test(self, **kw):
        """Página de contacto de prueba"""
        
        return request.render('vehicle_rental.sunset_contact_basic', {
            'contact_info': {
                'company_name': 'Sunset Rent a Car',
                'address': 'Calle Principal 123, 28001 Madrid, España',
                'phone': '+34 91 123 45 67',
                'email': 'info@sunsetrentacar.com',
            },
            'delegations': [],
        })
