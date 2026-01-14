# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import secrets
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BookingEnquiryLead(models.Model):
    """Booking Enquiry Lead"""
    _inherit = 'crm.lead'
    _description = __doc__

    access_token = fields.Char()
    # Booking Enquiry Details
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle",
                                 domain="[('status', '=', 'available')]")
    category_id = fields.Many2one(related='vehicle_id.category_id', string="Category")
    selected_category_id = fields.Many2one('fleet.vehicle.model.category', 
                                         string="Selected Category",
                                         help="Categoría seleccionada en la web")
    seats = fields.Integer(related='vehicle_id.seats', string="Seats Number")
    start_date = fields.Date()
    end_date = fields.Date()
    contract_id = fields.Many2one('vehicle.contract', string="Contract")
    customer_dni = fields.Char(string="DNI/NIE", help="Documento Nacional de Identidad o NIE del cliente")
    customer_dni_expiry_date = fields.Date(string="Fecha de Expiración del DNI", help="Fecha de expiración del documento de identidad")
    location = fields.Char(string="Ubicación de Recogida", help="Ubicación donde el cliente recogerá el vehículo")
    start_time = fields.Char(string="Hora de Inicio", help="Hora de recogida del vehículo")
    end_time = fields.Char(string="Hora de Fin", help="Hora de devolución del vehículo")

    @api.model_create_multi
    def create(self, vals_list):
        """Create claim record"""
        records = super().create(vals_list)
        for record in records:
            # Generate a URL-safe access token without underscores
            token = secrets.token_urlsafe(12).replace('_', '-')
            record.access_token = token
        return records

    def action_set_won(self):
        """Convert lead to opportunity and mark as won
        Automatically find or create a contact from lead data"""
        for lead in self:
            if lead.type == 'lead':
                # Si no tiene partner asignado, intentar encontrar o crear uno
                if not lead.partner_id:
                    partner = self._find_or_create_partner_from_lead(lead)
                    if partner:
                        lead.partner_id = partner.id
                
                # Si no tiene vehículo asignado pero tiene categoría seleccionada, buscar uno disponible
                if not lead.vehicle_id and lead.selected_category_id:
                    available_vehicle = self._find_available_vehicle_for_category(lead.selected_category_id.id)
                    if available_vehicle:
                        lead.vehicle_id = available_vehicle.id
                
                # Convert to opportunity
                lead.type = 'opportunity'
                lead.probability = 100
        return True
    
    def _find_or_create_partner_from_lead(self, lead):
        """Find existing partner or create new one from lead data"""
        Partner = self.env['res.partner']
        
        # 1. Buscar por email si existe
        if lead.email_from:
            partner = Partner.search([
                ('email', '=', lead.email_from.strip().lower())
            ], limit=1)
            if partner:
                return partner
        
        # 2. Buscar por teléfono si existe
        if lead.phone:
            # Limpiar el teléfono de espacios y caracteres especiales
            clean_phone = lead.phone.replace(' ', '').replace('-', '').replace('+', '')
            partners = Partner.search([
                ('phone', '!=', False)
            ])
            for partner in partners:
                partner_phone = (partner.phone or '').replace(' ', '').replace('-', '').replace('+', '')
                if partner_phone and partner_phone == clean_phone:
                    return partner
        
        # 3. Si no existe, crear nuevo contacto
        if lead.contact_name or lead.email_from or lead.phone:
            partner_vals = {
                'name': lead.contact_name or lead.name or 'Cliente Web',
                'email': lead.email_from,
                'phone': lead.phone,
                'customer_rank': 1,  # Marcar como cliente
                'comment': f'Contacto creado automáticamente desde reserva web: {lead.name}',
            }
            
            partner = Partner.create(partner_vals)
            return partner
        
        return False
    
    def _find_available_vehicle_for_category(self, category_id):
        """Find an available vehicle for the given category"""
        Vehicle = self.env['fleet.vehicle']
        
        print(f"DEBUG: Buscando vehículo para categoría {category_id}")
        
        # Buscar vehículos disponibles de la categoría
        vehicles = Vehicle.search([
            ('model_id.category_id', '=', category_id),
            ('status', '=', 'available')
        ], limit=1)
        
        print(f"DEBUG: Vehículos encontrados: {len(vehicles)}")
        
        if vehicles:
            print(f"DEBUG: Vehículo asignado: {vehicles[0].name} (ID: {vehicles[0].id})")
            return vehicles[0]
        
        print(f"DEBUG: No se encontraron vehículos disponibles para categoría {category_id}")
        return False
    
    def action_print_contract(self):
        """Imprimir el contrato del vehículo"""
        for lead in self:
            if lead.contract_id:
                return {
                    'type': 'ir.actions.report',
                    'report_name': 'vehicle_rental.vehicle_contract_report',
                    'report_type': 'qweb-pdf',
                    'data': {'ids': [lead.contract_id.id]},
                    'context': self.env.context,
                }
            else:
                raise UserError(_('No hay contrato asociado a este lead.'))
    
    def action_send_contract(self):
        """Enviar el contrato por email"""
        for lead in self:
            if lead.contract_id:
                # Renderizar PDF del contrato
                report_xmlid = 'vehicle_rental.action_vehicle_contract_report'
                pdf_content, _dummy = self.env['ir.actions.report']._render_qweb_pdf(
                    report_xmlid,
                    [lead.contract_id.id]
                )
                filename = f"Contrato_{lead.contract_id.name}.pdf"

                # Crear adjunto
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': self.env['ir.binary']._encode_base64(pdf_content),
                    'res_model': 'vehicle.contract',
                    'res_id': lead.contract_id.id,
                    'mimetype': 'application/pdf',
                })

                # Enviar email usando plantilla
                template = self.env.ref('vehicle_rental.email_template_vehicle_contract', False)
                if not template:
                    raise UserError(_('No se encontró el template de email para contratos.'))

                template.send_mail(
                    lead.contract_id.id,
                    force_send=True,
                    email_values={'attachment_ids': [(4, attachment.id)]}
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Contrato Enviado'),
                        'message': _('El contrato ha sido enviado por email al cliente.'),
                        'type': 'success',
                    }
                }
            else:
                raise UserError(_('No hay contrato asociado a este lead.'))
