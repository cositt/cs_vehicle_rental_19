# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class VehicleContractSubstitution(models.Model):
    """Vehicle Contract Substitution - Registro de sustituciones de vehículos"""
    _name = 'vehicle.contract.substitution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sustitución de Vehículo en Contrato'
    _order = 'substitution_date desc'
    _rec_name = 'display_name'

    # Referencia al contrato
    contract_id = fields.Many2one(
        'vehicle.contract',
        string='Contrato',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Información de la sustitución
    substitution_date = fields.Datetime(
        string='Fecha de Sustitución',
        required=True,
        default=fields.Datetime.now
    )
    
    reason = fields.Selection([
        ('breakdown', 'Avería del Vehículo'),
        ('accident', 'Accidente'),
        ('maintenance', 'Mantenimiento Programado'),
        ('upgrade', 'Mejora de Categoría'),
        ('downgrade', 'Reducción de Categoría'),
        ('customer_request', 'Solicitud del Cliente'),
        ('other', 'Otro Motivo')
    ], string='Motivo de Sustitución', required=True)
    
    reason_notes = fields.Text(string='Notas del Motivo')
    
    # VEHÍCULO ORIGINAL (el que se devuelve)
    old_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Original',
        required=True
    )
    old_vehicle_odometer = fields.Float(
        string='Kilometraje de Devolución (Original)',
        help='Kilometraje del vehículo original al momento de la sustitución'
    )
    old_vehicle_fuel_level = fields.Selection([
        ('0', 'Vacío'),
        ('1', '1/4'),
        ('2', '2/4 (Medio)'),
        ('3', '3/4'),
        ('4', 'Lleno')
    ], string='Nivel de Combustible (Original)')
    
    old_vehicle_has_damage = fields.Boolean(
        string='¿Tiene Daños? (Original)',
        default=False
    )
    old_vehicle_damage_description = fields.Html(
        string='Descripción de Daños (Original)'
    )
    old_vehicle_damage_amount = fields.Monetary(
        string='Monto de Daños (Original)',
        currency_field='currency_id'
    )
    old_vehicle_damage_images = fields.Many2many(
        'ir.attachment',
        'vehicle_substitution_old_damage_rel',
        'substitution_id',
        'attachment_id',
        string='Imágenes de Daños (Original)'
    )
    old_vehicle_painted_damage_image = fields.Binary(
        string='Imagen Pintada de Daños (Original)'
    )
    
    # VEHÍCULO NUEVO (el sustituto)
    new_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Sustituto',
        required=True,
        domain="[('status', '=', 'available')]"
    )
    new_vehicle_odometer = fields.Float(
        string='Kilometraje de Entrega (Sustituto)',
        help='Kilometraje del vehículo sustituto al momento de la entrega'
    )
    new_vehicle_fuel_level = fields.Selection([
        ('0', 'Vacío'),
        ('1', '1/4'),
        ('2', '2/4 (Medio)'),
        ('3', '3/4'),
        ('4', 'Lleno')
    ], string='Nivel de Combustible (Sustituto)', default='4')
    
    new_vehicle_has_damage = fields.Boolean(
        string='¿Tiene Daños Previos? (Sustituto)',
        default=False
    )
    new_vehicle_damage_description = fields.Html(
        string='Descripción de Daños Previos (Sustituto)'
    )
    new_vehicle_damage_images = fields.Many2many(
        'ir.attachment',
        'vehicle_substitution_new_damage_rel',
        'substitution_id',
        'attachment_id',
        string='Imágenes de Daños Previos (Sustituto)'
    )
    new_vehicle_painted_damage_image = fields.Binary(
        string='Imagen Pintada de Daños (Sustituto)'
    )
    
    # Documentación Legal
    addendum_generated = fields.Boolean(
        string='Addendum Generado',
        default=False
    )
    addendum_pdf = fields.Binary(
        string='PDF del Addendum'
    )
    addendum_filename = fields.Char(
        string='Nombre del Archivo',
        compute='_compute_addendum_filename'
    )
    
    # Firmas
    company_signature = fields.Binary(string='Firma de la Empresa')
    customer_signature = fields.Binary(string='Firma del Cliente')
    signature_date = fields.Datetime(string='Fecha de Firma')
    
    # Facturación (si hay diferencia de precio)
    has_price_difference = fields.Boolean(
        string='¿Hay Diferencia de Precio?',
        default=False
    )
    price_difference = fields.Monetary(
        string='Diferencia de Precio',
        currency_field='currency_id',
        help='Positivo si el nuevo vehículo es más caro, negativo si es más barato'
    )
    price_difference_invoice_id = fields.Many2one(
        'account.move',
        string='Factura de Diferencia de Precio'
    )
    
    # Información adicional
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='contract_id.company_id',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='contract_id.currency_id'
    )
    notes = fields.Text(string='Notas Adicionales')
    
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('contract_id', 'old_vehicle_id', 'new_vehicle_id', 'substitution_date')
    def _compute_display_name(self):
        """Compute display name"""
        for rec in self:
            if rec.contract_id and rec.old_vehicle_id and rec.new_vehicle_id:
                date_str = fields.Datetime.to_string(rec.substitution_date)[:10] if rec.substitution_date else ''
                rec.display_name = f"{rec.contract_id.reference_no} - {rec.old_vehicle_id.license_plate} → {rec.new_vehicle_id.license_plate} ({date_str})"
            else:
                rec.display_name = 'Nueva Sustitución'

    @api.depends('contract_id', 'substitution_date')
    def _compute_addendum_filename(self):
        """Compute addendum filename"""
        for rec in self:
            if rec.contract_id:
                date_str = fields.Datetime.to_string(rec.substitution_date)[:10] if rec.substitution_date else ''
                rec.addendum_filename = f"Addendum_Sustitución_{rec.contract_id.reference_no}_{date_str}.pdf"
            else:
                rec.addendum_filename = 'addendum.pdf'

    def action_generate_addendum(self):
        """Generar documento addendum/anexo al contrato"""
        self.ensure_one()
        # Aquí se generaría el PDF del addendum
        # Por ahora marcamos como generado
        self.addendum_generated = True
        
        # Retornar la vista del PDF o del reporte
        return self.env.ref('vehicle_rental.action_report_vehicle_substitution_addendum').report_action(self)

    def action_create_damage_invoice(self):
        """Crear factura por daños del vehículo original si aplica"""
        self.ensure_one()
        if not self.old_vehicle_has_damage or not self.old_vehicle_damage_amount:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('No hay daños registrados o el monto es cero'),
                }
            }
        
        # Crear factura de daños
        invoice_line_vals = {
            'product_id': self.env.ref('vehicle_rental.vehicle_damage_amount').id,
            'name': f"Daños - Sustitución {self.display_name}",
            'quantity': 1,
            'price_unit': self.old_vehicle_damage_amount,
        }
        
        invoice_data = {
            'partner_id': self.contract_id.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, invoice_line_vals)],
            'vehicle_contract_id': self.contract_id.id
        }
        
        invoice = self.env['account.move'].sudo().create(invoice_data)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Daños'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_price_difference_invoice(self):
        """Crear factura por diferencia de precio si aplica"""
        self.ensure_one()
        if not self.has_price_difference or not self.price_difference:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('No hay diferencia de precio registrada'),
                }
            }
        
        # Determinar el tipo de factura según si es cargo o devolución
        move_type = 'out_invoice' if self.price_difference > 0 else 'out_refund'
        price_abs = abs(self.price_difference)
        
        invoice_line_vals = {
            'product_id': self.env.ref('vehicle_rental.vehicle_rent_charge').id,
            'name': f"Ajuste de precio - Sustitución {self.display_name}",
            'quantity': 1,
            'price_unit': price_abs,
        }
        
        invoice_data = {
            'partner_id': self.contract_id.customer_id.id,
            'move_type': move_type,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, invoice_line_vals)],
            'vehicle_contract_id': self.contract_id.id
        }
        
        invoice = self.env['account.move'].sudo().create(invoice_data)
        self.price_difference_invoice_id = invoice.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Ajuste de Precio'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

