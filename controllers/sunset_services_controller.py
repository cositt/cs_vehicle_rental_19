# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class SunsetServicesController(http.Controller):

    @http.route('/our-services', type='http', auth='public', website=True)
    def sunset_services(self, **kwargs):
        """Página de servicios de Sunset"""
        
        # Datos de servicios principales
        services = [
            {
                'id': 1,
                'name': 'Alquiler de Vehículos',
                'description': 'Amplia flota de vehículos para todas tus necesidades de transporte',
                'icon': 'fa-car',
                'features': [
                    'Vehículos de todas las categorías',
                    'Precios competitivos',
                    'Disponibilidad 24/7',
                    'Seguro incluido'
                ]
            },
            {
                'id': 2,
                'name': 'Servicio de Chófer',
                'description': 'Conductores profesionales para tus desplazamientos',
                'icon': 'fa-user-tie',
                'features': [
                    'Conductores experimentados',
                    'Servicio puerta a puerta',
                    'Disponibilidad inmediata',
                    'Vehículos de lujo'
                ]
            },
            {
                'id': 3,
                'name': 'Transporte Corporativo',
                'description': 'Soluciones de transporte para empresas y eventos',
                'icon': 'fa-building',
                'features': [
                    'Flota empresarial',
                    'Gestión de eventos',
                    'Contratos personalizados',
                    'Soporte 24/7'
                ]
            }
        ]
        
        # Servicios adicionales
        additional_services = [
            {
                'name': 'Seguro Completo',
                'description': 'Cobertura total para tu tranquilidad',
                'icon': 'fa-shield-alt'
            },
            {
                'name': 'Entrega a Domicilio',
                'description': 'Te llevamos el vehículo donde lo necesites',
                'icon': 'fa-truck'
            },
            {
                'name': 'Asistencia en Carretera',
                'description': 'Soporte técnico las 24 horas',
                'icon': 'fa-tools'
            },
            {
                'name': 'Mantenimiento',
                'description': 'Servicio técnico especializado',
                'icon': 'fa-wrench'
            }
        ]
        
        # Testimonios
        testimonials = [
            {
                'name': 'María González',
                'company': 'Empresa ABC',
                'text': 'Excelente servicio, vehículos en perfecto estado y atención al cliente impecable.',
                'rating': 5
            },
            {
                'name': 'Carlos Rodríguez',
                'company': 'Eventos Plus',
                'text': 'Sunset nos ha ayudado con todos nuestros eventos corporativos. Totalmente recomendable.',
                'rating': 5
            },
            {
                'name': 'Ana Martín',
                'company': 'Particular',
                'text': 'El servicio de chófer es excepcional. Puntualidad y profesionalidad garantizadas.',
                'rating': 5
            }
        ]
        
        return request.render('vehicle_rental.sunset_services_page', {
            'services': services,
            'additional_services': additional_services,
            'testimonials': testimonials
        })
