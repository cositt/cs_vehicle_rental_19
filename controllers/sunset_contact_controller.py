# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SunsetContactController(http.Controller):
    """Controlador para la página de contacto de Sunset"""

    @http.route('/contactus', type='http', auth='public', website=True)
    def sunset_contact(self, **kw):
        """Página de contacto de Sunset"""
        
        # Información de contacto de Sunset
        contact_info = {
            'company_name': 'Sunset Rent a Car',
            'address': 'Calle Principal 123, 28001 Madrid, España',
            'phone': '+34 91 123 45 67',
            'email': 'info@sunsetrentacar.com',
            'hours': 'Lunes a Viernes: 8:00 - 20:00\nSábados: 9:00 - 18:00\nDomingos: 10:00 - 16:00',
        }
        
        # Delegaciones
        delegations = [
            {
                'name': 'Madrid Centro',
                'address': 'Calle Gran Vía 45, 28013 Madrid',
                'phone': '+34 91 123 45 67',
                'email': 'madrid@sunsetrentacar.com'
            },
            {
                'name': 'Barcelona',
                'address': 'Passeig de Gràcia 123, 08008 Barcelona',
                'phone': '+34 93 123 45 67',
                'email': 'barcelona@sunsetrentacar.com'
            },
            {
                'name': 'Valencia',
                'address': 'Calle Colón 78, 46004 Valencia',
                'phone': '+34 96 123 45 67',
                'email': 'valencia@sunsetrentacar.com'
            }
        ]
        
        return request.render('vehicle_rental.sunset_contact_simple', {
            'contact_info': contact_info,
            'delegations': delegations,
        })

    @http.route('/contactus/enviar', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def sunset_contact_submit(self, **kw):
        """Procesar envío del formulario de contacto"""
        
        # Información de contacto para pasar a las plantillas
        contact_info = {
            'company_name': 'Sunset Rent a Car',
            'address': 'Calle Principal 123, 28001 Madrid, España',
            'phone': '+34 91 123 45 67',
            'email': 'info@sunsetrentacar.com',
            'hours': 'Lunes a Viernes: 8:00 - 20:00\nSábados: 9:00 - 18:00\nDomingos: 10:00 - 16:00',
        }
        
        delegations = [
            {
                'name': 'Madrid Centro',
                'address': 'Calle Gran Vía 45, 28013 Madrid',
                'phone': '+34 91 123 45 67',
                'email': 'madrid@sunsetrentacar.com'
            },
            {
                'name': 'Barcelona',
                'address': 'Passeig de Gràcia 123, 08008 Barcelona',
                'phone': '+34 93 123 45 67',
                'email': 'barcelona@sunsetrentacar.com'
            },
            {
                'name': 'Valencia',
                'address': 'Calle Colón 78, 46004 Valencia',
                'phone': '+34 96 123 45 67',
                'email': 'valencia@sunsetrentacar.com'
            }
        ]
        
        # Validar campos obligatorios (verificar que no estén vacíos)
        required_fields = ['name', 'email', 'subject', 'message']
        missing_fields = []
        for field in required_fields:
            value = kw.get(field, '')
            if not value or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)
        
        if missing_fields:
            return request.render('vehicle_rental.sunset_contact_simple', {
                'error': f'Faltan campos obligatorios: {", ".join(missing_fields)}',
                'form_data': kw,
                'contact_info': contact_info,
                'delegations': delegations
            })
        
        # Obtener source_id de forma segura
        source_id = None
        try:
            source_ref = request.env.ref('crm.crm_lead_source_website', raise_if_not_found=False)
            if source_ref:
                source_id = source_ref.id
        except Exception:
            pass  # Si no existe, source_id será None
        
        # Crear lead en CRM
        lead_data = {
            'name': f"Contacto Web: {kw.get('subject')}",
            'contact_name': kw.get('name'),
            'email_from': kw.get('email'),
            'phone': kw.get('phone', ''),
            'description': kw.get('message'),
            'type': 'lead',
        }
        
        # Solo añadir source_id si existe
        if source_id:
            lead_data['source_id'] = source_id
        
        try:
            lead = request.env['crm.lead'].sudo().create(lead_data)
            
            # Enviar email de confirmación (opcional)
            # Aquí podrías agregar lógica para enviar un email de confirmación
            
            return request.render('vehicle_rental.sunset_contact_success', {
                'lead': lead,
                'contact_name': kw.get('name')
            })
            
        except Exception as e:
            return request.render('vehicle_rental.sunset_contact_simple', {
                'error': f'Error al enviar el mensaje: {str(e)}',
                'form_data': kw,
                'contact_info': contact_info,
                'delegations': delegations
            })
