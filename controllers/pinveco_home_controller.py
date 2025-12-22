# -*- coding: utf-8 -*-
# Copyright 2025 Pinveco
# Controlador para la página principal de Pinveco

from odoo import http
from odoo.http import request


class PinvecoHomeController(http.Controller):
    """Controlador para la página principal de Pinveco"""

    @http.route('/pinveco', type='http', auth='public', website=True)
    def pinveco_home(self, **kw):
        """Página principal de Pinveco"""
        # Obtener la compañía Pinveco
        pinveco_company = request.env['res.company'].sudo().search([('name', '=', 'Pinveco')], limit=1)
        
        # Datos estáticos para evitar errores de modelos
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

    @http.route('/pinveco/flota', type='http', auth='public', website=True)
    def pinveco_fleet(self, **kw):
        """Página de catálogo de flota de Pinveco"""
        try:
            # Obtener la compañía Pinveco
            pinveco_company = request.env['res.company'].sudo().search([('name', '=', 'Pinveco')], limit=1)
            
            # Obtener vehículos de Pinveco solamente
            if pinveco_company:
                vehicles = request.env['fleet.vehicle'].sudo().search([
                    ('company_id', '=', pinveco_company.id)
                ])
            else:
                vehicles = request.env['fleet.vehicle'].sudo().search([])
            
            # Convertir a formato para el template
            vehicle_list = []
            for vehicle in vehicles:
                try:
                    # Crear nombre sin matrícula
                    vehicle_name = vehicle.name or 'Furgoneta'
                    if vehicle.license_plate and vehicle.license_plate in vehicle_name:
                        vehicle_name = vehicle_name.replace(f'/{vehicle.license_plate}', '')
                    
                    vehicle_data = {
                        'id': vehicle.id,
                        'name': vehicle_name,
                        'model': vehicle.model_id.name if vehicle.model_id else 'Modelo',
                        'license_plate': vehicle.license_plate or '',
                        'category': 'Furgoneta',
                        'passengers': 3,
                        'price': 45,
                        'features': ['Aire acondicionado', 'GPS', 'Carga útil'],
                        'icon': 'fa-truck',
                        'color': 'Blanco',
                        'year': '',
                    }
                    
                    # Intentar obtener más datos si están disponibles
                    if hasattr(vehicle, 'category_id') and vehicle.category_id:
                        vehicle_data['category'] = vehicle.category_id.name
                    
                    if hasattr(vehicle, 'seats') and vehicle.seats:
                        vehicle_data['passengers'] = vehicle.seats
                    
                    if hasattr(vehicle, 'color') and vehicle.color:
                        vehicle_data['color'] = vehicle.color
                    
                    if hasattr(vehicle, 'model_year') and vehicle.model_year:
                        vehicle_data['year'] = vehicle.model_year
                    
                    # Todas las furgonetas usan icono de camión
                    vehicle_data['icon'] = 'fa-truck'
                    
                    vehicle_list.append(vehicle_data)
                    
                except Exception as veh_error:
                    continue
            
            # Si no hay vehículos, mostrar lista vacía
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
            
            # Si no hay categorías, usar las por defecto de furgonetas
            if not category_list:
                category_list = [
                    {'id': 1, 'name': 'Furgoneta Pequeña'},
                    {'id': 2, 'name': 'Furgoneta Mediana'},
                    {'id': 3, 'name': 'Furgoneta Grande'},
                    {'id': 4, 'name': 'Furgón Isotermo'},
                    {'id': 5, 'name': 'Furgoneta 9 Plazas'},
                    {'id': 6, 'name': 'Furgón Plataforma'},
                ]
            
        except Exception as e:
            # En caso de error, mostrar lista vacía
            vehicle_list = []
            category_list = []
        
        values = {
            'vehicles': vehicle_list,
            'categories': category_list,
        }
        
        return request.render('vehicle_rental.pinveco_fleet_page', values)

    @http.route('/pinveco/categoria/<int:category_id>', type='http', auth='public', website=True)
    def pinveco_category(self, category_id, **kw):
        """Página de categoría específica para Pinveco"""
        # Obtener la compañía Pinveco
        pinveco_company = request.env['res.company'].sudo().search([('name', '=', 'Pinveco')], limit=1)
        
        category = request.env['fleet.vehicle.model.category'].sudo().browse(category_id)
        
        if not category.exists():
            return request.not_found()
        
        # Obtener vehículos de esta categoría de Pinveco
        domain = [('category_id', '=', category_id)]
        if pinveco_company:
            domain.append(('company_id', '=', pinveco_company.id))
        
        vehicles = request.env['fleet.vehicle'].sudo().search(domain)
        
        values = {
            'category': category,
            'vehicles': vehicles,
        }
        
        return request.render('vehicle_rental.pinveco_category_page', values)

    @http.route('/pinveco/delegacion/<string:city>', type='http', auth='public', website=True)
    def pinveco_delegation(self, city, **kw):
        """Página de delegación específica de Pinveco"""
        delegations = {
            'madrid': {
                'name': 'Delegación Madrid',
                'address': 'C/ Alcalá, 200',
                'city': '28028 Madrid',
                'phone': '+34 913 221 100',
                'email': 'madrid@pinveco.com',
                'hours': 'L-V: 7:00-21:00, S: 8:00-15:00',
                'rating': 4.8,
                'description': 'Nuestra delegación principal en Madrid, especializada en alquiler de furgonetas profesionales.',
            },
            'barcelona': {
                'name': 'Delegación Barcelona',
                'address': 'Av. Diagonal, 500',
                'city': '08006 Barcelona',
                'phone': '+34 933 445 566',
                'email': 'barcelona@pinveco.com',
                'hours': 'L-V: 7:00-21:00, S: 8:00-15:00',
                'rating': 4.9,
                'description': 'Delegación estratégica en Barcelona, con amplia flota de furgonetas para empresas.',
            },
            'valencia': {
                'name': 'Delegación Valencia',
                'address': 'C/ Colón, 85',
                'city': '46004 Valencia',
                'phone': '+34 963 778 899',
                'email': 'valencia@pinveco.com',
                'hours': 'L-V: 7:00-21:00, S: 8:00-15:00',
                'rating': 4.7,
                'description': 'Nuestra delegación en Valencia, perfectamente ubicada para servicios de transporte profesional.',
            }
        }
        
        delegation = delegations.get(city.lower())
        if not delegation:
            return request.not_found()
        
        values = {
            'delegation': delegation,
            'city': city,
        }
        
        return request.render('vehicle_rental.pinveco_delegation_page', values)


