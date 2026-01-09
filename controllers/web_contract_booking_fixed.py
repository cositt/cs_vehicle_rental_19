# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import re


class WebsiteContractBookingFixed(http.Controller):

    def _get_image_path(self, tipo):
        """Retorna la ruta correcta de imagen según la compañía (Sunset vs Pinveco)"""
        current_domain = request.httprequest.headers.get('X-Forwarded-Host', request.httprequest.host)
        is_pinveco = 'pinveco' in current_domain.lower()

        # Determinar carpeta según compañía
        img_folder = 'tipos_pinveco' if is_pinveco else 'tipos'
        return f'/vehicle_rental/static/description/img/{img_folder}/{tipo}.png'

    def _get_initial_values(self):
        """Get initial values for the booking enquiry"""
        # Obtener categorías de vehículos disponibles (excluyendo las eliminadas desde UI)
        # Filtrar categorías que no queremos mostrar en la web
        excluded_categories = [
            'Tipo E - Bici Eléctrica',
            'Furgoneta',
            'Tipo E',
            'Bici Eléctrica'
        ]

        categories = request.env['fleet.vehicle.model.category'].sudo().search([
            ('name', 'not in', excluded_categories)
        ], order='name')

        print(f"DEBUG: Booking enquiry categories: {[(c.id, c.name) for c in categories]}")

        return {
            'vehicle_categories': categories,
        }

    def _get_vehicle_detail_info(self, category):
        """Get detailed vehicle information based on category"""
        # Mapeo por ID en lugar de por nombre para evitar problemas de cache
        vehicle_data_by_id = {
            37: {  # Tipo A - Combi 5 plazas
                'name': 'Furgoneta Combi Tipo A',
                'description': 'Compacta, ligera y de bajo consumo. El tipo A, engloba furgonetas muy urbanas, perfectas para moverse por el tráfico de la ciudad y para lidiar con el aparcamiento. Sus 5 plazas más el pequeño espacio de carga, la hacen perfectas para empresas de reparaciones o mantenimiento, o para el desplazamiento del personal.',
                'seats': 5,
                'volume': 'Pequeño',
                'ac': True,
                'image': self._get_image_path('tipoA'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 48, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 75, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 95, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            38: {  # Tipo B - Combi 7 plazas
                'name': 'Furgoneta Combi Tipo B',
                'description': 'Furgonetas medianas ideales para el transporte urbano. Perfectas para equipos de trabajo, servicios de reparto o desplazamientos de personal. Su capacidad de 7 plazas las hace ideales para grupos pequeños.',
                'seats': 7,
                'volume': 'Mediano',
                'ac': True,
                'image': self._get_image_path('tipoB'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 55, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 110, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            39: {  # Tipo D - Furgón 3 plazas
                'name': 'Furgón Tipo D',
                'description': 'Furgones de gran capacidad para el transporte de mercancías pesadas. Ideales para mudanzas y transporte industrial.',
                'seats': 3,
                'volume': 'Grande',
                'ac': True,
                'image': self._get_image_path('tipoD'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 70, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 100, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 130, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            40: {  # Tipo E - Furgón 2 plazas
                'name': 'Furgón Tipo E',
                'description': 'Furgones extra grandes para el transporte de mercancías voluminosas. Perfectos para mudanzas y transporte de equipos industriales.',
                'seats': 2,
                'volume': 'Extra Grande',
                'ac': True,
                'image': self._get_image_path('tipoE'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 80, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 110, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 140, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            41: {  # Tipo F - Furgón 2 plazas
                'name': 'Furgón Tipo F',
                'description': 'Furgones especiales para servicios profesionales. Ideales para equipos de mantenimiento y servicios técnicos.',
                'seats': 2,
                'volume': 'Grande',
                'ac': True,
                'image': self._get_image_path('tipoF'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 75, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 105, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 135, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            42: {  # Tipo K - Furgón 2 plazas
                'name': 'Furgón Tipo K',
                'description': 'Furgones de lujo para eventos especiales. Perfectos para catering, eventos corporativos y servicios premium.',
                'seats': 2,
                'volume': 'Mediano',
                'ac': True,
                'image': self._get_image_path('tipoK'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 90, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 120, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 150, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            }
        }

        # Mapeo de categorías a información de Pinveco (por nombre como fallback)
        vehicle_data = {
            'Tipo A - Combi 5 plazas': {
                'name': 'Furgoneta Combi Tipo A',
                'description': 'Compacta, ligera y de bajo consumo. El tipo A, engloba furgonetas muy urbanas, perfectas para moverse por el tráfico de la ciudad y para lidiar con el aparcamiento. Sus 5 plazas más el pequeño espacio de carga, la hacen perfectas para empresas de reparaciones o mantenimiento, o para el desplazamiento del personal.',
                'seats': 5,
                'volume': 'Pequeño',
                'ac': True,
                'image': self._get_image_path('tipoA'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 48, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 75, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 95, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo B - Combi 7 plazas': {
                'name': 'Furgoneta Combi Tipo B',
                'description': 'Furgonetas medianas ideales para el transporte urbano. Perfectas para equipos de trabajo, servicios de reparto o desplazamientos de personal. Su capacidad de 7 plazas las hace ideales para grupos pequeños.',
                'seats': 7,
                'volume': 'Mediano',
                'ac': True,
                'image': self._get_image_path('tipoB'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 55, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 110, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo C - Furgón 3 plazas': {
                'name': 'Furgón Tipo C',
                'description': 'Furgones compactos ideales para el transporte de mercancías ligeras. Perfectos para servicios de reparto urbano y transporte de equipos.',
                'seats': 3,
                'volume': 'Mediano',
                'ac': True,
                'image': self._get_image_path('tipoC'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 60, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 90, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 120, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo D - Furgón 3 plazas': {
                'name': 'Furgón Tipo D',
                'description': 'Furgones de gran capacidad para el transporte de mercancías pesadas. Ideales para mudanzas y transporte industrial.',
                'seats': 3,
                'volume': 'Grande',
                'ac': True,
                'image': self._get_image_path('tipoD'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 70, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 100, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 130, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo E - Furgón 2 plazas': {
                'name': 'Furgón Tipo E',
                'description': 'Furgones extra grandes para el transporte de mercancías voluminosas. Perfectos para mudanzas y transporte de equipos industriales.',
                'seats': 2,
                'volume': 'Extra Grande',
                'ac': True,
                'image': self._get_image_path('tipoE'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 80, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 110, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 140, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo F - Furgón 2 plazas': {
                'name': 'Furgón Tipo F',
                'description': 'Furgones especiales para servicios profesionales. Ideales para equipos de mantenimiento y servicios técnicos.',
                'seats': 2,
                'volume': 'Grande',
                'ac': True,
                'image': self._get_image_path('tipoF'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 75, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 105, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 135, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo K - Furgón 2 plazas': {
                'name': 'Furgón Tipo K',
                'description': 'Furgones de lujo para eventos especiales. Perfectos para catering, eventos corporativos y servicios premium.',
                'seats': 2,
                'volume': 'Mediano',
                'ac': True,
                'image': self._get_image_path('tipoK'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 90, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 120, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 150, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo T - Furgón 2 plazas': {
                'name': 'Furgón Tipo T',
                'description': 'Furgones de gran capacidad para transporte pesado. Ideales para construcción y transporte industrial.',
                'seats': 2,
                'volume': 'Extra Grande',
                'ac': True,
                'image': self._get_image_path('tipoT'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 85, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 115, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 145, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo V - Furgón 2 plazas': {
                'name': 'Furgón Tipo V',
                'description': 'Furgones de máxima capacidad para transporte industrial. Perfectos para grandes mudanzas y transporte de maquinaria.',
                'seats': 2,
                'volume': 'Máximo',
                'ac': True,
                'image': self._get_image_path('tipoV'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 95, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 125, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 155, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo W - Furgón 2 plazas': {
                'name': 'Furgón Tipo W',
                'description': 'Furgones especializados para servicios técnicos. Ideales para equipos de mantenimiento y reparación.',
                'seats': 2,
                'volume': 'Mediano',
                'ac': True,
                'image': self._get_image_path('tipoW'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 70, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 100, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 130, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo X - Furgón 2 plazas': {
                'name': 'Furgón Tipo X',
                'description': 'Furgones de alta gama para servicios premium. Perfectos para eventos especiales y servicios corporativos.',
                'seats': 2,
                'volume': 'Grande',
                'ac': True,
                'image': self._get_image_path('tipoX'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 100, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 130, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                    {'duration': '24h', 'km': '500km', 'price': 160, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                ]
            },
            'Tipo Z - Patinete Eléctrico': {
                'name': 'Patinete Eléctrico Tipo Z',
                'description': 'Patinetes eléctricos para movilidad urbana sostenible. Perfectos para desplazamientos cortos y ecológicos.',
                'seats': 1,
                'volume': 'Mínimo',
                'ac': False,
                'image': self._get_image_path('tipoZ'),
                'pricing': [
                    {'duration': '2h', 'km': '20km', 'price': 15, 'features': ['20km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico']},
                    {'duration': '4h', 'km': '40km', 'price': 25, 'features': ['40km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico'], 'popular': True},
                    {'duration': '8h', 'km': '80km', 'price': 40, 'features': ['80km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico']}
                ]
            }
        }
        # Intentar primero por ID
        if category.id in vehicle_data_by_id:
            print(f"DEBUG: Found by ID {category.id}")
            result = vehicle_data_by_id[category.id]
        else:
            # Fallback por nombre
            category_name = category.name
            print(f"DEBUG: Looking for category_name: '{category_name}'")
            print(f"DEBUG: Available keys: {list(vehicle_data.keys())}")
            result = vehicle_data.get(category_name, {
                'name': category_name,
                'description': 'Descubre las ventajas de esta categoría de vehículo.',
                'seats': 3,
                'volume': 'Variable',
                'ac': True,
                'image': self._get_image_path('default'),
                'pricing': [
                    {'duration': '4h', 'km': '100km', 'price': 50, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    {'duration': '24h', 'km': '350km', 'price': 80, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True}
                ]
            })

        print(f"DEBUG: Returning result: {result.get('name', 'N/A')}")
        return result

    def _get_fixed_pricing_offers(self, category_id, default_pricing=None):
        """Obtiene las ofertas fijas desde la BD, o usa las hardcodeadas si no hay"""
        try:
            from odoo import fields
            # Buscar tarifas estándar activas para esta categoría
            pricing_rules = request.env['vehicle.pricing.rule'].sudo().search([
                ('vehicle_category_id', '=', category_id),
                ('pricing_type', '=', 'standard'),
                ('active', '=', True),
                ('valid_from', '<=', fields.Date.today()),
                '|', ('valid_until', '=', False), ('valid_until', '>=', fields.Date.today())
            ], order='km_range, duration_range')

            if pricing_rules:
                # Buscar directamente las 3 tarifas prioritarias en este orden:
                # 1. 4h/100km
                # 2. 1-2d/350km (mostrar como 24h/350km)
                # 3. 1-2d/500km (mostrar como 24h/500km)
                priority_offers = []

                # Buscar 4h/100km
                rule_4h_100 = pricing_rules.filtered(
                    lambda r: r.duration_range == '4h' and r.km_range == '100'
                )
                if rule_4h_100:
                    rule = rule_4h_100[0]
                    priority_offers.append({
                        'duration': '4h',
                        'km': '100km',
                        'price': float(rule.price_per_unit),
                        'features': [
                            '100km autonomía (ampliable a 150km)',
                            'Recogida y entrega en horario laboral',
                            'Seguro obligatorio'
                        ],
                        'popular': False
                    })

                # Buscar 1-2d/350km
                rule_1_2d_350 = pricing_rules.filtered(
                    lambda r: r.duration_range == '1-2d' and r.km_range == '350'
                )
                if rule_1_2d_350:
                    rule = rule_1_2d_350[0]
                    priority_offers.append({
                        'duration': '24h',
                        'km': '350km',
                        'price': float(rule.price_per_unit),
                        'features': [
                            '350km autonomía',
                            'Recogida y entrega en horario laboral',
                            'Seguro obligatorio'
                        ],
                        'popular': True
                    })

                # Buscar 1-2d/500km
                rule_1_2d_500 = pricing_rules.filtered(
                    lambda r: r.duration_range == '1-2d' and r.km_range == '500'
                )
                if rule_1_2d_500:
                    rule = rule_1_2d_500[0]
                    priority_offers.append({
                        'duration': '24h',
                        'km': '500km',
                        'price': float(rule.price_per_unit),
                        'features': [
                            '500km autonomía',
                            'Recogida y entrega en horario laboral',
                            'Seguro obligatorio'
                        ],
                        'popular': False
                    })

                # Si encontramos las 3 prioritarias, devolverlas
                if len(priority_offers) >= 3:
                    print(f"DEBUG: Found {len(priority_offers)} priority offers from database")
                    return priority_offers[:3]
                elif priority_offers:
                    print(f"DEBUG: Found {len(priority_offers)} priority offers (less than 3)")
                    return priority_offers

            # Si no hay tarifas en BD, usar las hardcodeadas
            return default_pricing if default_pricing else []

        except Exception as e:
            print(f"DEBUG: Error getting fixed pricing offers: {e}")
            import traceback
            traceback.print_exc()
            # En caso de error, usar las hardcodeadas
            return default_pricing if default_pricing else []

    def _get_dynamic_pricing_rules(self, category_id):
        """Obtiene las tarifas dinámicas del módulo para una categoría"""
        try:
            from odoo import fields
            # Buscar tarifas activas para esta categoría en la base de datos
            pricing_rules = request.env['vehicle.pricing.rule'].sudo().search([
                ('vehicle_category_id', '=', category_id),
                ('active', '=', True),
                ('valid_from', '<=', fields.Date.today()),
                '|', ('valid_until', '=', False), ('valid_until', '>=', fields.Date.today())
            ], order='pricing_type, price_per_unit')

            # Convertir a formato compatible con la vista
            dynamic_pricing = []
            for rule in pricing_rules:
                if rule.pricing_type == 'standard':
                    # Tarifa estándar - usar los valores directos de la base de datos
                    km_label = rule.km_range if rule.km_range != 'unlimited' else 'Sin límite'
                    duration_label = rule.duration_range

                    dynamic_pricing.append({
                        'type': 'standard',
                        'duration': duration_label,
                        'km': km_label,
                        'price': rule.price_per_unit,
                        'features': [
                            f'{km_label} autonomía',
                            'Recogida y entrega en horario laboral',
                            'Seguro obligatorio'
                        ],
                        'rule_id': rule.id
                    })
                elif rule.pricing_type == 'flexirent':
                    # Tarifa FLEXIRENT
                    dynamic_pricing.append({
                        'type': 'flexirent',
                        'duration': f'{rule.flexirent_duration_days} días',
                        'km': f'{rule.flexirent_km_total}km',
                        'price': rule.price_per_unit,
                        'features': [
                            f'{rule.flexirent_km_total}km autonomía total',
                            'Paquete de larga temporada',
                            'Recogida y entrega en horario laboral',
                            'Seguro obligatorio'
                        ],
                        'rule_id': rule.id,
                        'popular': True  # FLEXIRENT siempre es popular
                    })

            # Si no hay tarifas en la base de datos, usar datos de prueba
            if not dynamic_pricing:
                test_pricing_data = {
                    27: [  # Tipo A - Combi 5 plazas
                        {
                            'type': 'standard',
                            'duration': '4h (mañana o tarde)',
                            'km': '100 Km',
                            'price': 48.00,
                            'features': [
                                '100km autonomía',
                                'Recogida y entrega en horario laboral',
                                'Seguro obligatorio'
                            ],
                            'rule_id': 'test_1'
                        },
                        {
                            'type': 'standard',
                            'duration': '1-2 días',
                            'km': '350 Km',
                            'price': 75.00,
                            'features': [
                                '350km autonomía',
                                'Recogida y entrega en horario laboral',
                                'Seguro obligatorio'
                            ],
                            'rule_id': 'test_2'
                        },
                        {
                            'type': 'flexirent',
                            'duration': '30 días',
                            'km': '4500km',
                            'price': 695.00,
                            'features': [
                                '4500km autonomía total',
                                'Paquete de larga temporada',
                                'Recogida y entrega en horario laboral',
                                'Seguro obligatorio'
                            ],
                            'rule_id': 'test_flex_1',
                            'popular': True
                        }
                    ]
                }
                dynamic_pricing = test_pricing_data.get(category_id, [])

            return dynamic_pricing

        except Exception as e:
            print(f"DEBUG: Error getting dynamic pricing rules: {e}")
            return []

    def _render_dynamic_pricing_cards(self, pricing_rules):
        """Renderiza las tarjetas de tarifas dinámicas"""
        if not pricing_rules:
            return '<div class="col-12"><div class="alert alert-info text-center"><i class="fa fa-info-circle me-2"></i>No hay tarifas dinámicas configuradas para esta categoría de vehículo.</div></div>'

        cards_html = []
        for rule in pricing_rules:
            popular_badge = '<div class="badge mb-2" style="background-color: {primary_color}; color: white;">Más Popular</div>' if rule.get('popular') else ''
            border_style = 'border-color: {primary_color} !important; border-width: 2px !important;' if rule.get('popular') else ''
            border_class = 'border-warning' if rule.get('popular') else ''

            features_html = ''.join([f'<li class="mb-1"><i class="fa fa-check text-success me-2"></i>{feature}</li>' for feature in rule.get('features', [])])

            card_html = f'''
            <div class="col-lg-4 col-md-6 mb-4">
                <div class="card h-100 {border_class}" style="{border_style}">
                    <div class="card-body text-center">
                        {popular_badge}
                        <h4 class="card-title">{rule.get('duration', '')}</h4>
                        <div class="mb-3">
                            <span class="h3" style="color: {primary_color};">€{rule.get('price', 0)}</span>
                        </div>
                        <p class="text-muted mb-3">{rule.get('km', '')}</p>
                        <ul class="list-unstyled">
                            {features_html}
                        </ul>
                        <div class="mt-3">
                            <small class="text-muted">
                                <i class="fa fa-calculator me-1"></i>
                                {rule.get('type', '').title()} - ID: {rule.get('rule_id', '')}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
            '''
            cards_html.append(card_html)

        return ''.join(cards_html)

    @http.route('/web/vehicle-detail/<int:category_id>', auth='public', website=True, type='http')
    def vehicle_detail(self, category_id, **kw):
        """Vehicle Detail View"""
        try:
            # Detectar el dominio actual para colores corporativos
            current_domain = request.httprequest.headers.get('X-Forwarded-Host', request.httprequest.host)
            is_pinveco = 'pinveco' in current_domain.lower()
            if is_pinveco:
                primary_color = '#0066B3'
                secondary_color = '#003D7A'
                company_id = 2  # Pinveco
            else:
                primary_color = '#FF8C00'
                secondary_color = '#FFA500'
                company_id = 1  # Sunset

            # Obtener ubicaciones disponibles según la compañía
            available_locations = []
            if company_id:
                vehicles = request.env['fleet.vehicle'].sudo().search([('company_id', '=', company_id)])
                locations_set = set()
                for vehicle in vehicles:
                    if hasattr(vehicle, 'location') and vehicle.location:
                        # Normalizar ubicaciones (Málaga/Malaga, Córdoba/Cordoba)
                        loc = vehicle.location.strip()
                        if loc:
                            locations_set.add(loc)
                available_locations = sorted(list(locations_set))

            # Si no hay ubicaciones específicas, usar "Todas" como opción por defecto
            if not available_locations:
                available_locations = ['Todas las ubicaciones']

            # Primero intentar obtener la categoría de la BD
            category = request.env['fleet.vehicle.model.category'].sudo().browse(category_id)
            if not category.exists():
                return f"<h1>Error: No category found with ID {category_id}</h1>"

            print(f"DEBUG: Category found - ID: {category_id}, Name: {category.name}")
            print(f"DEBUG: Available locations for company {company_id}: {available_locations}")

            # Mapeo por nombre de categoría para independencia de IDs entre desarrollo y producción
            vehicle_data_by_name = {
                'Tipo A': {
                    'name': 'Furgoneta Combi Tipo A',
                    'description': 'Compacta, ligera y de bajo consumo. El tipo A, engloba furgonetas muy urbanas, perfectas para moverse por el tráfico de la ciudad y para lidiar con el aparcamiento. Sus 5 plazas más el pequeño espacio de carga, la hacen perfectas para empresas de reparaciones o mantenimiento, o para el desplazamiento del personal.',
                    'seats': 5,
                    'volume': 'Pequeño',
                    'ac': True,
                    'image': self._get_image_path('tipoA'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 48, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 75, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 95, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo B': {
                    'name': 'Furgoneta Combi Tipo B',
                    'description': 'Furgonetas medianas ideales para el transporte urbano. Perfectas para equipos de trabajo, servicios de reparto o desplazamientos de personal. Su capacidad de 7 plazas las hace ideales para grupos pequeños.',
                    'seats': 7,
                    'volume': 'Mediano',
                    'ac': True,
                    'image': self._get_image_path('tipoB'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 55, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 110, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo C': {
                    'name': 'Furgoneta Tipo C (3m³)',
                    'description': 'Furgoneta compacta de 3 metros cúbicos. Perfecta para transportes urbanos y repartos locales. Ideal para empresas de servicios y mantenimiento.',
                    'seats': 3,
                    'volume': '3 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoC'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 48, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 75, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 95, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo D': {
                    'name': 'Furgoneta Tipo D (8m³)',
                    'description': 'Furgoneta de 8 metros cúbicos con mayor capacidad de carga. Ideal para trasportes comerciales medianos.',
                    'seats': 3,
                    'volume': '8 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoD'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 58, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 105, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo F': {
                    'name': 'Furgoneta Tipo F (6m³)',
                    'description': 'Furgoneta de 6 metros cúbicos con capacidad media. Buena relación tamaño-carga para transportes urbanos.',
                    'seats': 3,
                    'volume': '6-7 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoF'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 53, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 80, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 100, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo K': {
                    'name': 'Furgoneta Tipo K (15m³)',
                    'description': 'Furgoneta de 15 metros cúbicos con alta capacidad de carga. Perfecta para mudanzas grandes.',
                    'seats': 3,
                    'volume': '15 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoK'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 83, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 120, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 140, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo T': {
                    'name': 'Furgoneta Tipo T (Caja Abierta)',
                    'description': 'Furgoneta con caja abierta ideal para transporte de materiales voluminosos. Facilita carga y descarga.',
                    'seats': 3,
                    'volume': 'Caja abierta',
                    'ac': True,
                    'image': self._get_image_path('tipoT'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 86, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 125, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 145, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo V': {
                    'name': 'Furgoneta Tipo V (11m³)',
                    'description': 'Furgoneta de 11 metros cúbicos con capacidad considerable. Ideal para transportes de mayor volumen.',
                    'seats': 3,
                    'volume': '11 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoV'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 66, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 95, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 115, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo W': {
                    'name': 'Furgoneta Tipo W (13m³)',
                    'description': 'Furgoneta de 13 metros cúbicos con gran capacidad de carga. Ideal para mudanzas y transportes grandes.',
                    'seats': 3,
                    'volume': '13 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoW'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 66, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 95, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 115, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo X': {
                    'name': 'Furgoneta Tipo X (22m³)',
                    'description': 'Furgoneta de gran capacidad con 22 metros cúbicos. Máxima capacidad de carga, perfecta para grandes mudanzas y transportes.',
                    'seats': 3,
                    'volume': '22 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoX'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 86, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 135, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 155, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                    ]
                },
                'Tipo Z': {
                    'name': 'Patinete Eléctrico Tipo Z',
                    'description': 'Patinetes eléctricos para movilidad urbana sostenible. Perfectos para desplazamientos cortos y ecológicos.',
                    'seats': 1,
                    'volume': 'Mínimo',
                    'ac': False,
                    'image': self._get_image_path('tipoZ'),
                    'pricing': [
                        {'duration': '2h', 'km': '20km', 'price': 15, 'features': ['20km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico']},
                        {'duration': '4h', 'km': '40km', 'price': 25, 'features': ['40km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico'], 'popular': True},
                        {'duration': '8h', 'km': '80km', 'price': 40, 'features': ['80km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico']},
                    ]
                },
            }

            # Extraer el "tipo" del nombre de la categoría (e.g., "Tipo B - Furgoneta 22m³ plataforma" -> "Tipo B")
            tipo_match = re.match(r'^(Tipo [A-Z])', category.name, re.IGNORECASE)
            vehicle_info = None

            if tipo_match:
                tipo = tipo_match.group(1)
                vehicle_info = vehicle_data_by_name.get(tipo)
                print(f"DEBUG: Mapped {category.name} to {tipo}, found: {vehicle_info is not None}")

            # Fallback: usar mapeo directo por ID para compatibilidad con otros IDs
            if not vehicle_info:
                # Mantener el diccionario antiguo como fallback
                vehicle_data_by_id = {
                2: {  # Tipo X - Furgoneta 22m³
                    'name': 'Furgoneta Tipo X (22m³)',
                    'description': 'Furgoneta de gran capacidad con 22 metros cúbicos. Máxima capacidad de carga, perfecta para grandes mudanzas y transportes.',
                    'seats': 3,
                    'volume': '22 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoX'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 86, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 135, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 155, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                27: {  # Categoría ID 27 - Tipo A
                    'name': 'Furgoneta Combi Tipo A',
                    'description': 'Compacta, ligera y de bajo consumo. El tipo A, engloba furgonetas muy urbanas, perfectas para moverse por el tráfico de la ciudad y para lidiar con el aparcamiento. Sus 5 plazas más el pequeño espacio de carga, la hacen perfectas para empresas de reparaciones o mantenimiento, o para el desplazamiento del personal.',
                    'seats': 5,
                    'volume': 'Pequeño',
                    'ac': True,
                    'image': self._get_image_path('tipoA'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 48, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 75, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 95, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                28: {  # Tipo B - Combi 7 plazas
                    'name': 'Furgoneta Combi Tipo B',
                    'description': 'Furgonetas medianas ideales para el transporte urbano. Perfectas para equipos de trabajo, servicios de reparto o desplazamientos de personal. Su capacidad de 7 plazas las hace ideales para grupos pequeños.',
                    'seats': 7,
                    'volume': 'Mediano',
                    'ac': True,
                    'image': self._get_image_path('tipoB'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 55, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 110, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                29: {  # Tipo D - Furgoneta 8m³
                    'name': 'Furgoneta Tipo D (8m³)',
                    'description': 'Furgoneta de 8 metros cúbicos con mayor capacidad de carga. Ideal para trasportes comerciales medianos.',
                    'seats': 3,
                    'volume': '8 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoD'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 58, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 105, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                38: {  # Tipo C - Furgoneta 3m³
                    'name': 'Furgoneta Tipo C (3m³)',
                    'description': 'Furgoneta compacta de 3 metros cúbicos. Perfecta para transportes urbanos y repartos locales. Ideal para empresas de servicios y mantenimiento.',
                    'seats': 3,
                    'volume': '3 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoC'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 48, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 75, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 95, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                30: {  # Tipo E - Furgoneta Botellero
                    'name': 'Furgoneta Tipo E (Botellero)',
                    'description': 'Furgoneta especializada para transporte de bebidas con sistema de separadores y lona. Ideal para distribución de bebidas.',
                    'seats': 3,
                    'volume': 'Especial para botellas',
                    'ac': True,
                    'image': self._get_image_path('tipoE'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 90, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 130, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 150, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                31: {  # Tipo F - Furgoneta 6m³
                    'name': 'Furgoneta Tipo F (6m³)',
                    'description': 'Furgoneta de 6 metros cúbicos con capacidad media. Buena relación tamaño-carga para transportes urbanos.',
                    'seats': 3,
                    'volume': '6-7 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoF'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 53, 'features': ['100km autonomía (ampliable a 150km)', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 80, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 100, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                32: {  # Tipo K - Furgoneta 15m³
                    'name': 'Furgoneta Tipo K (15m³)',
                    'description': 'Furgoneta de 15 metros cúbicos con alta capacidad de carga. Perfecta para mudanzas grandes.',
                    'seats': 3,
                    'volume': '15 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoK'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 83, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 120, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 140, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                33: {  # Tipo T - Furgoneta Caja Abierta
                    'name': 'Furgoneta Tipo T (Caja Abierta)',
                    'description': 'Furgoneta con caja abierta ideal para transporte de materiales voluminosos. Facilita carga y descarga.',
                    'seats': 3,
                    'volume': 'Caja abierta',
                    'ac': True,
                    'image': self._get_image_path('tipoT'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 86, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 125, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 145, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                34: {  # Tipo V - Furgoneta 11m³
                    'name': 'Furgoneta Tipo V (11m³)',
                    'description': 'Furgoneta de 11 metros cúbicos con capacidad considerable. Ideal para transportes de mayor volumen.',
                    'seats': 3,
                    'volume': '11 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoV'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 66, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 95, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 115, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                35: {  # Tipo W - Furgoneta 13m³
                    'name': 'Furgoneta Tipo W (13m³)',
                    'description': 'Furgoneta de 13 metros cúbicos con gran capacidad de carga. Ideal para mudanzas y transportes grandes.',
                    'seats': 3,
                    'volume': '13 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoW'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 66, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 95, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 115, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                36: {  # Tipo X - Furgoneta 22m³
                    'name': 'Furgoneta Tipo X (22m³)',
                    'description': 'Furgoneta de gran capacidad con 22 metros cúbicos. Máxima capacidad de carga, perfecta para grandes mudanzas y transportes.',
                    'seats': 3,
                    'volume': '22 m³',
                    'ac': True,
                    'image': self._get_image_path('tipoX'),
                    'pricing': [
                        {'duration': '4h', 'km': '150km', 'price': 86, 'features': ['150km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '400km', 'price': 135, 'features': ['400km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '600km', 'price': 155, 'features': ['600km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                37: {  # Tipo Z - Patinete Eléctrico
                    'name': 'Patinete Eléctrico Tipo Z',
                    'description': 'Patinetes eléctricos para movilidad urbana sostenible. Perfectos para desplazamientos cortos y ecológicos.',
                    'seats': 1,
                    'volume': 'Mínimo',
                    'ac': False,
                    'image': self._get_image_path('tipoZ'),
                    'pricing': [
                        {'duration': '2h', 'km': '20km', 'price': 15, 'features': ['20km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico']},
                        {'duration': '4h', 'km': '40km', 'price': 25, 'features': ['40km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico'], 'popular': True},
                        {'duration': '8h', 'km': '80km', 'price': 40, 'features': ['80km autonomía', 'Recogida y entrega en horario laboral', 'Seguro básico']}
                    ]
                },
                38: {  # Tipo B - Combi 7 plazas
                    'name': 'Furgoneta Combi Tipo B',
                    'description': 'Furgonetas medianas ideales para el transporte urbano. Perfectas para equipos de trabajo, servicios de reparto o desplazamientos de personal. Su capacidad de 7 plazas las hace ideales para grupos pequeños.',
                    'seats': 7,
                    'volume': 'Mediano',
                    'ac': True,
                    'image': self._get_image_path('tipoB'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 55, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 85, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 110, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                39: {  # Tipo D - Furgón 3 plazas
                    'name': 'Furgón Tipo D',
                    'description': 'Furgones de gran capacidad para el transporte de mercancías pesadas. Ideales para mudanzas y transporte industrial.',
                    'seats': 3,
                    'volume': 'Grande',
                    'ac': True,
                    'image': self._get_image_path('tipoD'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 70, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 100, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 130, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                40: {  # Tipo E - Furgón 2 plazas
                    'name': 'Furgón Tipo E',
                    'description': 'Furgones extra grandes para el transporte de mercancías voluminosas. Perfectos para mudanzas y transporte de equipos industriales.',
                    'seats': 2,
                    'volume': 'Extra Grande',
                    'ac': True,
                    'image': self._get_image_path('tipoE'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 80, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 110, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 140, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                41: {  # Tipo F - Furgón 2 plazas
                    'name': 'Furgón Tipo F',
                    'description': 'Furgones especiales para servicios profesionales. Ideales para equipos de mantenimiento y servicios técnicos.',
                    'seats': 2,
                    'volume': 'Grande',
                    'ac': True,
                    'image': self._get_image_path('tipoF'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 75, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 105, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 135, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                },
                42: {  # Tipo K - Furgón 2 plazas
                    'name': 'Furgón Tipo K',
                    'description': 'Furgones de lujo para eventos especiales. Perfectos para catering, eventos corporativos y servicios premium.',
                    'seats': 2,
                    'volume': 'Mediano',
                    'ac': True,
                    'image': self._get_image_path('tipoK'),
                    'pricing': [
                        {'duration': '4h', 'km': '100km', 'price': 90, 'features': ['100km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']},
                        {'duration': '24h', 'km': '350km', 'price': 120, 'features': ['350km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio'], 'popular': True},
                        {'duration': '24h', 'km': '500km', 'price': 150, 'features': ['500km autonomía', 'Recogida y entrega en horario laboral', 'Seguro obligatorio']}
                    ]
                }
            }

            # Si no se encontró en el mapeo por nombre, intentar por ID (fallback)
            if not vehicle_info and category_id in vehicle_data_by_id:
                vehicle_info = vehicle_data_by_id[category_id]
                print(f"DEBUG: Using fallback ID mapping for ID {category_id}: {vehicle_info.get('name', 'N/A')}")
            elif vehicle_info:
                print(f"DEBUG: Using name mapping for ID {category_id}: {vehicle_info.get('name', 'N/A')}")

            if vehicle_info:
                # Obtener ofertas fijas desde BD o usar hardcodeadas como fallback
                default_pricing = vehicle_info.get('pricing', [])
                fixed_offers = self._get_fixed_pricing_offers(category_id, default_pricing)
                # Reemplazar las ofertas hardcodeadas con las de BD si existen
                if fixed_offers:
                    vehicle_info['pricing'] = fixed_offers
                    print(f"DEBUG: Using {len(fixed_offers)} fixed offers from database for category {category_id}")
                else:
                    print(f"DEBUG: Using {len(default_pricing)} hardcoded offers for category {category_id}")

                # Obtener tarifas dinámicas del módulo
                pricing_rules = self._get_dynamic_pricing_rules(category_id)

                # Construir el contenido HTML (sin navbar, sin DOCTYPE/html/head/body)
                # Solo el contenido que va dentro del layout de Odoo
                content_html = f"""
                <div class="container py-5">
                                <div class="mb-4">
                                    <button class="btn" style="background-color: {primary_color}; border-color: {primary_color}; color: white;" onclick="window.location.href='/web/booking-enquiry'">
                                        <i class="fa fa-arrow-left me-2"></i>Volver a categorías
                                    </button>
                                </div>

                                <div class="row">
                                    <div class="col-lg-6">
                                        <img src="{vehicle_info.get('image', self._get_image_path('default'))}" 
                                             alt="{vehicle_info.get('name', 'Vehículo')}" class="img-fluid rounded shadow"/>
                                    </div>
                                    <div class="col-lg-6">
                                        <h2>{vehicle_info.get('name', 'Vehículo')}</h2>
                                        <p class="lead">{vehicle_info.get('description', 'Descripción no disponible')}</p>
                                        <div class="row">
                                            <div class="col-md-4">
                                                <div class="text-center p-3 border rounded">
                                                    <i class="fa fa-users fa-2x mb-2" style="color: {primary_color};"></i>
                                                    <h5>{vehicle_info.get('seats', 0)} plazas</h5>
                                                </div>
                                            </div>
                                            <div class="col-md-4">
                                                <div class="text-center p-3 border rounded">
                                                    <i class="fa fa-snowflake-o fa-2x mb-2" style="color: {primary_color};"></i>
                                                    <h5>{'Aire acondicionado' if vehicle_info.get('ac', False) else 'Sin aire acondicionado'}</h5>
                                                </div>
                                            </div>
                                            <div class="col-md-4">
                                                <div class="text-center p-3 border rounded">
                                                    <i class="fa fa-cube fa-2x mb-2" style="color: {primary_color};"></i>
                                                    <h5>{vehicle_info.get('volume', 'Variable')}</h5>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="row mt-5">
                                    <div class="col-12">
                                        <h3>Ofertas de Alquiler</h3>

                                        <!-- Selector de tipo de alquiler -->
                                        <div class="row mb-4">
                                            <div class="col-12">
                                                <div class="card">
                                                    <div class="card-body">
                                                        <h5 class="card-title">Selecciona el tipo de alquiler:</h5>
                                                        <div class="btn-group w-100" role="group">
                                                            <input type="radio" class="btn-check" name="pricing_type" id="fixed_offers" value="fixed" checked>
                                                            <label class="btn btn-outline-warning" for="fixed_offers" style="border-color: {primary_color}; color: {primary_color};">
                                                                <i class="fa fa-tags me-2"></i>Ofertas Fijas
                                                            </label>

                                                            <input type="radio" class="btn-check" name="pricing_type" id="dynamic_pricing" value="dynamic">
                                                            <label class="btn btn-outline-warning" for="dynamic_pricing" style="border-color: {primary_color}; color: {primary_color};">
                                                                <i class="fa fa-calculator me-2"></i>Tarifas Dinámicas
                                                            </label>
                                                        </div>
                                                        <small class="text-muted mt-2 d-block">
                                                            <strong>Ofertas Fijas:</strong> Precios predefinidos | 
                                                            <strong>Tarifas Dinámicas:</strong> Precios calculados según duración y kilometraje
                                                        </small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Ofertas Fijas -->
                                        <div id="fixed_offers_section">
                                            <h4 class="mb-3">Ofertas Predefinidas</h4>
                                            <div class="row">
                                            {''.join([f'''
                                            <div class="col-lg-4 col-md-6 mb-4">
                                                <div class="card h-100 {'border-warning' if offer.get('popular') else ''} offer-card" style="{'border-color: {primary_color} !important; border-width: 2px !important;' if offer.get('popular') else ''} cursor: pointer;" onclick="selectFixedOffer('{offer.get('duration', '')}', '{offer.get('km', '')}', {offer.get('price', 0)})">
                                                    <div class="card-body text-center d-flex flex-column justify-content-center" style="min-height: 100%; padding: 2rem 1.5rem;">
                                                        {'<div class="badge mb-3" style="background-color: {primary_color}; color: white;">Más Popular</div>' if offer.get('popular') else '<div class="mb-3"></div>'}
                                                        <div class="form-check d-flex justify-content-center mb-3">
                                                            <input class="form-check-input" type="radio" name="fixed_offer" id="offer_{offer.get('duration', '').replace('h', '').replace('d', '')}_{offer.get('km', '').replace('km', '')}" value="{offer.get('duration', '')}_{offer.get('km', '')}_{offer.get('price', 0)}">
                                                            <label class="form-check-label ms-2" for="offer_{offer.get('duration', '').replace('h', '').replace('d', '')}_{offer.get('km', '').replace('km', '')}">
                                                                <h4 class="card-title mb-0">{offer.get('duration', '')}</h4>
                                                            </label>
                                                        </div>
                                                        <div class="mb-3">
                                                            <span class="h3" style="color: {primary_color};">€{offer.get('price', 0)}</span>
                                                        </div>
                                                        <p class="text-muted mb-3">{offer.get('km', '')}</p>
                                                        <ul class="list-unstyled mb-0">
                                                            {''.join([f'<li class="mb-1"><i class="fa fa-check text-success me-2"></i>{feature}</li>' for feature in offer.get('features', [])])}
                                                        </ul>
                                                    </div>
                                                </div>
                                            </div>
                                            ''' for offer in vehicle_info.get('pricing', [])])}
                                            </div>
                                        </div>

                                        <!-- Tarifas Dinámicas -->
                                        <div id="dynamic_pricing_section" style="display: none;">
                                            <h4 class="mb-3">Tarifas Calculadas</h4>

                                            <!-- Selectores de Duración y Kilometraje -->
                                            <div class="row mb-4">
                                                <div class="col-md-6">
                                                    <label for="duration_select" class="form-label">
                                                        <i class="fa fa-calendar me-2"></i>Duración del alquiler
                                                    </label>
                                                    <select class="form-select" id="duration_select" onchange="updateKmOptions()">
                                                        <option value="">Selecciona duración...</option>
                                                        <option value="4h">4 horas (mañana o tarde)</option>
                                                        <option value="1-2d">1-2 días</option>
                                                        <option value="3-5d">3-5 días</option>
                                                        <option value="6-10d">6-10 días</option>
                                                        <option value="11-20d">11-20 días</option>
                                                        <option value="21-29d">21-29 días</option>
                                                    </select>
                                                </div>
                                                <div class="col-md-6">
                                                    <label for="km_select" class="form-label">
                                                        <i class="fa fa-road me-2"></i>Kilometraje incluido
                                                    </label>
                                                    <select class="form-select" id="km_select" onchange="updateDynamicPricing()" disabled>
                                                        <option value="">Primero selecciona la duración</option>
                                                    </select>
                                                </div>
                                            </div>

                                            <!-- Resultado de la tarifa -->
                                            <div id="dynamic_pricing_result" class="text-center" style="display: none;">
                                                <div class="card border-warning">
                                                    <div class="card-body">
                                                        <div class="row align-items-center">
                                                            <div class="col-md-8">
                                                                <h5 class="card-title mb-2">
                                                                    <i class="fa fa-calculator me-2 text-warning"></i>
                                                                    Tarifa Calculada
                                                                </h5>
                                                                <p class="card-text mb-1" id="pricing_details"></p>
                                                                <small class="text-muted" id="pricing_features"></small>
                                                            </div>
                                                            <div class="col-md-4">
                                                                <div class="text-end">
                                                                    <h3 class="text-warning mb-0" id="calculated_price">0€</h3>
                                                                    <small class="text-muted">por día</small>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            <!-- Mensaje cuando no hay selección -->
                                            <div id="dynamic_pricing_placeholder" class="text-center text-muted">
                                                <i class="fa fa-info-circle fa-3x mb-3"></i>
                                                <p>Selecciona la duración y el kilometraje para calcular tu tarifa personalizada</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Selector de Ubicación -->
                                <div class="row mt-5">
                                    <div class="col-12">
                                        <div class="card">
                                            <div class="card-header">
                                                <h4>Selecciona la ubicación</h4>
                                            </div>
                                            <div class="card-body">
                                                <div class="mb-3">
                                                    <label for="location_select" class="form-label">
                                                        <i class="fa fa-map-marker me-2" style="color: {primary_color};"></i>
                                                        <strong>Ubicación de recogida *</strong>
                                                    </label>
                                                    <select class="form-select form-select-lg" id="location_select" name="location" required onchange="checkLocationAvailability()">
                                                        <option value="">-- Selecciona una ubicación --</option>
                                                        {''.join([f'<option value="{loc}">{loc}</option>' for loc in available_locations])}
                                                    </select>
                                                    <small class="text-muted mt-2 d-block">
                                                        <i class="fa fa-info-circle me-1"></i>
                                                        Selecciona la ubicación donde deseas recoger el vehículo
                                                    </small>
                                                </div>

                                                <!-- Mensaje cuando no hay vehículos disponibles en la ubicación -->
                                                <div id="no_vehicles_location_message" class="alert alert-warning text-center" style="display: none;">
                                                    <i class="fa fa-exclamation-triangle fa-2x mb-3"></i>
                                                    <h5>No hay vehículos disponibles</h5>
                                                    <p>No se encontraron vehículos de este tipo disponibles en la ubicación seleccionada.</p>
                                                    <p class="mb-0">
                                                        <small>Por favor, selecciona otra ubicación o contacta con nosotros para más información.</small>
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Formulario de Reserva (oculto hasta que se seleccione ubicación y haya vehículos) -->
                                <div class="row mt-4" id="booking_form_section" style="display: none;">
                                    <div class="col-12">
                                        <div class="card">
                                            <div class="card-header">
                                                <h4>Reservar este vehículo</h4>
                                            </div>
                                            <div class="card-body">
                                                <form method="post" action="/rental/payment" id="booking_form">
                                                    <input type="hidden" name="category_id" value="{category_id}"/>
                                                    <input type="hidden" name="location" id="booking_location" value=""/>
                                                    <input type="hidden" name="selected_pricing_type" id="selected_pricing_type" value=""/>
                                                    <input type="hidden" name="selected_duration" id="selected_duration" value=""/>
                                                    <input type="hidden" name="selected_km" id="selected_km" value=""/>
                                                    <input type="hidden" name="selected_price" id="selected_price" value=""/>
                                                    <input type="hidden" name="selected_km_included" id="selected_km_included" value=""/>
                                                    <input type="hidden" name="selected_package_days" id="selected_package_days" value=""/>
                                                    <input type="hidden" name="selected_vehicle_id" id="selected_vehicle_id" value=""/>
                                                    <input type="hidden" name="min_duration_days" id="min_duration_days" value=""/>
                                                    <input type="hidden" name="max_duration_days" id="max_duration_days" value=""/>

                                                    <h5 class="mb-3">Datos de contacto</h5>
                                                    <div class="row">
                                                        <div class="col-md-6 mb-3">
                                                            <label for="customer_name" class="form-label">Nombre completo *</label>
                                                            <input type="text" class="form-control" id="customer_name" name="customer_name" required/>
                                                        </div>
                                                        <div class="col-md-6 mb-3">
                                                            <label for="customer_email" class="form-label">Email *</label>
                                                            <input type="email" class="form-control" id="customer_email" name="customer_email" required/>
                                                        </div>
                                                    </div>
                                                    <div class="row">
                                                        <div class="col-md-6 mb-3">
                                                            <label for="customer_phone" class="form-label">Teléfono *</label>
                                                            <input type="tel" class="form-control" id="customer_phone" name="customer_phone" required/>
                                                        </div>
                                                        <div class="col-md-6 mb-3">
                                                            <label for="customer_company" class="form-label">Empresa (opcional)</label>
                                                            <input type="text" class="form-control" id="customer_company" name="customer_company"/>
                                                        </div>
                                                    </div>
                                                    <div class="row">
                                                        <div class="col-md-6 mb-3">
                                                            <label for="customer_dni" class="form-label">DNI/NIE <span class="text-danger">*</span></label>
                                                            <input type="text" class="form-control" id="customer_dni" name="customer_dni" placeholder="Ej: 12345678A" required/>
                                                        </div>
                                                        <div class="col-md-6 mb-3">
                                                            <label for="customer_dni_expiry_date" class="form-label">Fecha de Expiración del DNI (Mes/Año) <span class="text-danger">*</span></label>
                                                            <input type="month" class="form-control" id="customer_dni_expiry_date" name="customer_dni_expiry_date" required/>
                                                        </div>
                                                    </div>

                                                    <hr class="my-4">
                                                    <h5 class="mb-3">Fechas de alquiler</h5>
                                                    <div id="duration_info" class="alert alert-info" style="display: none;">
                                                        <i class="fa fa-info-circle me-2"></i>
                                                        <span id="duration_message">Seleccione una tarifa para ver la duración mínima requerida</span>
                                                    </div>
                                                    <div class="row">
                                                        <div class="col-md-6 mb-3">
                                                            <label for="start_date" class="form-label">Fecha de inicio *</label>
                                                            <input type="date" class="form-control" id="start_date" name="start_date" required onchange="updateEndDate()"/>
                                                        </div>
                                                        <div class="col-md-6 mb-3">
                                                            <label for="end_date" class="form-label">Fecha de fin *</label>
                                                            <input type="date" class="form-control" id="end_date" name="end_date" required onchange="validateDateRange()"/>
                                                        </div>
                                                    </div>
                                                    <div class="row">
                                                        <div class="col-md-6 mb-3">
                                                            <label for="start_time" class="form-label">Hora de inicio *</label>
                                                            <input type="time" class="form-control" id="start_time" name="start_time" required/>
                                                        </div>
                                                        <div class="col-md-6 mb-3">
                                                            <label for="end_time" class="form-label">Hora de fin *</label>
                                                            <input type="time" class="form-control" id="end_time" name="end_time" required/>
                                                        </div>
                                                    </div>

                                                    <!-- Sección de Vehículos Disponibles -->
                                                    <div id="available_vehicles_section" style="display: none;">
                                                        <hr class="my-4"/>
                                                        <h5 class="mb-3">Vehículos Disponibles</h5>
                                                        <div id="vehicles_loading" class="text-center" style="display: none;">
                                                            <div class="spinner-border text-warning" role="status">
                                                                <span class="visually-hidden">Buscando vehículos...</span>
                                                            </div>
                                                            <p class="mt-2 text-muted">Buscando vehículos disponibles...</p>
                                                        </div>
                                                        <div id="vehicles_container" class="row">
                                                            <!-- Los vehículos se cargarán aquí dinámicamente -->
                                                        </div>
                                                        <div id="no_vehicles_message" class="alert alert-warning text-center" style="display: none;">
                                                            <i class="fa fa-exclamation-triangle fa-2x mb-3"></i>
                                                            <h5>No hay vehículos disponibles</h5>
                                                            <p>No se encontraron vehículos disponibles para las fechas seleccionadas.</p>
                                                        </div>
                                                    </div>

                                                    <div class="text-center">
                                                        <button type="submit" id="submit_btn" class="btn btn-lg" style="background-color: {primary_color}; border-color: {primary_color}; color: white;" disabled>
                                                            <i class="fa fa-calendar-check-o me-2"></i>Continuar con la reserva
                                                        </button>
                                                        <div id="submit_requirements" class="mt-2">
                                                            <small class="text-muted">
                                                                <i class="fa fa-info-circle me-1"></i>
                                                                Complete todos los datos, seleccione una tarifa y un vehículo para continuar
                                                            </small>
                                                        </div>
                                                    </div>
                                                </form>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                <script>
                        document.addEventListener('DOMContentLoaded', function() {{
                            const fixedOffersRadio = document.getElementById('fixed_offers');
                            const dynamicPricingRadio = document.getElementById('dynamic_pricing');
                            const fixedOffersSection = document.getElementById('fixed_offers_section');
                            const dynamicPricingSection = document.getElementById('dynamic_pricing_section');

                            function togglePricingSections() {{
                                if (fixedOffersRadio.checked) {{
                                    fixedOffersSection.style.display = 'block';
                                    dynamicPricingSection.style.display = 'none';
                                }} else if (dynamicPricingRadio.checked) {{
                                    fixedOffersSection.style.display = 'none';
                                    dynamicPricingSection.style.display = 'block';
                                }}
                            }}

                            fixedOffersRadio.addEventListener('change', togglePricingSections);
                            dynamicPricingRadio.addEventListener('change', togglePricingSections);

                            togglePricingSections();
                        }});

                        // Función para actualizar las opciones de kilometraje según la duración
                        function updateKmOptions() {{
                            const duration = document.getElementById('duration_select').value;
                            const kmSelect = document.getElementById('km_select');

                            if (!duration) {{
                                kmSelect.disabled = true;
                                kmSelect.innerHTML = '<option value="">Primero selecciona la duración</option>';
                                return;
                            }}

                            // Mostrar loading
                            kmSelect.disabled = true;
                            kmSelect.innerHTML = '<option value="">Cargando opciones...</option>';

                            // Obtener opciones válidas de kilometraje
                            const formData = new FormData();
                            formData.append('category_id', {category_id});
                            formData.append('duration', duration);

                            fetch('/web/get-valid-km-options', {{
                                method: 'POST',
                                body: formData
                            }})
                            .then(response => response.json())
                            .then(data => {{
                                if (data.success && data.km_options.length > 0) {{
                                    kmSelect.innerHTML = '<option value="">Selecciona kilometraje...</option>';
                                    data.km_options.forEach(km => {{
                                        const option = document.createElement('option');
                                        option.value = km;
                                        option.textContent = km;
                                        kmSelect.appendChild(option);
                                    }});
                                    kmSelect.disabled = false;
                                }} else {{
                                    kmSelect.innerHTML = '<option value="">No hay opciones disponibles</option>';
                                    kmSelect.disabled = true;
                                }}

                                // Resetear resultado de tarifa
                                document.getElementById('dynamic_pricing_result').style.display = 'none';
                                document.getElementById('dynamic_pricing_placeholder').style.display = 'block';
                            }})
                            .catch(error => {{
                                console.error('Error:', error);
                                kmSelect.innerHTML = '<option value="">Error al cargar opciones</option>';
                                kmSelect.disabled = true;
                            }});
                        }}

                        // Función para seleccionar ofertas fijas
                        function selectFixedOffer(duration, km, price) {{
                            // Desmarcar todos los radio buttons
                            const radioButtons = document.querySelectorAll('input[name="fixed_offer"]');
                            radioButtons.forEach(radio => {{
                                radio.checked = false;
                            }});

                            // Marcar el seleccionado
                            const selectedRadio = document.getElementById(`offer_${{duration.replace('h', '').replace('d', '')}}_${{km.replace('km', '')}}`);
                            if (selectedRadio) {{
                                selectedRadio.checked = true;
                            }}

                            // Actualizar visualmente la tarjeta seleccionada
                            const cards = document.querySelectorAll('.offer-card');
                            cards.forEach(card => {{
                                card.style.borderColor = '';
                                card.style.borderWidth = '';
                            }});

                            // Resaltar la tarjeta seleccionada
                            const selectedCard = event.currentTarget;
                            selectedCard.style.borderColor = '{primary_color}';
                            selectedCard.style.borderWidth = '3px';

                            console.log(`Oferta fija seleccionada: ${{duration}} - ${{km}} - €${{price}}`);

                            // Calcular duración mínima y máxima en días
                            const durationRange = calculateMinMaxDays(duration);
                            const minDays = durationRange.min;
                            const maxDays = durationRange.max;

                            // Actualizar campos ocultos del formulario
                            document.getElementById('selected_pricing_type').value = 'fixed';
                            document.getElementById('selected_duration').value = duration;
                            document.getElementById('selected_km').value = km;
                            document.getElementById('selected_price').value = price;
                            document.getElementById('min_duration_days').value = minDays;
                            document.getElementById('max_duration_days').value = maxDays || '';

                            // Mostrar información de duración
                            showDurationInfo(minDays, maxDays);

                            // Actualizar fecha de fin si ya hay fecha de inicio
                            updateEndDate();

                            // Validar formulario
                            validateForm();
                        }}

                        // Función para actualizar campos ocultos cuando se selecciona tarifa dinámica
                        function updateDynamicPricing() {{
                            const duration = document.getElementById('duration_select').value;
                            const kmRange = document.getElementById('km_select').value;
                            const resultDiv = document.getElementById('dynamic_pricing_result');
                            const placeholderDiv = document.getElementById('dynamic_pricing_placeholder');

                            if (!duration || !kmRange) {{
                                resultDiv.style.display = 'none';
                                placeholderDiv.style.display = 'block';
                                return;
                            }}

                            // Mostrar loading
                            resultDiv.style.display = 'block';
                            placeholderDiv.style.display = 'none';
                            document.getElementById('calculated_price').textContent = 'Calculando...';

                            // Llamar al endpoint para obtener la tarifa
                            const formData = new FormData();
                            formData.append('category_id', {category_id});
                            formData.append('duration', duration);
                            formData.append('km_range', kmRange);

                            fetch('/web/get-dynamic-pricing', {{
                                method: 'POST',
                                body: formData
                            }})
                            .then(response => response.json())
                            .then(data => {{
                                if (data.success) {{
                                    document.getElementById('calculated_price').textContent = data.price + '€';
                                    document.getElementById('pricing_details').textContent = 
                                        `Duración: ${{duration}} | Kilometraje: ${{kmRange}}`;
                                    document.getElementById('pricing_features').textContent = 
                                        data.features.join(' • ');

                                    // Calcular duración mínima y máxima en días
                                    const durationRange = calculateMinMaxDays(duration);
                                    const minDays = durationRange.min;
                                    const maxDays = durationRange.max;

                                    // Actualizar campos ocultos del formulario
                                    document.getElementById('selected_pricing_type').value = 'dynamic';
                                    document.getElementById('selected_duration').value = duration;
                                    document.getElementById('selected_km').value = kmRange;
                                    document.getElementById('selected_price').value = data.price;
                                    document.getElementById('selected_km_included').value = data.km_included;
                                    document.getElementById('selected_package_days').value = data.package_days;
                                    document.getElementById('min_duration_days').value = minDays;
                                    document.getElementById('max_duration_days').value = maxDays || '';

                                    // Mostrar información de duración
                                    showDurationInfo(minDays, maxDays);

                                    // Actualizar fecha de fin si ya hay fecha de inicio
                                    updateEndDate();

                                    // Validar formulario
                                    validateForm();
                                }} else {{
                                    document.getElementById('calculated_price').textContent = 'No disponible';
                                    document.getElementById('pricing_details').textContent = data.message;
                                    document.getElementById('pricing_features').textContent = '';
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error:', error);
                                document.getElementById('calculated_price').textContent = 'Error';
                                document.getElementById('pricing_details').textContent = 'Error al calcular la tarifa';
                                document.getElementById('pricing_features').textContent = '';
                            }});
                        }}

                        // Interceptar envío del formulario para validar selección de tarifa y vehículo
                        document.addEventListener('DOMContentLoaded', function() {{
                            const form = document.getElementById('booking_form');
                            if (form) {{
                                form.addEventListener('submit', function(e) {{
                                    const pricingType = document.getElementById('selected_pricing_type').value;
                                    const vehicleId = document.getElementById('selected_vehicle_id').value;

                                    if (!pricingType) {{
                                        e.preventDefault();
                                        alert('Por favor, selecciona una tarifa (Ofertas Fijas o Tarifas Dinámicas)');
                                        return false;
                                    }}

                                    if (!vehicleId) {{
                                        e.preventDefault();
                                        alert('Por favor, selecciona un vehículo disponible');
                                        return false;
                                    }}
                                }});
                            }}

                            // Validar formulario cuando cambien los campos
                            validateForm();

                            // Añadir listeners para validación en tiempo real
                            const inputs = ['customer_name', 'customer_email', 'customer_phone', 'customer_dni', 'customer_dni_expiry_date', 'start_date', 'end_date', 'start_time', 'end_time'];
                            inputs.forEach(inputId => {{
                                const input = document.getElementById(inputId);
                                if (input) {{
                                    input.addEventListener('change', validateForm);
                                    input.addEventListener('input', validateForm);
                                }}
                            }});
                        }});

                        // Función para validar el formulario completo
                        function validateForm() {{
                            const pricingType = document.getElementById('selected_pricing_type').value;
                            const vehicleId = document.getElementById('selected_vehicle_id').value;
                            const customerName = document.getElementById('customer_name').value;
                            const customerEmail = document.getElementById('customer_email').value;
                            const customerPhone = document.getElementById('customer_phone').value;
                            const customerDni = document.getElementById('customer_dni').value;
                            const customerDniExpiry = document.getElementById('customer_dni_expiry_date').value;
                            const startDate = document.getElementById('start_date').value;
                            const endDate = document.getElementById('end_date').value;
                            const startTime = document.getElementById('start_time').value;
                            const endTime = document.getElementById('end_time').value;

                            const submitBtn = document.getElementById('submit_btn');
                            const requirements = document.getElementById('submit_requirements');

                            // Validar que el DNI no esté expirado
                            let dniValid = true;
                            if (customerDniExpiry) {{
                                // Comparar mes/año (el DNI expira al final del mes)
                                const [expiryYear, expiryMonth] = customerDniExpiry.split('-').map(Number);
                                const today = new Date();
                                const currentYear = today.getFullYear();
                                const currentMonth = today.getMonth() + 1; // getMonth() devuelve 0-11

                                // El DNI está expirado si el año es anterior, o si es el mismo año pero el mes es anterior
                                if (expiryYear < currentYear || (expiryYear === currentYear && expiryMonth < currentMonth)) {{
                                    dniValid = false;
                                    // Mostrar mensaje de error
                                    const dniField = document.getElementById('customer_dni_expiry_date');
                                    if (dniField) {{
                                        dniField.setCustomValidity('El DNI está expirado. La fecha de expiración no puede ser anterior al mes actual.');
                                        dniField.reportValidity();
                                    }}
                                }} else {{
                                    const dniField = document.getElementById('customer_dni_expiry_date');
                                    if (dniField) {{
                                        dniField.setCustomValidity('');
                                    }}
                                }}
                            }}

                            // Verificar si todos los campos están completos
                            const allFieldsComplete = customerName && customerEmail && customerPhone && customerDni && customerDniExpiry && startDate && endDate && startTime && endTime && dniValid;

                            if (allFieldsComplete && pricingType && !vehicleId) {{
                                // Cargar vehículos disponibles
                                loadAvailableVehicles();
                            }}

                            // Validar duración de fechas
                            let durationValid = true;
                            if (startDate && endDate && pricingType) {{
                                durationValid = validateDateRange();
                            }}

                            // Habilitar botón solo si todo está completo y la duración es válida
                            if (allFieldsComplete && pricingType && vehicleId && durationValid && dniValid) {{
                                submitBtn.disabled = false;
                                submitBtn.style.opacity = '1';
                                requirements.innerHTML = '<small class="text-success"><i class="fa fa-check me-1"></i>Todo listo para continuar</small>';
                            }} else {{
                                submitBtn.disabled = true;
                                submitBtn.style.opacity = '0.6';
                                let message = 'Complete todos los datos';
                                if (allFieldsComplete && !pricingType) message += ', seleccione una tarifa';
                                if (allFieldsComplete && pricingType && !vehicleId) message += ', seleccione un vehículo';
                                if (!durationValid) message += ', ajuste la duración de fechas';
                                if (!dniValid) message += ', DNI expirado';
                                requirements.innerHTML = `<small class="text-muted"><i class="fa fa-info-circle me-1"></i>${{message}}</small>`;
                            }}
                        }}

                        // Función para cargar vehículos disponibles (actualizada para incluir ubicación)
                        function loadAvailableVehicles() {{
                            const startDate = document.getElementById('start_date').value;
                            const location = document.getElementById('location_select') ? document.getElementById('location_select').value : '';
                            const endDate = document.getElementById('end_date').value;
                            const categoryId = {category_id};

                            if (!startDate || !endDate) return;

                            // Mostrar sección de vehículos
                            document.getElementById('available_vehicles_section').style.display = 'block';
                            document.getElementById('vehicles_loading').style.display = 'block';
                            document.getElementById('vehicles_container').innerHTML = '';
                            document.getElementById('no_vehicles_message').style.display = 'none';

                            // Llamar al endpoint
                            const formData = new FormData();
                            formData.append('category_id', categoryId);
                            formData.append('start_date', startDate);
                            formData.append('end_date', endDate);
                            if (location) {{
                                formData.append('location', location);
                            }}

                            fetch('/web/get-available-vehicles', {{
                                method: 'POST',
                                body: formData
                            }})
                            .then(response => response.json())
                            .then(data => {{
                                document.getElementById('vehicles_loading').style.display = 'none';

                                if (data.success && data.vehicles.length > 0) {{
                                    displayVehicles(data.vehicles);
                                }} else {{
                                    document.getElementById('no_vehicles_message').style.display = 'block';
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error:', error);
                                document.getElementById('vehicles_loading').style.display = 'none';
                                document.getElementById('no_vehicles_message').style.display = 'block';
                            }});
                        }}

                        // Función para mostrar vehículos
                        function displayVehicles(vehicles) {{
                            const container = document.getElementById('vehicles_container');
                            container.innerHTML = '';

                            vehicles.forEach(vehicle => {{
                                // Usar categoría para determinar imagen
                                const categoryName = vehicle.category_name || vehicle.name;
                                // Extraer nombre sin matrícula (quitar la última parte)
                                const nameParts = vehicle.name.split('/');
                                const vehicleName = nameParts.length > 1 ? nameParts.slice(0, -1).join('/') : vehicle.name;

                                // Detectar si es Pinveco o Sunset
                                const currentDomain = window.location.hostname;
                                const isPinveco = currentDomain.includes('pinveco');
                                const imgDir = isPinveco ? '/vehicle_rental/static/description/img/tipos_pinveco' : '/vehicle_rental/static/description/img/tipos';

                                // Extraer tipo de la categoría (Tipo B -> B)
                                const typeMatch = categoryName.match(/Tipo\s+([A-Z])/);
                                let brandImage = '/vehicle_rental/static/description/img/marcas/ford.svg'; // fallback

                                if (typeMatch && typeMatch[1]) {{
                                    const typeId = typeMatch[1]; // B, A, D, etc.
                                    brandImage = `${{imgDir}}/tipo${{typeId}}.png`;
                                }}

                                const vehicleCard = document.createElement('div');
                                vehicleCard.className = 'col-md-6 col-lg-4 mb-3';
                                vehicleCard.innerHTML = `
                                    <div class="card h-100 vehicle-card" style="cursor: pointer;" onclick="selectVehicle(${{vehicle.id}}, '${{vehicle.name}}', '${{vehicle.license_plate}}')">
                                        <div class="card-body text-center">
                                            <img src="${{brandImage}}" class="card-img-top mb-3" style="height: 120px; object-fit: contain;" alt="${{categoryName}}">
                                            <h6 class="card-title">${{vehicleName}}</h6>
                                        </div>
                                    </div>
                                `;
                                container.appendChild(vehicleCard);
                            }});
                        }}

                        // Función para seleccionar vehículo
                        function selectVehicle(vehicleId, vehicleName, licensePlate) {{
                            // Desmarcar todos los vehículos
                            document.querySelectorAll('.vehicle-card').forEach(card => {{
                                card.style.borderColor = '';
                                card.style.borderWidth = '';
                            }});

                            // Marcar el seleccionado
                            event.currentTarget.style.borderColor = '{primary_color}';
                            event.currentTarget.style.borderWidth = '3px';

                            // Guardar selección
                            document.getElementById('selected_vehicle_id').value = vehicleId;

                            console.log(`Vehículo seleccionado: ${{vehicleName}} (${{licensePlate}}) - ID: ${{vehicleId}}`);

                            // Validar formulario
                            validateForm();
                        }}

                        // Función para calcular días mínimos basado en la duración de la tarifa
                        function calculateMinMaxDays(duration) {{
                            let minDays = 1;
                            let maxDays = null; // null significa sin límite máximo

                            if (duration.includes('h')) {{
                                // Para horas, mínimo 1 día, máximo 1 día
                                minDays = 1;
                                maxDays = 1;
                            }} else if (duration.includes('d')) {{
                                // Para días, extraer el rango
                                const rangeMatch = duration.match(/(\d+)-(\d+)d/);
                                if (rangeMatch) {{
                                    // Rango: 3-5d
                                    minDays = parseInt(rangeMatch[1]);
                                    maxDays = parseInt(rangeMatch[2]);
                                }} else {{
                                    // Un solo número: 1d
                                    const singleMatch = duration.match(/(\d+)d/);
                                    if (singleMatch) {{
                                        minDays = parseInt(singleMatch[1]);
                                        maxDays = parseInt(singleMatch[1]); // Mismo valor para min y max
                                    }}
                                }}
                            }}

                            return {{ min: minDays, max: maxDays }};
                        }}

                        // Función legacy para compatibilidad
                        function calculateMinDays(duration) {{
                            const range = calculateMinMaxDays(duration);
                            return range.min;
                        }}

                        // Función para mostrar información de duración
                        function showDurationInfo(minDays, maxDays) {{
                            const durationInfo = document.getElementById('duration_info');
                            const durationMessage = document.getElementById('duration_message');

                            if (minDays && minDays > 0) {{
                                durationInfo.style.display = 'block';
                                if (maxDays && maxDays === minDays) {{
                                    // Si min y max son iguales, es una duración fija
                                    durationMessage.textContent = `Duración requerida: ${{minDays}} día${{minDays > 1 ? 's' : ''}} (exactamente). La fecha de fin se calculará automáticamente.`;
                                }} else if (maxDays) {{
                                    // Hay un rango
                                    durationMessage.textContent = `Duración requerida: entre ${{minDays}} y ${{maxDays}} días. La fecha de fin se calculará automáticamente al mínimo.`;
                                }} else {{
                                    // Solo mínimo
                                    durationMessage.textContent = `Duración mínima requerida: ${{minDays}} días. La fecha de fin se calculará automáticamente.`;
                                }}
                            }} else {{
                                durationInfo.style.display = 'none';
                            }}
                        }}

                        // Función para actualizar la fecha de fin basada en la fecha de inicio y duración mínima
                        function updateEndDate() {{
                            const startDate = document.getElementById('start_date').value;
                            const minDays = parseInt(document.getElementById('min_duration_days').value);

                            if (startDate && minDays) {{
                                const start = new Date(startDate);
                                const end = new Date(start);
                                end.setDate(start.getDate() + minDays);

                                // Formatear fecha para input date (YYYY-MM-DD)
                                const endDateStr = end.toISOString().split('T')[0];
                                document.getElementById('end_date').value = endDateStr;

                                // Validar que no exceda el máximo si existe (sin mostrar alertas)
                                validateDateRange(false);

                                console.log(`Fecha de fin actualizada: ${{startDate}} + ${{minDays}} días = ${{endDateStr}}`);
                            }}
                        }}

                        // Función para validar el rango de fechas
                        function validateDateRange(showAlerts = true) {{
                            const startDate = document.getElementById('start_date').value;
                            const endDate = document.getElementById('end_date').value;
                            const minDays = parseInt(document.getElementById('min_duration_days').value);
                            const maxDaysStr = document.getElementById('max_duration_days').value;
                            const maxDays = maxDaysStr ? parseInt(maxDaysStr) : null;

                            if (startDate && endDate && minDays) {{
                                const start = new Date(startDate);
                                const end = new Date(endDate);
                                const diffTime = end - start;
                                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                                // Validar mínimo
                                if (diffDays < minDays) {{
                                    if (showAlerts) {{
                                        alert(`La duración mínima para esta tarifa es de ${{minDays}} día${{minDays > 1 ? 's' : ''}}. Por favor, seleccione una fecha de fin posterior.`);
                                    }}
                                    // Recalcular automáticamente al mínimo
                                    const newEnd = new Date(start);
                                    newEnd.setDate(start.getDate() + minDays);
                                    document.getElementById('end_date').value = newEnd.toISOString().split('T')[0];
                                    return false;
                                }}

                                // Validar máximo si existe
                                if (maxDays && diffDays > maxDays) {{
                                    if (showAlerts) {{
                                        alert(`La duración máxima para esta tarifa es de ${{maxDays}} día${{maxDays > 1 ? 's' : ''}}. Por favor, seleccione una fecha de fin anterior.`);
                                    }}
                                    // Ajustar automáticamente al máximo
                                    const newEnd = new Date(start);
                                    newEnd.setDate(start.getDate() + maxDays);
                                    document.getElementById('end_date').value = newEnd.toISOString().split('T')[0];
                                    return false;
                                }}

                                // Si min y max son iguales, forzar la duración exacta
                                if (maxDays && maxDays === minDays && diffDays !== minDays) {{
                                    if (showAlerts) {{
                                        alert(`Esta tarifa requiere exactamente ${{minDays}} día${{minDays > 1 ? 's' : ''}}. La fecha de fin se ajustará automáticamente.`);
                                    }}
                                    // Ajustar automáticamente a la duración exacta
                                    const newEnd = new Date(start);
                                    newEnd.setDate(start.getDate() + minDays);
                                    document.getElementById('end_date').value = newEnd.toISOString().split('T')[0];
                                    return false;
                                }}
                            }}
                            return true;
                        }}

                        // Función para verificar disponibilidad de vehículos en la ubicación seleccionada
                        function checkLocationAvailability() {{
                            const locationSelect = document.getElementById('location_select');
                            const location = locationSelect.value;
                            const bookingFormSection = document.getElementById('booking_form_section');
                            const noVehiclesMessage = document.getElementById('no_vehicles_location_message');
                            const bookingLocationInput = document.getElementById('booking_location');

                            // Ocultar formulario y mensaje inicialmente
                            bookingFormSection.style.display = 'none';
                            noVehiclesMessage.style.display = 'none';

                            if (!location) {{
                                return;
                            }}

                            // Actualizar campo oculto de ubicación
                            if (bookingLocationInput) {{
                                bookingLocationInput.value = location;
                            }}

                            // Verificar disponibilidad llamando al endpoint
                            const formData = new FormData();
                            formData.append('category_id', {category_id});
                            formData.append('location', location);
                            // No necesitamos fechas para verificar disponibilidad inicial
                            formData.append('start_date', '');
                            formData.append('end_date', '');

                            // Mostrar indicador de carga
                            noVehiclesMessage.innerHTML = `
                                <div class="text-center">
                                    <div class="spinner-border text-warning mb-3" role="status">
                                        <span class="visually-hidden">Verificando disponibilidad...</span>
                                    </div>
                                    <p>Verificando disponibilidad en ${{location}}...</p>
                                </div>
                            `;
                            noVehiclesMessage.style.display = 'block';

                            fetch('/web/get-available-vehicles', {{
                                method: 'POST',
                                body: formData
                            }})
                            .then(response => response.json())
                            .then(data => {{
                                console.log('Location availability check:', data);

                                if (data.success && data.count > 0) {{
                                    // Hay vehículos disponibles - mostrar formulario
                                    bookingFormSection.style.display = 'block';
                                    noVehiclesMessage.style.display = 'none';

                                    // Scroll suave al formulario
                                    bookingFormSection.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                                }} else {{
                                    // No hay vehículos disponibles - mostrar mensaje
                                    bookingFormSection.style.display = 'none';
                                    noVehiclesMessage.innerHTML = `
                                        <i class="fa fa-exclamation-triangle fa-2x mb-3"></i>
                                        <h5>No hay vehículos disponibles</h5>
                                        <p>No se encontraron vehículos de este tipo disponibles en <strong>${{location}}</strong>.</p>
                                        <p class="mb-0">
                                            <small>Por favor, selecciona otra ubicación o contacta con nosotros para más información.</small>
                                        </p>
                                    `;
                                    noVehiclesMessage.style.display = 'block';
                                }}
                            }})
                            .catch(error => {{
                                console.error('Error checking location availability:', error);
                                bookingFormSection.style.display = 'none';
                                noVehiclesMessage.innerHTML = `
                                    <i class="fa fa-exclamation-triangle fa-2x mb-3"></i>
                                    <h5>Error al verificar disponibilidad</h5>
                                    <p>Hubo un problema al verificar la disponibilidad. Por favor, intenta de nuevo.</p>
                                `;
                                noVehiclesMessage.style.display = 'block';
                            }});
                        }}
                    </script>
                """

                # Usar la plantilla de Odoo para que navbar y footer se rendericen correctamente
                # La plantilla vehicle_detail_template usa website.layout que incluye navbar y footer
                try:
                    return request.render('vehicle_rental.vehicle_detail_template', {
                        'content_html': content_html,
                    })
                except Exception as e:
                    # Si la plantilla no existe, usar el fallback con HTML completo
                    # pero asegurándonos de que los estilos CSS de Odoo se carguen
                    print(f"DEBUG: Error al renderizar plantilla: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback: usar el HTML hardcodeado pero con los estilos CSS de Odoo
                    assets_url = '/web/assets/1/c1278a6/web.assets_frontend.min.css'
                    css_links = f'<link type="text/css" rel="stylesheet" href="{assets_url}"/>'

                    # Devolver HTML completo pero SIN footer hardcodeado
                    # El footer se renderizará automáticamente por Odoo si está configurado
                    return f"""
                    <!DOCTYPE html>
                    <html lang="en-US">
                    <head>
                        <meta charset="utf-8"/>
                        <meta name="viewport" content="width=device-width, initial-scale=1"/>
                        <title>Vista Detalle del Vehículo</title>
                        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                        {css_links}
                    </head>
                    <body>
                        <div id="wrapwrap" class="o_footer_effect_enable">
                            <a class="o_skip_to_content btn btn-primary rounded-0 visually-hidden-focusable position-absolute start-0" href="#wrap">Skip to Content</a>
                            <header id="top" data-anchor="true" data-name="Header" class="o_header_standard">
                                <nav data-name="Navbar" aria-label="Main" class="navbar navbar-expand-lg navbar-light o_colored_level o_cc d-none d-lg-block shadow-sm">
                                    <div id="o_main_nav" class="o_main_nav container">
                                        <a data-name="Navbar Logo" href="/" class="navbar-brand logo me-4">
                                            <span role="img" aria-label="Logo of My Website" title="My Website">
                                                <img src="/web/image/website/1/logo/My%20Website" class="img img-fluid" width="95" height="40" alt="My Website" loading="lazy"/>
                                            </span>
                                        </a>
                                        <ul role="menu" id="top_menu" class="nav navbar-nav top_menu o_menu_loading me-auto">
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/" class="nav-link"><span>Home</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/web/booking-enquiry" class="nav-link active"><span>Booking Enquiry</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/shop" class="nav-link"><span>Shop</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/our-services" class="nav-link"><span>Services</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/about-us" class="nav-link"><span>About Us</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/contactus" class="nav-link"><span>Contact us</span></a>
                                            </li>
                                        </ul>
                                        <ul class="navbar-nav align-items-center gap-2 flex-shrink-0 justify-content-end ps-3">
                                            <li class="o_wsale_my_cart">
                                                <a href="/shop/cart" aria-label="eCommerce cart" class="o_navlink_background btn position-relative rounded-circle p-1 text-center text-reset">
                                                    <div class=""><i class="fa fa-shopping-cart fa-stack"></i><sup class="my_cart_quantity badge bg-primary position-absolute top-0 end-0 mt-n1 me-n1 rounded-pill d-none" data-order-id="">0</sup></div>
                                                </a>
                                            </li>
                                            <li class="">
                                                <a data-bs-target="#o_search_modal" data-bs-toggle="modal" role="button" title="Search" href="#" class="btn rounded-circle p-1 lh-1 o_navlink_background text-reset o_not_editable">
                                                    <i class="oi oi-search fa-stack lh-lg"></i>
                                                </a>
                                            </li>
                                            <li class="">
                                                <a href="tel:+1 555-555-5556" class="nav-link o_nav-link_secondary p-2">
                                                    <i class="fa fa-1x fa-fw fa-phone me-1"></i>
                                                    <span class="o_force_ltr"><small>+1 555-555-5556</small></span>
                                                </a>
                                            </li>
                                            <li class="o_no_autohide_item">
                                                <a href="/web/login" class="o_nav_link_btn nav-link border px-3">Sign in</a>
                                            </li>
                                            <li class="">
                                                <a href="/contactus" class="oe_unremovable btn btn-primary btn_cta">Contact Us</a>
                                            </li>
                                        </ul>
                                    </div>
                                </nav>
                            </header>
                            <div id="wrap">
                                <main>
                                    {content_html}
                                </main>
                            </div>
                        </div>
                        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
                    </body>
                    </html>
                    """
                    # Último fallback: HTML completo con estilos CSS de Odoo cargados
                    # Obtener la URL del asset CSS de Odoo directamente
                    try:
                        # Obtener el asset bundle de Odoo
                        assets_url = '/web/assets/1/c1278a6/web.assets_frontend.min.css'  # URL estándar de Odoo
                        css_links = f'<link type="text/css" rel="stylesheet" href="{assets_url}"/>'
                    except:
                        css_links = ''

                    return f"""
                    <!DOCTYPE html>
                    <html lang="en-US">
                    <head>
                        <meta charset="utf-8"/>
                        <meta name="viewport" content="width=device-width, initial-scale=1"/>
                        <title>Vista Detalle del Vehículo</title>
                        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                        {css_links}
                    </head>
                    <body>
                        <div id="wrapwrap" class="o_footer_effect_enable">
                            <a class="o_skip_to_content btn btn-primary rounded-0 visually-hidden-focusable position-absolute start-0" href="#wrap">Skip to Content</a>
                            <header id="top" data-anchor="true" data-name="Header" class="o_header_standard">
                                <nav data-name="Navbar" aria-label="Main" class="navbar navbar-expand-lg navbar-light o_colored_level o_cc d-none d-lg-block shadow-sm">
                                    <div id="o_main_nav" class="o_main_nav container">
                                        <a data-name="Navbar Logo" href="/" class="navbar-brand logo me-4">
                                            <span role="img" aria-label="Logo of My Website" title="My Website">
                                                <img src="/web/image/website/1/logo/My%20Website" class="img img-fluid" width="95" height="40" alt="My Website" loading="lazy"/>
                                            </span>
                                        </a>
                                        <ul role="menu" id="top_menu" class="nav navbar-nav top_menu o_menu_loading me-auto">
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/" class="nav-link"><span>Home</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/web/booking-enquiry" class="nav-link active"><span>Booking Enquiry</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/shop" class="nav-link"><span>Shop</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/our-services" class="nav-link"><span>Services</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/about-us" class="nav-link"><span>About Us</span></a>
                                            </li>
                                            <li role="presentation" class="nav-item">
                                                <a role="menuitem" href="/contactus" class="nav-link"><span>Contact us</span></a>
                                            </li>
                                        </ul>
                                        <ul class="navbar-nav align-items-center gap-2 flex-shrink-0 justify-content-end ps-3">
                                            <li class="o_wsale_my_cart">
                                                <a href="/shop/cart" aria-label="eCommerce cart" class="o_navlink_background btn position-relative rounded-circle p-1 text-center text-reset">
                                                    <div class=""><i class="fa fa-shopping-cart fa-stack"></i><sup class="my_cart_quantity badge bg-primary position-absolute top-0 end-0 mt-n1 me-n1 rounded-pill d-none" data-order-id="">0</sup></div>
                                                </a>
                                            </li>
                                            <li class="">
                                                <a data-bs-target="#o_search_modal" data-bs-toggle="modal" role="button" title="Search" href="#" class="btn rounded-circle p-1 lh-1 o_navlink_background text-reset o_not_editable">
                                                    <i class="oi oi-search fa-stack lh-lg"></i>
                                                </a>
                                            </li>
                                            <li class="">
                                                <a href="tel:+1 555-555-5556" class="nav-link o_nav-link_secondary p-2">
                                                    <i class="fa fa-1x fa-fw fa-phone me-1"></i>
                                                    <span class="o_force_ltr"><small>+1 555-555-5556</small></span>
                                                </a>
                                            </li>
                                            <li class="o_no_autohide_item">
                                                <a href="/web/login" class="o_nav_link_btn nav-link border px-3">Sign in</a>
                                            </li>
                                            <li class="">
                                                <a href="/contactus" class="oe_unremovable btn btn-primary btn_cta">Contact Us</a>
                                            </li>
                                        </ul>
                                    </div>
                                </nav>
                            </header>
                            <div id="wrap">
                                <main>
                                    {content_html}
                                </main>
                            </div>
                        </div>
                        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
                    </body>
                    </html>
                    """
            else:
                return f"<h1>Error: No category found with ID {category_id}</h1>"
        except Exception as e:
            print(f"DEBUG: Error in vehicle_detail: {e}")
            return f"<h1>Error: {str(e)}</h1>"

    @http.route('/web/booking-enquiry', auth='public', website=True, type='http')
    def contract_booking_enquiry(self, **kw):
        """Contract Booking Enquiry - Detecta dominio para usar template correcto"""
        try:
            values = self._get_initial_values()

            # Detectar el dominio actual
            current_domain = request.httprequest.headers.get('X-Forwarded-Host', request.httprequest.host)

            # Si es Pinveco, añadir una variable para que la plantilla use colores azules
            if 'pinveco' in current_domain.lower():
                values['is_pinveco'] = True
                values['primary_color'] = '#0066B3'
                values['secondary_color'] = '#003D7A'
                print(f"DEBUG: Detected Pinveco domain: {current_domain}, colors: {values['primary_color']}")
            else:
                values['is_pinveco'] = False
                values['primary_color'] = '#FFD700'
                values['secondary_color'] = '#FFA500'
                print(f"DEBUG: Detected Sunset domain: {current_domain}, colors: {values['primary_color']}")

            print(f"DEBUG: Final values being passed to template: {values.keys()}")
            return request.render('vehicle_rental.booking_enquiry_simple', values)
        except Exception as e:
            print(f"DEBUG: Error in contract_booking_enquiry: {e}")
            return f"<h1>Error: {str(e)}</h1>"

    @http.route('/web/get-valid-km-options', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def get_valid_km_options(self, **kw):
        """Get valid km options for a specific duration and category"""
        try:
            import json

            category_id = kw.get('category_id')
            duration = kw.get('duration')

            print(f"DEBUG: Getting valid km options for category {category_id}, duration {duration}")

            # Buscar todas las tarifas disponibles para esta duración
            pricing_rules = request.env['vehicle.pricing.rule'].sudo().search([
                ('vehicle_category_id', '=', int(category_id)),
                ('active', '=', True),
                ('duration_range', '=', duration)
            ])

            # Extraer opciones de kilometraje únicas
            km_options = []
            for rule in pricing_rules:
                if rule.km_range not in km_options:
                    km_options.append(rule.km_range)

            result = {
                'success': True,
                'km_options': km_options
            }

            response = request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
            return response

        except Exception as e:
            print(f"DEBUG: Error getting valid km options: {e}")
            result = {
                'success': False,
                'message': f'Error: {str(e)}'
            }
            response = request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
            return response

    @http.route('/web/get-available-vehicles', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def get_available_vehicles(self, **kw):
        """Get available vehicles for a category and date range"""
        try:
            import json

            category_id = kw.get('category_id')
            start_date = kw.get('start_date')
            end_date = kw.get('end_date')
            location = kw.get('location', '').strip()

            # Detectar la compañía según el dominio
            current_domain = request.httprequest.headers.get('X-Forwarded-Host', request.httprequest.host)
            is_pinveco = 'pinveco' in current_domain.lower()
            company_id = 2 if is_pinveco else 1  # Pinveco=2, Sunset=1

            print(f"DEBUG: Getting available vehicles for category {category_id}, dates {start_date} - {end_date}, location: {location}, company: {company_id}")

            # Buscar vehículos disponibles de la categoría
            print(f"DEBUG: Searching vehicles with category_id={category_id}, company_id={company_id}")

            # Construir dominio de búsqueda
            # Buscar por category_id directamente en el vehículo O por model_id.category_id
            # Y filtrar por compañía y estado
            domain = [
                '|',
                ('category_id', '=', int(category_id)),
                ('model_id.category_id', '=', int(category_id)),
                ('company_id', '=', company_id),
                ('status', '=', 'available')
            ]

            # Nota: En Odoo, el dominio se interpreta como:
            # (category_id = X OR model_id.category_id = X) AND company_id = Y AND status = 'available'

            # Filtrar por ubicación si se proporciona y no es "Todas las ubicaciones"
            if location and location != 'Todas las ubicaciones':
                # Buscar vehículos con la ubicación exacta o variaciones (Málaga/Malaga, Córdoba/Cordoba)
                location_variations = [location]
                if location == 'Málaga':
                    location_variations.append('Malaga')
                elif location == 'Malaga':
                    location_variations.append('Málaga')
                elif location == 'Córdoba':
                    location_variations.append('Cordoba')
                elif location == 'Cordoba':
                    location_variations.append('Córdoba')

                domain.append(('location', 'in', location_variations))
                print(f"DEBUG: Filtering by location: {location_variations}")

            # Primero buscar TODOS los vehículos de la categoría (sin filtro de status) para debug
            all_vehicles = request.env['fleet.vehicle'].sudo().search([
                '|',
                ('category_id', '=', int(category_id)),
                ('model_id.category_id', '=', int(category_id)),
                ('company_id', '=', company_id)
            ])
            print(f"DEBUG: Found {len(all_vehicles)} total vehicles for category {category_id}")
            for v in all_vehicles:
                v_location = getattr(v, 'location', 'N/A')
                print(f"DEBUG:   - Vehicle ID={v.id}, Name={v.name}, Plate={v.license_plate}, Status={v.status if hasattr(v, 'status') else 'N/A'}, Location={v_location}")

            # Ahora buscar solo los disponibles con el filtro de ubicación
            vehicles = request.env['fleet.vehicle'].sudo().search(domain)
            print(f"DEBUG: Found {len(vehicles)} available vehicles matching criteria")

            vehicles_data = []
            for vehicle in vehicles:
                # Obtener categoría
                category_id = vehicle.category_id.id if vehicle.category_id else (vehicle.model_id.category_id.id if vehicle.model_id and vehicle.model_id.category_id else None)
                category_name = vehicle.category_id.name if vehicle.category_id else (vehicle.model_id.category_id.name if vehicle.model_id and vehicle.model_id.category_id else 'Sin categoría')

                vehicles_data.append({
                    'id': vehicle.id,
                    'name': vehicle.name,
                    'license_plate': vehicle.license_plate,
                    'model_name': vehicle.model_id.name if vehicle.model_id else 'Sin modelo',
                    'seats': vehicle.seats,
                    'fuel_type': vehicle.fuel_type,
                    'transmission': vehicle.transmission,
                    'category_id': category_id,
                    'category_name': category_name,
                    'image': f'/web/image/fleet.vehicle/{vehicle.id}/image_128' if hasattr(vehicle, 'image_128') else self._get_image_path('default')
                })

            result = {
                'success': True,
                'vehicles': vehicles_data,
                'count': len(vehicles_data)
            }

            response = request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
            return response

        except Exception as e:
            print(f"DEBUG: Error getting available vehicles: {e}")
            result = {
                'success': False,
                'message': f'Error: {str(e)}'
            }
            response = request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
            return response

    @http.route('/web/get-dynamic-pricing', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def get_dynamic_pricing(self, **kw):
        """Get dynamic pricing for a vehicle category"""
        try:
            import json

            # Obtener datos del POST
            category_id = kw.get('category_id')
            duration = kw.get('duration')
            km_range = kw.get('km_range')

            print(f"DEBUG: Getting dynamic pricing for category {category_id}, duration {duration}, km {km_range}")

            # Buscar tarifas en la base de datos
            pricing_rules = request.env['vehicle.pricing.rule'].sudo().search([
                ('vehicle_category_id', '=', int(category_id)),
                ('active', '=', True),
                ('duration_range', '=', duration),
                ('km_range', '=', km_range)
            ])

            if pricing_rules:
                rule = pricing_rules[0]
                result = {
                    'success': True,
                    'price': rule.price_per_unit,
                    'km_included': rule.km_included,
                    'package_days': rule.package_days,
                    'km_limit': rule.km_limit,
                    'features': [
                        f'{rule.km_included}km autonomía' if rule.km_included < 9999 else 'Sin límite de km',
                        'Recogida y entrega en horario laboral',
                        'Seguro obligatorio'
                    ]
                }
            else:
                result = {
                    'success': False,
                    'message': 'No se encontró tarifa para esta combinación'
                }

            # Devolver como JSON
            response = request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
            return response

        except Exception as e:
            print(f"DEBUG: Error getting dynamic pricing: {e}")
            result = {
                'success': False,
                'message': f'Error: {str(e)}'
            }
            response = request.make_response(
                json.dumps(result),
                headers=[('Content-Type', 'application/json')]
            )
            return response

    @http.route('/web/test-lead-creation', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def test_lead_creation(self, **kw):
        """Test method to create a simple lead"""
        try:
            customer_name = kw.get('customer_name', 'Test Customer')
            customer_email = kw.get('customer_email', 'test@test.com')

            print(f"DEBUG: Test lead creation for {customer_name}")

            # Crear lead básico
            lead_vals = {
                'name': f'Test Lead - {customer_name}',
                'contact_name': customer_name,
                'email_from': customer_email,
                'type': 'lead',
            }

            lead = request.env['crm.lead'].sudo().create(lead_vals)
            print(f"DEBUG: Test lead creado con ID {lead.id}")

            # Forzar commit
            request.env.cr.commit()
            print(f"DEBUG: Test lead commit exitoso")

            # Verificar inmediatamente si se guardó
            lead_check = request.env['crm.lead'].sudo().browse(lead.id)
            print(f"DEBUG: Verificación inmediata - Lead ID {lead_check.id} existe: {lead_check.exists()}")

            return f"<h1>Test Lead creado con ID: {lead.id}</h1>"

        except Exception as e:
            print(f"DEBUG: Error en test lead: {e}")
            import traceback
            print(f"DEBUG: Traceback completo: {traceback.format_exc()}")
            return f"<h1>Error: {str(e)}</h1>"

    @http.route('/web/test-lead-no-html', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def test_lead_no_html(self, **kw):
        """Test method to create lead without HTML generation"""
        try:
            customer_name = kw.get('customer_name', 'Test Customer')
            customer_email = kw.get('customer_email', 'test@test.com')

            print(f"DEBUG: Test lead NO HTML for {customer_name}")

            # Crear lead básico
            lead_vals = {
                'name': f'Test Lead NO HTML - {customer_name}',
                'contact_name': customer_name,
                'email_from': customer_email,
                'type': 'lead',
            }

            lead = request.env['crm.lead'].sudo().create(lead_vals)
            print(f"DEBUG: Test lead NO HTML creado con ID {lead.id}")

            # Forzar commit
            request.env.cr.commit()
            print(f"DEBUG: Test lead NO HTML commit exitoso")

            # Verificar inmediatamente si se guardó
            lead_check = request.env['crm.lead'].sudo().browse(lead.id)
            print(f"DEBUG: Verificación NO HTML - Lead ID {lead_check.id} existe: {lead_check.exists()}")

            # Devolver solo texto plano
            return f"Test Lead NO HTML creado con ID: {lead.id}"

        except Exception as e:
            print(f"DEBUG: Error en test lead NO HTML: {e}")
            import traceback
            print(f"DEBUG: Traceback NO HTML: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    @http.route('/web/test-direct-sql', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def test_direct_sql(self, **kw):
        """Test method using direct SQL to create lead"""
        try:
            customer_name = kw.get('customer_name', 'Test Customer')
            customer_email = kw.get('customer_email', 'test@test.com')

            print(f"DEBUG: Test DIRECT SQL for {customer_name}")

            # Usar SQL directo para insertar
            import psycopg2
            from odoo import sql_db

            # Obtener conexión directa
            db = sql_db.db_connect('odoo-dev')
            with db.cursor() as cr:
                cr.execute("""
                    INSERT INTO crm_lead (name, contact_name, email_from, type, create_date, write_date, create_uid, write_uid)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), 1, 1)
                    RETURNING id
                """, (f'Test DIRECT SQL - {customer_name}', customer_name, customer_email, 'lead'))

                lead_id = cr.fetchone()[0]
                print(f"DEBUG: Test DIRECT SQL creado con ID {lead_id}")

                # Commit directo
                cr.commit()
                print(f"DEBUG: Test DIRECT SQL commit exitoso")

                return f"Test DIRECT SQL creado con ID: {lead_id}"

        except Exception as e:
            print(f"DEBUG: Error en test DIRECT SQL: {e}")
            import traceback
            print(f"DEBUG: Traceback DIRECT SQL: {traceback.format_exc()}")
            return f"Error: {str(e)}"

    def _find_or_create_partner(self, name, email, phone, company):
        """Find existing partner or create new one from customer data"""
        Partner = request.env['res.partner']

        # 1. Buscar por email si existe
        if email:
            partner = Partner.sudo().search([
                ('email', '=', email.strip().lower())
            ], limit=1)
            if partner:
                print(f"DEBUG: Contacto encontrado por email: {partner.name}")
                return partner

        # 2. Buscar por teléfono si existe
        if phone:
            # Limpiar el teléfono de espacios y caracteres especiales
            clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
            partners = Partner.sudo().search([
                ('phone', '!=', False)
            ])
            for partner in partners:
                partner_phone = (partner.phone or '').replace(' ', '').replace('-', '').replace('+', '')
                if partner_phone and partner_phone == clean_phone:
                    print(f"DEBUG: Contacto encontrado por teléfono: {partner.name}")
                    return partner

        # 3. Si no existe, crear nuevo contacto
        if name or email or phone:
            partner_vals = {
                'name': name or 'Cliente Web',
                'email': email,
                'phone': phone,
                'customer_rank': 1,  # Marcar como cliente
                'comment': f'Contacto creado automáticamente desde reserva web: {name}',
            }

            if company:
                partner_vals['is_company'] = True
                partner_vals['name'] = company
                partner_vals['comment'] += f' (Empresa: {company})'

            partner = Partner.sudo().create(partner_vals)
            print(f"DEBUG: Nuevo contacto creado: {partner.name}")
            return partner

        return False

    def _find_available_vehicle(self, category_id, start_date, end_date):
        """Find an available vehicle for the given category and dates"""
        try:
            print(f"DEBUG: Buscando vehículo para categoría {category_id} en fechas {start_date} - {end_date}")

            # Convertir fechas a formato datetime
            from datetime import datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # Buscar vehículos de la categoría que estén disponibles
            vehicles = request.env['fleet.vehicle'].sudo().search([
                ('category_id', '=', category_id),
                ('status', '=', 'available')
            ])

            print(f"DEBUG: Vehículos encontrados en categoría {category_id}: {len(vehicles)}")

            # Por ahora, devolver el primer vehículo disponible (sin verificación de contratos)
            if vehicles:
                vehicle = vehicles[0]
                print(f"DEBUG: Vehículo seleccionado: {vehicle.name} (ID: {vehicle.id}) - DISPONIBLE para las fechas {start_date} - {end_date}")
                return vehicle

            print(f"DEBUG: No se encontraron vehículos disponibles para categoría {category_id} en fechas {start_date} - {end_date}")
            return False

        except Exception as e:
            print(f"DEBUG: Error en _find_available_vehicle: {e}")
            return False

    # ===== ENDPOINT REDSYS PAGO =====
#     @http.route('/web/booking-confirmation', auth='public', website=True, type='http', methods=['POST'], csrf=False)
#     def booking_confirmation(self, **kw):
#         """Booking Confirmation - Redsys Payment"""
#         import base64, json, hmac, hashlib, binascii, subprocess, tempfile, os, time
#         
#         def derive_key_3des(secret_b64, order):
#             secret = base64.b64decode(secret_b64)
#             order_bytes = order.encode('ascii')
#             pad = (-len(order_bytes)) % 8
#             order_padded = order_bytes + b'\x00'*pad
#             with tempfile.NamedTemporaryFile(delete=False) as f:
#                 f.write(order_padded)
#                 f.flush()
#                 key_hex = binascii.hexlify(secret).decode('ascii')
#             out_path = tempfile.mktemp()
#             try:
#                 subprocess.check_call(['openssl','enc','-des-ede3-cbc','-K', key_hex, '-iv','0000000000000000','-nopad','-in', f.name, '-out', out_path])
#                 return open(out_path,'rb').read()
#             finally:
#                 os.unlink(f.name)
#                 if os.path.exists(out_path): os.unlink(out_path)
#         
#         try:
#             merchant_code = '369056973'
#             terminal = '1'
#             secret_key = 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'
#             
#             amount_cents = int(float(kw.get('selected_price', 0)) * 100)
#             if amount_cents < 1: amount_cents = 1
#             order_number = kw.get('order_number', f'ORD{int(time.time())}')
#             
#             merchant_data = {
#                 'DS_MERCHANT_AMOUNT': str(amount_cents),
#                 'DS_MERCHANT_ORDER': order_number,
#                 'DS_MERCHANT_MERCHANTCODE': merchant_code,
#                 'DS_MERCHANT_CURRENCY': '978',
#                 'DS_MERCHANT_TRANSACTIONTYPE': '0',
#                 'DS_MERCHANT_TERMINAL': terminal,
#                 'DS_MERCHANT_MERCHANTURL': 'https://sunsetrent.es/web/redsys-webhook',
#             }
#             
#             merchant_json = json.dumps(merchant_data, separators=(',', ':'))
#             merchant_params = base64.b64encode(merchant_json.encode('utf-8')).decode('utf-8')
#             
#             K = derive_key_3des(secret_key, order_number)
#             signature_bytes = hmac.new(K, merchant_params.encode('utf-8'), hashlib.sha256).digest()
#             signature = base64.b64encode(signature_bytes).decode('utf-8')
#             
#             # Devolver HTML directo con los valores interpolados
#             print(f"DEBUG HTML: merchant_params={merchant_params[:50]}... signature={signature}")
#             html = '<html><body onload="document.forms[0].submit()"><h2>Procesando pago...</h2><form id="f" method="POST" action="https://sis-t.redsys.es:25443/sis/realizarPago"><input type="hidden" name="Ds_SignVersion" value="HMAC_SHA256_V1"/><input type="hidden" name="Ds_MerchantParameters" value="' + merchant_params + '"/><input type="hidden" name="Ds_Signature" value="' + signature + '"/></form></body></html>'
#             return html
# 
#         except Exception as e:
#             return f"<h1>Error en booking_confirmation</h1><pre>{str(e)}</pre>"

    # ===== NUEVO FLUJO: Usar payment_redsys nativo =====
    # @http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    # def rental_payment_gateway(self, **kw):
    #     """Create payment transaction for vehicle rental"""
    #     import logging
    #     import json
    #     import time
    #     _logger = logging.getLogger(__name__)

    #     try:
    #         # Obtener datos de la reserva
    #         category_id = int(kw.get('category_id', 0))
            _logger.warning(f"RENTAL_PAYMENT_PARAMS: {kw}")
    #         selected_price = float(kw.get('selected_price', 0))
    #         customer_name = kw.get('customer_name', '')
    #         customer_email = kw.get('customer_email', '')
    #         customer_phone = kw.get('customer_phone', '')
    #         start_date = kw.get('start_date', '')
    #         end_date = kw.get('end_date', '')
    #         order_number = kw.get('order_number', f'RENT-{int(time.time())}')

    #         _logger.info(f"DEBUG RENTAL PAYMENT: Creating payment.transaction for order {order_number}")

    #         # Preparar datos de booking
    #         booking_data = {
    #             'category_id': category_id,
    #             'customer_name': customer_name,
    #             'customer_email': customer_email,
    #             'customer_phone': customer_phone,
    #             'start_date': start_date,
    #             'end_date': end_date,
    #         }

    #         # Guardar en sesión
    #         request.session['booking_data'] = booking_data

    #         # Obtener provider Redsys
    #         providers = request.env['payment.provider'].sudo().search([('code', '=', 'redsys')], limit=1)
    #         if not providers:
    #             providers = request.env['payment.provider'].sudo().search([], limit=1)

    #         if not providers:
    #             raise Exception("No payment provider available")

    #         # Obtener payment_method para el provider
    #         payment_methods = request.env['payment.method'].sudo().search([
    #             ('provider_ids', 'in', providers.id)
    #         ], limit=1)

    #         if not payment_methods:
    #             # Si no existe, crear uno genérico
    #             # Imagen base64 mínima (1x1 PNG blanco)
    #             minimal_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

    #             payment_methods = request.env['payment.method'].sudo().create({
    #                 'name': 'Credit/Debit Card',
    #                 'code': 'card',
    #                 'image': minimal_image,
    #                 'provider_ids': [(4, providers.id)],  # Agregar provider al Many2many
    #             })
    #             _logger.info(f"DEBUG: Created payment.method {payment_methods.id} with provider {providers.id}")

    #         # Crear payment.transaction
    #         payment_tx = request.env['payment.transaction'].sudo().create({
    #             'provider_id': providers.id,
    #             'payment_method_id': payment_methods.id,
    #             'amount': selected_price,
    #             'currency_id': request.env.company.currency_id.id,
    #             'partner_id': request.env.user.partner_id.id,
    #             'reference': order_number,
    #             'booking_data_json': json.dumps(booking_data),
    #         })

    #         _logger.info(f"DEBUG RENTAL PAYMENT: payment.transaction created with ID {payment_tx.id}")

    #         # Redirigir al formulario de pago
    #         return request.redirect(f'/payment/process/{payment_tx.id}')

    #     except Exception as e:
    #         import logging
    #         import traceback
    #         _logger = logging.getLogger(__name__)
    #         error_detail = traceback.format_exc()
    #         _logger.error(f"ERROR en rental_payment_gateway: {error_detail}")
    #         return f"<h1>Error</h1><p>{str(e)}</p><pre>{error_detail}</pre>", 500

    @http.route('/test/rental-endpoint', auth='public', website=True, type='http')
    def test_rental_endpoint(self):
        return "TEST RENTAL ENDPOINT WORKS"

    @http.route('/rental/payment/test', auth='public', website=False, type='http', methods=['POST'], csrf=False)
    def test_rental_payment(self):
        return "TEST RENTAL PAYMENT OK"

    @http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_payment(self, **kw):
        """Create payment transaction for vehicle rental"""
        import logging
        import json
        import base64
        import hmac
        import hashlib
        from werkzeug.wrappers import Response
        import time as time_mod
        
        _logger = logging.getLogger(__name__)
        
        try:
            # Extraer parámetros
            category_id = int(kw.get('category_id', 0))
            selected_price = float(kw.get('selected_price', 0))
            customer_email = kw.get('customer_email', '').strip()
            customer_name = kw.get('customer_name', 'Guest').strip()
            customer_phone = kw.get('customer_phone', '').strip()
            
            start_date = kw.get('start_date', '')
            end_date = kw.get('end_date', '')
            start_time = kw.get('start_time', '')
            end_time = kw.get('end_time', '')
            
            # Validar campos requeridos
            if not category_id or selected_price <= 0 or not customer_email:
                return Response(
                    json.dumps({"error": "Missing required fields"}),
                    status=400,
                    mimetype='application/json'
                )
            
            # Guardar datos en sesión
            request.session['booking_data'] = {
                'category_id': category_id,
                'selected_price': selected_price,
                'customer_email': customer_email,
                'customer_name': customer_name,
                'customer_phone': customer_phone,
                'start_date': start_date,
                'end_date': end_date,
                'start_time': start_time,
                'end_time': end_time,
            }
            
            # Obtener/crear partner
            partner = request.env['res.partner'].sudo().search([('email', '=', customer_email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': customer_name,
                    'email': customer_email,
                    'phone': customer_phone,
                    'customer_rank': 1,
                })
            else:
                partner.sudo().write({
                    'phone': customer_phone or partner.phone,
                    'name': customer_name or partner.name,
                })
            
            order_number = f'ORD{int(time_mod.time())}'
            
            # Buscar provider Redsys
            provider = request.env['payment.provider'].sudo().search([('code', '=', 'redsys')], limit=1)
            if not provider:
                provider = request.env['payment.provider'].sudo().search([], limit=1)
            
            if not provider:
                return Response(
                    json.dumps({"error": "No payment provider found"}),
                    status=500,
                    mimetype='application/json'
                )
            
            # Buscar o crear payment.method
            payment_method = request.env['payment.method'].sudo().search([
                ('provider_ids', 'in', [provider.id]),
                ('name', '=', 'Credit Card')
            ], limit=1)
            
            if not payment_method:
                payment_method = request.env['payment.method'].sudo().create({
                    'name': 'Credit Card',
                    'code': 'card',
                    'provider_ids': [(4, provider.id)],
                })
            
            # Crear payment.transaction
            tx = request.env['payment.transaction'].sudo().create({
                'provider_id': provider.id,
                'payment_method_id': payment_method.id,
                'amount': selected_price,
                'currency_id': request.env.company.currency_id.id,
                'partner_id': partner.id,
                'reference': order_number,
            })
            
            _logger.info(f"Created payment.transaction: {tx.id}")
            
            # Generar formulario Redsys usando HMAC-SHA256_V1
            merchant_code = '369056973'
            terminal = '1'
            secret_key = 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'
            
            amount_cents = int(selected_price * 100)
            currency = '978'  # EUR
            
            merchant_data = {
                'Ds_Merchant_Amount': str(amount_cents),
                'Ds_Merchant_Currency': str(currency),
                'Ds_Merchant_Order': order_number.zfill(12),
                'Ds_Merchant_MerchantCode': merchant_code,
                'Ds_Merchant_Terminal': terminal,
                'Ds_Merchant_TransactionType': '0',
                'Ds_Merchant_MerchantURL': f'https://sunsetrent.es/payment/webhook/{tx.id}',
                'Ds_Merchant_UrlOK': f'https://sunsetrent.es/rental/success',
                'Ds_Merchant_UrlKO': f'https://sunsetrent.es/rental/error',
            }
            
            # Codificar merchant_data en base64
            merchant_json = json.dumps(merchant_data)
            merchant_params = base64.b64encode(merchant_json.encode()).decode()
            
            # Generar firma HMAC-SHA256
            try:
                signature = hmac.new(secret_key.encode(), merchant_params.encode(), hashlib.sha256).digest()
                signature_b64 = base64.b64encode(signature).decode()
                _logger.info(f"Signature generated: {signature_b64[:20]}...")
            except Exception as e:
                _logger.error(f"Error generating signature: {e}", exc_info=True)
                signature_b64 = ''
            
            # Generar formulario HTML para Redsys
            redsys_url = 'https://sis-t.redsys.es:25443/sis/realizarPago'
            
            from html import escape
            html_form = f'''<!DOCTYPE html>
<html>
<head>
    <title>Procesando pago...</title>
</head>
<body onload="document.redsysForm.submit();">
    <form name="redsysForm" action="{redsys_url}" method="POST">
        <input type="hidden" name="Ds_SignatureVersion" value="HMAC_SHA256_V1"/>
        <input type="hidden" name="Ds_MerchantParameters" value="{escape(merchant_params)}"/>
        <input type="hidden" name="Ds_Signature" value="{escape(signature_b64)}"/>
        <noscript>
            <p>Por favor haz clic en el botón para continuar:</p>
            <input type="submit" value="Continuar"/>
        </noscript>
    </form>
</body>
</html>'''
            
            return Response(html_form, mimetype='text/html')
            
        except Exception as e:
            _logger.error(f"RENTAL PAYMENT ERROR: {str(e)}", exc_info=True)
            return Response(
                json.dumps({"error": str(e)}),
                status=500,
                mimetype='application/json'
            )


    @http.route('/rental/payment-test', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_payment_test(self, **kw):
        return "RENTAL PAYMENT TEST OK"

    @http.route('/rental/debug', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_debug(self, **kw):
        import logging
        _logger = logging.getLogger(__name__)
        try:
            _logger.info("DEBUG: rental_debug START")
            _logger.info(f"DEBUG: kw={kw}")
            _logger.info("DEBUG: Creating response")
            return ("OK", 200)
        except Exception as e:
            _logger.error(f"DEBUG ERROR: {e}")
            return (str(e), 500)

    @http.route('/rental/payment-form-debug', auth='public', website=True, type='http', methods=['GET'], csrf=False)
    def rental_payment_form_debug(self, **kw):
        """Debug endpoint to show the form that will be sent to Redsys"""
        import logging
        import json
        import base64
        import hmac
        import hashlib
        from werkzeug.wrappers import Response
        
        _logger = logging.getLogger(__name__)
        
        # Test data
        merchant_code = '369056973'
        terminal = '1'
        order_number = 'TESTORD123456'
        selected_price = 150.00
        tx_id = 999
        secret_key = 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'
        
        amount_cents = int(selected_price * 100)
        currency = '978'
        
        merchant_data = {
            'Ds_Merchant_Amount': str(amount_cents),
            'Ds_Merchant_Currency': str(currency),
            'Ds_Merchant_Order': order_number.zfill(12),
            'Ds_Merchant_MerchantCode': merchant_code,
            'Ds_Merchant_Terminal': terminal,
            'Ds_Merchant_TransactionType': '0',
            'Ds_Merchant_MerchantURL': f'https://sunsetrent.es/payment/webhook/{tx_id}',
            'Ds_Merchant_UrlOK': f'https://sunsetrent.es/rental/success',
            'Ds_Merchant_UrlKO': f'https://sunsetrent.es/rental/error',
        }
        
        merchant_json = json.dumps(merchant_data)
        merchant_params = base64.b64encode(merchant_json.encode()).decode()
        
        signature = hmac.new(secret_key.encode(), merchant_params.encode(), hashlib.sha256).digest()
        signature_b64 = base64.b64encode(signature).decode()
        
        _logger.warning(f"=== REDSYS DEBUG ===")
        _logger.warning(f"Merchant Data: {merchant_data}")
        _logger.warning(f"Merchant Params: {merchant_params}")
        _logger.warning(f"Signature: {signature_b64}")
        
        redsys_url = 'https://sis-t.redsys.es:25443/sis/realizarPago'
        
        html_debug = f'''<!DOCTYPE html>
<html>
<head>
    <title>DEBUG Redsys Form</title>
    <style>
        body {{ font-family: monospace; padding: 20px; }}
        .field {{ margin: 10px 0; padding: 10px; background: #f0f0f0; }}
        .label {{ font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Redsys Form Debug</h1>
    <div class="field">
        <div class="label">Ds_SignatureVersion:</div>
        <div>HMAC_SHA256_V1</div>
    </div>
    <div class="field">
        <div class="label">Ds_MerchantParameters:</div>
        <div style="word-break: break-all;">{merchant_params}</div>
    </div>
    <div class="field">
        <div class="label">Ds_Signature:</div>
        <div>{signature_b64}</div>
    </div>
    
    <h2>Decoded Merchant Data:</h2>
    <pre>{json.dumps(merchant_data, indent=2)}</pre>
    
    <hr>
    <p>
        <a href="#" onclick="document.redsysForm.submit(); return false;">Click here to submit to Redsys</a>
        or
        <button onclick="document.redsysForm.submit();">Submit Form</button>
    </p>
    
    <form name="redsysForm" action="{redsys_url}" method="POST" style="display:none;">
        <input type="hidden" name="Ds_SignatureVersion" value="HMAC_SHA256_V1"/>
        <input type="hidden" name="Ds_MerchantParameters" value="{merchant_params}"/>
        <input type="hidden" name="Ds_Signature" value="{signature_b64}"/>
    </form>
</body>
</html>'''
        
        return Response(html_debug, mimetype='text/html')
