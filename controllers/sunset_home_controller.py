# -*- coding: utf-8 -*-
# Copyright 2025 Sunset Rent a Car
# Controlador para la página principal de Sunset

from odoo import http
from odoo.http import request


class SunsetHomeController(http.Controller):
    """Controlador para la página principal de Sunset"""

    @http.route('/', type='http', auth='public', website=True)
    def sunset_home(self, **kw):
        """Página principal - detecta automáticamente la compañía según el dominio"""
        # Obtener el dominio actual desde el header X-Forwarded-Host (Nginx)
        current_domain = request.httprequest.headers.get('X-Forwarded-Host', request.httprequest.host)
        
        # Si el dominio es pinveco.local, mostrar la página de Pinveco directamente
        if 'pinveco' in current_domain.lower():
            # Obtener la compañía Pinveco
            pinveco_company = request.env['res.company'].sudo().search([('name', '=', 'Pinveco')], limit=1)
            
            # Datos de furgonetas para Pinveco
            vehicle_categories = [
                {'id': 1, 'name': 'Furgoneta Pequeña'},
                {'id': 2, 'name': 'Furgoneta Mediana'},
                {'id': 3, 'name': 'Furgoneta Grande'},
                {'id': 4, 'name': 'Furgón Isotermo'},
                {'id': 5, 'name': 'Furgoneta 9 Plazas'},
                {'id': 6, 'name': 'Furgón Plataforma'},
            ]
            
            values = {
                'vehicle_categories': vehicle_categories,
                'total_vehicles': 30,
                'available_vehicles': 25,
                'total_contracts': 800,
                'company_id': pinveco_company.id if pinveco_company else False,
            }
            
            return request.render('vehicle_rental.pinveco_home_basic', values)
        
        # Datos estáticos para Sunset (dominio por defecto)
        vehicle_categories = [
            {'id': 1, 'name': 'Economy'},
            {'id': 2, 'name': 'Compact'},
            {'id': 3, 'name': 'Standard'},
            {'id': 4, 'name': 'Premium'},
            {'id': 5, 'name': 'SUV'},
            {'id': 6, 'name': 'Furgoneta'},
        ]
        
        values = {
            'vehicle_categories': vehicle_categories,
            'total_vehicles': 50,
            'available_vehicles': 45,
            'total_contracts': 1200,
        }
        
        return request.render('vehicle_rental.sunset_home_basic', values)

    @http.route('/sunset', type='http', auth='public', website=True)
    def sunset_home_alt(self, **kw):
        """URL alternativa para la página principal"""
        return self.sunset_home(**kw)

    @http.route('/sunset/flota', type='http', auth='public', website=True)
    def sunset_fleet(self, **kw):
        """Página de catálogo de flota"""
        try:
            # Obtener vehículos reales de la base de datos
            vehicles = request.env['fleet.vehicle'].sudo().search([])  # Obtener TODOS los vehículos
            # Obtener vehículos reales de la base de datos
            
            # Convertir a formato para el template
            vehicle_list = []
            for vehicle in vehicles:
                try:
                    # Datos básicos del vehículo
                    # Crear nombre sin matrícula
                    vehicle_name = vehicle.name or 'Vehículo'
                    if vehicle.license_plate and vehicle.license_plate in vehicle_name:
                        # Remover la matrícula del nombre
                        vehicle_name = vehicle_name.replace(f'/{vehicle.license_plate}', '')
                    
                    vehicle_data = {
                        'id': vehicle.id,
                        'name': vehicle_name,
                        'model': vehicle.model_id.name if vehicle.model_id else 'Modelo',
                        'license_plate': vehicle.license_plate or '',
                        'category': 'Standard',
                        'passengers': 5,
                        'price': 50,
                        'features': ['Aire acondicionado', 'Bluetooth', 'GPS'],
                        'icon': 'fa-car',
                        'color': 'Blanco',
                        'year': '',
                    }
                    
                    # Intentar obtener más datos si están disponibles
                    # Nota: fleet.vehicle.model no tiene categ_id, usar category_id directamente
                    if hasattr(vehicle, 'category_id') and vehicle.category_id:
                        vehicle_data['category'] = vehicle.category_id.name
                    
                    if hasattr(vehicle, 'seats') and vehicle.seats:
                        vehicle_data['passengers'] = vehicle.seats
                    
                    if hasattr(vehicle, 'color') and vehicle.color:
                        vehicle_data['color'] = vehicle.color
                    
                    if hasattr(vehicle, 'model_year') and vehicle.model_year:
                        vehicle_data['year'] = vehicle.model_year
                    
                    # Determinar icono
                    if vehicle.model_id and vehicle.model_id.name:
                        model_name = vehicle.model_id.name.lower()
                        if any(word in model_name for word in ['furgoneta', 'van', 'transit', 'sprinter', 'daily', 'master', 'crafter']):
                            vehicle_data['icon'] = 'fa-truck'
                    
                    vehicle_list.append(vehicle_data)
                    
                except Exception as veh_error:
                    # Continuar con el siguiente vehículo
                    continue
            
            # Si no hay vehículos, mostrar mensaje
            if not vehicle_list:
                vehicle_list = []
            
            # Obtener categorías reales
            categories = request.env['fleet.vehicle.model.category'].sudo().search([])
            category_list = []
            for category in categories:
                category_list.append({
                    'id': category.id,
                    'name': category.name
                })
            
            # Si no hay categorías, usar las por defecto
            if not category_list:
                category_list = [
                    {'id': 1, 'name': 'Economy'},
                    {'id': 2, 'name': 'Compact'},
                    {'id': 3, 'name': 'Standard'},
                    {'id': 4, 'name': 'Premium'},
                    {'id': 5, 'name': 'SUV'},
                    {'id': 6, 'name': 'Furgoneta'},
                ]
            
        except Exception as e:
            # En caso de error, mostrar lista vacía
            vehicle_list = []
            category_list = []
        
        values = {
            'vehicles': vehicle_list,
            'categories': category_list,
        }
        
        return request.render('vehicle_rental.sunset_fleet_page', values)

    @http.route('/test/flota', type='http', auth='public', website=True)
    def test_fleet(self, **kw):
        """Página de prueba para verificar vehículos"""
        try:
            # Obtener vehículos reales de la base de datos
            vehicles = request.env['fleet.vehicle'].sudo().search([])
            
            # Convertir a formato para el template
            vehicle_list = []
            for vehicle in vehicles:
                vehicle_data = {
                    'id': vehicle.id,
                    'name': vehicle.name or 'Vehículo',
                    'model': vehicle.model_id.name if vehicle.model_id else 'Modelo',
                    'license_plate': vehicle.license_plate or '',
                    'category': vehicle.model_id.categ_id.name if vehicle.model_id and vehicle.model_id.categ_id else 'Standard',
                    'passengers': vehicle.seats if hasattr(vehicle, 'seats') and vehicle.seats else 5,
                    'price': 50,
                    'features': ['Aire acondicionado', 'Bluetooth', 'GPS'],
                    'icon': 'fa-car',
                    'color': vehicle.color if hasattr(vehicle, 'color') and vehicle.color else 'Blanco',
                    'year': vehicle.model_year if hasattr(vehicle, 'model_year') and vehicle.model_year else '',
                }
                vehicle_list.append(vehicle_data)
            
            values = {
                'vehicles': vehicle_list,
            }
            
            return request.render('vehicle_rental.test_fleet_page', values)
            
        except Exception as e:
            return f"<h1>Error: {str(e)}</h1>"

    @http.route('/simple/flota', type='http', auth='public', website=True)
    def simple_fleet(self, **kw):
        """Página simple para verificar vehículos"""
        try:
            # Obtener vehículos reales de la base de datos
            vehicles = request.env['fleet.vehicle'].sudo().search([])
            
            # Convertir a formato para el template
            vehicle_list = []
            for vehicle in vehicles:
                vehicle_data = {
                    'id': vehicle.id,
                    'name': vehicle.name or 'Vehículo',
                    'model': vehicle.model_id.name if vehicle.model_id else 'Modelo',
                    'license_plate': vehicle.license_plate or '',
                    'category': vehicle.model_id.categ_id.name if vehicle.model_id and vehicle.model_id.categ_id else 'Standard',
                    'passengers': vehicle.seats if hasattr(vehicle, 'seats') and vehicle.seats else 5,
                    'price': 50,
                    'features': ['Aire acondicionado', 'Bluetooth', 'GPS'],
                    'icon': 'fa-car',
                    'color': vehicle.color if hasattr(vehicle, 'color') and vehicle.color else 'Blanco',
                    'year': vehicle.model_year if hasattr(vehicle, 'model_year') and vehicle.model_year else '',
                }
                vehicle_list.append(vehicle_data)
            
            values = {
                'vehicles': vehicle_list,
            }
            
            return request.render('vehicle_rental.simple_fleet_page', values)
            
        except Exception as e:
            return f"<h1>Error: {str(e)}</h1>"

    @http.route('/sunset/categoria/<int:category_id>', type='http', auth='public', website=True)
    def sunset_category(self, category_id, **kw):
        """Página de categoría específica"""
        category = request.env['fleet.vehicle.model.category'].sudo().browse(category_id)
        
        if not category.exists():
            return request.not_found()
        
        # Obtener vehículos de esta categoría
        vehicles = request.env['fleet.vehicle'].sudo().search([
            ('category_id', '=', category_id),
            ('status', '=', 'available')
        ])
        
        values = {
            'category': category,
            'vehicles': vehicles,
        }
        
        return request.render('vehicle_rental.sunset_category_page', values)

    @http.route('/sunset/delegacion/<string:city>', type='http', auth='public', website=True)
    def sunset_delegation(self, city, **kw):
        """Página de delegación específica"""
        # Datos de delegaciones (podrían venir de un modelo en el futuro)
        delegations = {
            'cordoba': {
                'name': 'Delegación Córdoba',
                'address': 'Av. de la Libertad, 123',
                'city': '14005 Córdoba',
                'phone': '+34 957 322 664',
                'email': 'cordoba@sunsetrentacar.com',
                'hours': 'L-V: 8:00-20:00, S: 9:00-14:00',
                'rating': 4.8,
                'description': 'Nuestra delegación principal en Córdoba, ubicada en el corazón de la ciudad.',
            },
            'malaga': {
                'name': 'Delegación Málaga',
                'address': 'C/ Larios, 45',
                'city': '29001 Málaga',
                'phone': '+34 951 234 567',
                'email': 'malaga@sunsetrentacar.com',
                'hours': 'L-V: 8:00-20:00, S: 9:00-14:00',
                'rating': 4.9,
                'description': 'Delegación estratégica en Málaga, cerca del centro histórico y la costa.',
            },
            'sevilla': {
                'name': 'Delegación Sevilla',
                'address': 'Paseo de la Delicias, 78',
                'city': '41012 Sevilla',
                'phone': '+34 954 567 890',
                'email': 'sevilla@sunsetrentacar.com',
                'hours': 'L-V: 8:00-20:00, S: 9:00-14:00',
                'rating': 4.7,
                'description': 'Nuestra delegación en Sevilla, perfectamente ubicada para acceder a toda Andalucía.',
            }
        }
        
        delegation = delegations.get(city.lower())
        if not delegation:
            return request.not_found()
        
        values = {
            'delegation': delegation,
            'city': city,
        }
        
        return request.render('vehicle_rental.sunset_delegation_page', values)

    @http.route('/sunset/servicios/<string:service>', type='http', auth='public', website=True)
    def sunset_service(self, service, **kw):
        """Página de servicio específico"""
        services = {
            'carga': {
                'name': 'Furgonetas de Carga',
                'title': 'Soluciones de Transporte de Carga',
                'description': 'Nuestra flota de furgonetas de carga está diseñada para satisfacer todas tus necesidades de transporte de mercancías.',
                'features': [
                    'Amplia gama de tamaños y capacidades',
                    'Vehículos modernos y bien mantenidos',
                    'Seguro incluido en todos los alquileres',
                    'Asistencia 24/7 en toda España',
                    'Precios competitivos y transparentes'
                ],
                'vehicles': ['Tipo A', 'Tipo B', 'Tipo C', 'Tipo D']
            },
            'pasajeros': {
                'name': 'Furgonetas de Pasajeros',
                'title': 'Transporte de Grupos y Excursiones',
                'description': 'Perfectas para grupos, excursiones y transporte de pasajeros. Confort y seguridad garantizados.',
                'features': [
                    'Hasta 9 plazas disponibles',
                    'Confort y seguridad premium',
                    'Aire acondicionado en todos los vehículos',
                    'Conductores profesionales disponibles',
                    'Rutas personalizadas'
                ],
                'vehicles': ['Tipo E', 'Tipo F', 'Tipo G', 'Tipo H']
            },
            'comerciales': {
                'name': 'Vehículos Comerciales',
                'title': 'Soluciones Empresariales',
                'description': 'Servicios especializados para empresas con necesidades de transporte comercial.',
                'features': [
                    'Flota moderna y eficiente',
                    'Mantenimiento incluido',
                    'Contratos flexibles',
                    'Soporte técnico especializado',
                    'Facturación empresarial'
                ],
                'vehicles': ['Tipo I', 'Tipo J', 'Tipo K', 'Tipo L']
            }
        }
        
        service_data = services.get(service.lower())
        if not service_data:
            return request.not_found()
        
        values = {
            'service': service_data,
            'service_key': service,
        }
        
        return request.render('vehicle_rental.sunset_service_page', values)

    @http.route('/sunset/seguros', type='http', auth='public', website=True)
    def sunset_insurance(self, **kw):
        """Página de seguros"""
        values = {
            'insurance_types': [
                {
                    'name': 'Seguro Básico',
                    'description': 'Cobertura esencial incluida en todos nuestros alquileres',
                    'features': ['Responsabilidad civil', 'Defensa jurídica', 'Asistencia en carretera'],
                    'price': 'Incluido'
                },
                {
                    'name': 'Seguro Completo',
                    'description': 'Cobertura ampliada para mayor tranquilidad',
                    'features': ['Todo lo del básico', 'Robo y hurto', 'Daños propios', 'Cristales'],
                    'price': '€15/día'
                },
                {
                    'name': 'Seguro Premium',
                    'description': 'Cobertura total sin franquicia',
                    'features': ['Todo lo del completo', 'Sin franquicia', 'Vehículo de sustitución', 'Asistencia 24/7'],
                    'price': '€25/día'
                }
            ]
        }
        
        return request.render('vehicle_rental.sunset_insurance_page', values)
