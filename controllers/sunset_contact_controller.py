# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SunsetContactController(http.Controller):
    """Controlador para la página de contacto de Sunset"""

    def _contact_values(self, **extra):
        """Datos de contacto reales: los de la compañía del sitio web.

        Antes estaban escritos a mano (una oficina en Madrid y delegaciones en
        Barcelona y Valencia que no existen).
        """
        partner = request.website.company_id.partner_id.sudo()
        address = ', '.join(part for part in [
            partner.street,
            ' '.join(p for p in [partner.zip, partner.city] if p),
            partner.state_id.name,
        ] if part)
        values = {
            'contact_info': {
                'company_name': request.website.company_id.name,
                'address': address,
                'phone': partner.phone or '',
                'email': (partner.email or '').lower(),
            },
            # Se llenarán con el modelo de delegaciones (Fase 4 del plan)
            'delegations': [],
        }
        values.update(extra)
        return values

    @http.route('/contactus', type='http', auth='public', website=True)
    def sunset_contact(self, **kw):
        """Página de contacto de Sunset"""
        return request.render('vehicle_rental.sunset_contact_simple', self._contact_values())

    @http.route('/contactus/enviar', type='http', auth='public', website=True, methods=['POST'])
    def sunset_contact_submit(self, **kw):
        """Procesar envío del formulario de contacto"""
        # Validar campos obligatorios (verificar que no estén vacíos)
        required_fields = ['name', 'email', 'subject', 'message']
        missing_fields = [
            field for field in required_fields
            if not (kw.get(field) or '').strip()
        ]
        if missing_fields:
            return request.render('vehicle_rental.sunset_contact_simple', self._contact_values(
                error=f'Faltan campos obligatorios: {", ".join(missing_fields)}',
                form_data=kw,
            ))

        lead_data = {
            'name': f"Contacto Web: {kw.get('subject')}",
            'contact_name': kw.get('name'),
            'email_from': kw.get('email'),
            'phone': kw.get('phone', ''),
            'description': kw.get('message'),
            'type': 'lead',
            'company_id': request.website.company_id.id,
        }
        source = request.env.ref('crm.crm_lead_source_website', raise_if_not_found=False)
        if source:
            lead_data['source_id'] = source.id

        try:
            lead = request.env['crm.lead'].sudo().create(lead_data)
        except Exception:
            return request.render('vehicle_rental.sunset_contact_simple', self._contact_values(
                error='No se ha podido enviar el mensaje. Inténtelo de nuevo o llámenos.',
                form_data=kw,
            ))
        return request.render('vehicle_rental.sunset_contact_success', self._contact_values(
            lead=lead,
            contact_name=kw.get('name'),
        ))
