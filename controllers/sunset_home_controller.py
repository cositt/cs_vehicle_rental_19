# -*- coding: utf-8 -*-
# Copyright 2025 Sunset Rent a Car

from odoo import http
from odoo.http import request


class SunsetHomeController(http.Controller):

    @http.route('/', type='http', auth='public', website=True)
    def sunset_home(self, **kw):
        """Página principal editable"""
        return request.render('website.homepage', {})

    @http.route('/sunset', type='http', auth='public', website=True)
    def sunset_home_alt(self, **kw):
        return request.render('website.homepage', {})

    @http.route('/sunset/flota', type='http', auth='public', website=True)
    def sunset_fleet(self, **kw):
        return request.render('vehicle_rental.sunset_fleet_page', {})

    @http.route('/sunset/categoria/<int:category_id>', type='http', auth='public', website=True)
    def sunset_category(self, category_id, **kw):
        return request.render('vehicle_rental.sunset_home_basic', {})

    @http.route('/sunset/delegacion/<string:city>', type='http', auth='public', website=True)
    def sunset_delegation(self, city, **kw):
        return request.render('vehicle_rental.sunset_contact_page', {})

    @http.route('/sunset/servicios/<string:service>', type='http', auth='public', website=True)
    def sunset_services(self, service, **kw):
        return request.render('vehicle_rental.sunset_services_page', {})

    @http.route('/sunset/seguros', type='http', auth='public', website=True)
    def sunset_seguros(self, **kw):
        return request.render('vehicle_rental.sunset_home_basic', {})

    @http.route('/test/flota', type='http', auth='public', website=True)
    def test_fleet(self, **kw):
        return request.render('vehicle_rental.sunset_fleet_page', {})

    @http.route('/simple/flota', type='http', auth='public', website=True)
    def simple_fleet(self, **kw):
        return request.render('vehicle_rental.sunset_fleet_page', {})
