# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _

FUEL_LEVEL_SELECTION = [
    ('0', 'Vacío'),
    ('1', '1/4'),
    ('2', '2/4 (Medio)'),
    ('3', '3/4'),
    ('4', 'Lleno'),
]


class VehicleContractReturn(models.Model):
    """Vehicle Contract Return - Registro de devoluciones de vehículos"""
    _name = 'vehicle.contract.return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Devolución de Vehículo del Contrato'
    _order = 'return_date desc'
    _rec_name = 'display_name'

    # Referencia al contrato
    contract_id = fields.Many2one(
        'vehicle.contract',
        string='Contrato',
        required=True,
        ondelete='cascade',
        index=True
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Devuelto',
        required=True
    )
    return_date = fields.Datetime(
        string='Fecha de Devolución',
        required=True,
        default=fields.Datetime.now
    )
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user
    )

    # Estado del vehículo a la devolución
    odometer = fields.Float(string='Kilometraje de Devolución')
    odometer_start = fields.Float(
        string='Kilometraje de Entrega',
        help='Kilometraje registrado en el contrato al momento de la entrega'
    )
    km_driven = fields.Float(
        string='Kilómetros Recorridos',
        compute='_compute_km_driven',
        store=True
    )
    odometer_unit = fields.Selection(
        related='contract_id.odometer_unit',
        string='Unidad'
    )
    fuel_level = fields.Selection(
        FUEL_LEVEL_SELECTION,
        string='Nivel de Combustible (Devolución)'
    )
    fuel_level_start = fields.Selection(
        FUEL_LEVEL_SELECTION,
        string='Nivel de Combustible (Entrega)'
    )

    # Inspección de daños
    inspection_done = fields.Boolean(
        string='Vehículo Inspeccionado',
        default=False
    )
    has_damage = fields.Boolean(string='¿Tiene Daños?', default=False)
    damage_description = fields.Html(string='Descripción de Daños')
    damage_amount = fields.Monetary(
        string='Importe de Daños',
        currency_field='currency_id'
    )
    damage_image_ids = fields.Many2many(
        'ir.attachment',
        'vehicle_return_damage_rel',
        'return_id',
        'attachment_id',
        string='Fotos de Daños'
    )
    painted_damage_image = fields.Binary(string='Imagen Pintada de Daños')
    damage_invoice_id = fields.Many2one(
        'account.move',
        string='Factura de Daños'
    )

    # Documentación
    acta_generated = fields.Boolean(string='Acta Generada', default=False)
    acta_pdf = fields.Binary(string='PDF del Acta')
    acta_filename = fields.Char(
        string='Nombre del Archivo',
        compute='_compute_acta_filename'
    )
    customer_signature = fields.Binary(string='Firma del Cliente')
    company_signature = fields.Binary(string='Firma de la Empresa')
    signature_date = fields.Datetime(string='Fecha de Firma')

    # Auxiliares
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

    @api.depends('odometer', 'odometer_start')
    def _compute_km_driven(self):
        """Kilómetros recorridos durante el contrato"""
        for rec in self:
            rec.km_driven = max(rec.odometer - rec.odometer_start, 0.0)

    @api.depends('contract_id', 'vehicle_id', 'return_date')
    def _compute_display_name(self):
        """Compute display name"""
        for rec in self:
            if rec.contract_id and rec.vehicle_id:
                date_str = fields.Datetime.to_string(rec.return_date)[:10] if rec.return_date else ''
                rec.display_name = f"{rec.contract_id.reference_no} - Devolución {rec.vehicle_id.license_plate} ({date_str})"
            else:
                rec.display_name = 'Nueva Devolución'

    @api.depends('contract_id', 'return_date')
    def _compute_acta_filename(self):
        """Compute acta filename"""
        for rec in self:
            if rec.contract_id:
                date_str = fields.Datetime.to_string(rec.return_date)[:10] if rec.return_date else ''
                rec.acta_filename = f"Acta_Devolución_{rec.contract_id.reference_no}_{date_str}.pdf"
            else:
                rec.acta_filename = 'acta_devolucion.pdf'

    def fuel_label(self, value):
        """Etiqueta legible de un nivel de combustible (para informes y correos)."""
        return dict(FUEL_LEVEL_SELECTION).get(value, '-')

    def get_process_invoices(self):
        """Todas las facturas emitidas del contrato, para el resumen final."""
        self.ensure_one()
        return self.env['account.move'].sudo().search([
            ('vehicle_contract_id', '=', self.contract_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '!=', 'cancel'),
        ], order='invoice_date, id')

    def action_send_return_email(self, extra_attachment_ids=None):
        """Enviar al cliente el correo de cierre con el resumen del proceso."""
        self.ensure_one()
        if not self.contract_id.customer_id.email:
            return False
        template = self.env.ref(
            'vehicle_rental.email_template_vehicle_contract_return',
            raise_if_not_found=False
        )
        if not template:
            return False
        email_values = {}
        if extra_attachment_ids:
            email_values['attachment_ids'] = [(6, 0, extra_attachment_ids)]
        template.sudo().send_mail(
            self.id,
            force_send=False,
            email_values=email_values or None,
        )
        return True

    def action_generate_acta(self):
        """Generar acta de devolución en PDF"""
        self.ensure_one()
        self.acta_generated = True
        return self.env.ref(
            'vehicle_rental.action_report_vehicle_contract_return'
        ).report_action(self)

    def action_create_damage_invoice(self):
        """Crear factura por los daños detectados en la devolución"""
        self.ensure_one()
        if not self.has_damage or not self.damage_amount:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('No hay daños registrados o el importe es cero'),
                }
            }
        if self.damage_invoice_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('Esta devolución ya tiene factura de daños'),
                }
            }

        invoice_line_vals = {
            'product_id': self.env.ref('vehicle_rental.vehicle_damage_amount').id,
            'name': f"Daños - Devolución {self.display_name}",
            'quantity': 1,
            'price_unit': self.damage_amount,
        }
        invoice_data = {
            'partner_id': self.contract_id.customer_id.id,
            'move_type': 'out_invoice',
            'journal_id': self.contract_id._get_sale_journal().id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, invoice_line_vals)],
            'vehicle_contract_id': self.contract_id.id,
        }
        invoice = self.env['account.move'].sudo().create(invoice_data)
        self.damage_invoice_id = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Daños'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_damage_invoice(self):
        """Abrir la factura de daños"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Daños'),
            'res_model': 'account.move',
            'res_id': self.damage_invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
