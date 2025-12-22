# -*- coding: utf-8 -*-
# Copyright 2025 Sunset Rent a Car
# Controlador para la página principal de Sunset

from odoo import http
from odoo.http import request


class SunsetHomeController(http.Controller):
    """Controlador para la página principal de Sunset"""

    @http.route('/', type='http', auth='public', website=True)
    def sunset_home(self, **kw):
        """Página principal - renderiza website.homepage para ambos dominios"""
        return request.render('website.homepage', {})

    @http.route('/sunset', type='http', auth='public', website=True)
    def sunset_home_alt(self, **kw):
        """Página principal alternativa"""
        return request.render('website.homepage', {})

    @http.route('/sunset/flota', type='http', auth='public', website=True)
    def sunset_fleet(self, **kw):
        """Página de flota"""
        return request.render('vehicle_rental.sunset_fleet_page', {})

    @http.route('/sunset/categoria/<int:category_id>', type='http', auth='public', website=True)
    def sunset_category(self, category_id, **kw):
        """Página de categoría"""
        return request.render('vehicle_rental.sunset_home_basic', {})

    @http.route('/sunset/delegacion/<string:city>', type='http', auth='public', website=True)
    def sunset_delegation(self, city, **kw):
        """Página de delegación"""
        return request.render('vehicle_rental.sunset_contact_page', {})

    @http.route('/sunset/servicios/<string:service>', type='http', auth='public', website=True)
    def sunset_services(self, service, **kw):
        """Página de servicios"""
        return request.render('vehicle_rental.sunset_services_page', {})

    @http.route('/sunset/seguros', type='http', auth='public', website=True)
    def sunset_seguros(self, **kw):
        """Página de seguros"""
        return request.render('vehicle_rental.sunset_home_basic', {})

    @http.route('/test/flota', type='http', auth='public', website=True)
    def test_fleet(self, **kw):
        """Página de prueba de flota"""
        return request.render('vehicle_rental.sunset_fleet_page', {})

    @http.route('/simple/flota', type='http', auth='public', website=True)
    def simple_fleet(self, **kw):
        """Página simple de flota"""
        return request.render('vehicle_rental.sunset_fleet_page', {})
