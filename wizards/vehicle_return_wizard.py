# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import base64

from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..models.vehicle_contract_return import FUEL_LEVEL_SELECTION


class VehicleReturnWizard(models.TransientModel):
    """Wizard para registrar la devolución de un vehículo en un contrato activo"""
    _name = 'vehicle.contract.return.wizard'
    _description = 'Asistente de Devolución de Vehículo'

    contract_id = fields.Many2one(
        'vehicle.contract',
        string='Contrato',
        required=True,
        readonly=True
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        related='contract_id.customer_id',
        readonly=True
    )
    return_date = fields.Datetime(
        string='Fecha de Devolución',
        required=True,
        default=fields.Datetime.now
    )

    # === VEHÍCULO ===
    # Se usa current_vehicle_id (no vehicle_id) para respetar sustituciones previas
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        compute='_compute_vehicle',
        store=True,
        readonly=True
    )
    vehicle_license_plate = fields.Char(
        string='Matrícula',
        related='vehicle_id.license_plate',
        readonly=True
    )
    odometer_start = fields.Float(
        string='Kilometraje de Entrega',
        compute='_compute_vehicle',
        store=True,
        readonly=True
    )
    odometer = fields.Float(string='Kilometraje de Devolución')
    odometer_unit = fields.Selection(
        related='contract_id.odometer_unit',
        string='Unidad',
        readonly=True
    )
    km_driven = fields.Float(
        string='Kilómetros Recorridos',
        compute='_compute_km_driven'
    )
    fuel_level_start = fields.Selection(
        FUEL_LEVEL_SELECTION,
        string='Combustible en Entrega',
        compute='_compute_vehicle',
        store=True,
        readonly=False
    )
    fuel_level = fields.Selection(
        FUEL_LEVEL_SELECTION,
        string='Combustible en Devolución'
    )

    # === INSPECCIÓN DE DAÑOS ===
    inspection_done = fields.Boolean(
        string='He inspeccionado el vehículo',
        default=False
    )
    has_damage = fields.Boolean(string='El vehículo presenta daños', default=False)
    damage_description = fields.Html(string='Descripción de los Daños')
    damage_amount = fields.Monetary(
        string='Importe Estimado de Daños',
        currency_field='currency_id',
        help='Opcional. Déjelo a cero si la valoración se hará más adelante; '
             'los daños podrán facturarse después desde la ficha de la devolución.'
    )
    painted_damage_image = fields.Binary(string='Imagen de Daños Pintada')
    invoice_damage_now = fields.Boolean(
        string='Facturar los daños ahora',
        default=False
    )

    # === FIRMA ===
    request_signature = fields.Boolean(
        string='Solicitar firma del cliente',
        default=False
    )
    customer_signature = fields.Binary(string='Firma del Cliente')
    company_signature = fields.Binary(string='Firma de la Empresa')

    notes = fields.Text(string='Notas Adicionales')

    # === CIERRE ===
    send_closing_email = fields.Boolean(
        string='Enviar email de cierre al cliente',
        default=True,
        help='Envía al cliente el resumen final del proceso con el acta de devolución adjunta.'
    )
    customer_email = fields.Char(
        related='contract_id.customer_id.email',
        string='Email del Cliente',
        readonly=True
    )

    # Auxiliares
    company_id = fields.Many2one(
        'res.company',
        related='contract_id.company_id',
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='contract_id.currency_id',
        readonly=True
    )

    @api.depends('contract_id')
    def _compute_vehicle(self):
        """Vehículo actual del contrato, respetando sustituciones previas"""
        for wizard in self:
            contract = wizard.contract_id
            wizard.vehicle_id = contract.current_vehicle_id or contract.vehicle_id
            wizard.odometer_start = contract.last_odometer or 0.0
            wizard.fuel_level_start = contract.initial_fuel_level or False

    @api.depends('odometer', 'odometer_start')
    def _compute_km_driven(self):
        """Kilómetros recorridos durante el contrato"""
        for wizard in self:
            wizard.km_driven = max(wizard.odometer - wizard.odometer_start, 0.0)

    @api.onchange('has_damage')
    def _onchange_has_damage(self):
        """Limpiar datos de daños si se desmarca"""
        for wizard in self:
            if not wizard.has_damage:
                wizard.damage_description = False
                wizard.damage_amount = 0.0
                wizard.invoice_damage_now = False

    @api.constrains('odometer', 'odometer_start')
    def _check_odometer(self):
        """El kilometraje de devolución no puede ser menor al de entrega"""
        for wizard in self:
            if wizard.odometer and wizard.odometer < wizard.odometer_start:
                raise ValidationError(
                    _('El kilometraje de devolución (%s) no puede ser menor al registrado en la entrega (%s)') %
                    (wizard.odometer, wizard.odometer_start)
                )

    def _reopen(self):
        """Reabrir este mismo asistente conservando lo introducido."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devolución de Vehículo'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_clear_damage_image(self):
        """Borrar las marcas para volver a empezar el dibujo."""
        self.ensure_one()
        self.painted_damage_image = False
        return self._reopen()

    def action_open_damage_painter(self):
        """Abrir editor de daños para el vehículo devuelto"""
        self.ensure_one()
        painter_wizard = self.env['vehicle.contract.return.damage.painter'].create({
            'return_wizard_id': self.id,
            'vehicle_id': self.vehicle_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Editor de Daños - Vehículo Devuelto'),
            'res_model': 'vehicle.contract.return.damage.painter',
            'res_id': painter_wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_return_wizard_id': self.id,
                'default_vehicle_id': self.vehicle_id.id,
            },
        }

    def _validate_return(self):
        """Validaciones de la política híbrida antes de confirmar"""
        self.ensure_one()
        if self.contract_id.status != 'b_in_progress':
            raise UserError(_('Solo se pueden devolver vehículos de contratos en progreso.'))
        if not self.odometer:
            raise UserError(_('Debe indicar el kilometraje de devolución.'))
        if self.odometer < self.odometer_start:
            raise UserError(
                _('El kilometraje de devolución (%s) no puede ser menor al registrado en la entrega (%s).') %
                (self.odometer, self.odometer_start)
            )
        if not self.fuel_level:
            raise UserError(_('Debe indicar el nivel de combustible de la devolución.'))
        if not self.inspection_done:
            raise UserError(
                _('Debe confirmar que ha inspeccionado el vehículo antes de cerrar la devolución.')
            )
        # El importe no se exige a propósito: la valoración puede ser posterior
        # (peritaje). Los daños se pueden facturar más tarde desde la devolución.
        if self.has_damage and not self.damage_description:
            raise UserError(_('Ha marcado que hay daños: describa los daños detectados.'))
        if self.request_signature and not self.customer_signature:
            raise UserError(
                _('Ha solicitado la firma del cliente: recoja la firma o desmarque la opción.')
            )

    def _build_chatter_message(self, return_record):
        """Construir el mensaje resumen para el chatter del contrato"""
        self.ensure_one()
        fuel_labels = dict(FUEL_LEVEL_SELECTION)
        unit = 'km' if self.odometer_unit == 'kilometers' else 'mi'
        date_str = self.return_date.strftime('%d/%m/%Y %H:%M')

        fuel_row = ''
        if self.fuel_level_start:
            fuel_row = Markup('''
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Combustible:</td>
                        <td style="padding: 5px;">%s → %s</td>
                    </tr>
            ''') % (
                fuel_labels.get(self.fuel_level_start, '-'),
                fuel_labels.get(self.fuel_level, '-'),
            )
        else:
            fuel_row = Markup('''
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Combustible:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
            ''') % fuel_labels.get(self.fuel_level, '-')

        if self.has_damage:
            if self.damage_amount:
                importe = '%s %s' % (f"{self.damage_amount:,.2f}", self.currency_id.symbol or '')
            else:
                importe = _('importe pendiente de valorar')
            damage_row = Markup('''
                    <tr style="background-color: #f8d7da;">
                        <td style="padding: 5px; font-weight: bold;">Daños:</td>
                        <td style="padding: 5px;">SÍ — %s</td>
                    </tr>
            ''') % importe
        else:
            damage_row = Markup('''
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Daños:</td>
                        <td style="padding: 5px;">Inspeccionado — sin daños</td>
                    </tr>
            ''')

        signature_row = ''
        if self.customer_signature:
            signature_row = Markup('''
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Firma del cliente:</td>
                        <td style="padding: 5px;">Recogida</td>
                    </tr>
            ''')

        return_link = Markup('''
                    <tr>
                        <td colspan="2" style="padding: 10px 5px; text-align: center;">
                            <a href="/web#id=%s&amp;model=vehicle.contract.return&amp;view_type=form"
                               style="color: #007bff; text-decoration: none; font-weight: bold;">
                                <i class="fa fa-file-text-o"></i> Ver Acta de Devolución
                            </a>
                        </td>
                    </tr>
        ''') % return_record.id

        return Markup('''
            <div style="padding: 10px; background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px;">
                <h4 style="color: #0c5460; margin: 0 0 10px 0;">
                    <i class="fa fa-check-circle"></i> Vehículo Devuelto
                </h4>
                <table style="width: 100%%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; font-weight: bold; width: 40%%;">Fecha:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 5px; font-weight: bold;">Vehículo:</td>
                        <td style="padding: 5px;">%s (%s)</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Kilometraje:</td>
                        <td style="padding: 5px;">%s → %s %s (%s %s recorridos)</td>
                    </tr>
                    %s
                    %s
                    %s
                    %s
                </table>
            </div>
        ''') % (
            date_str,
            self.vehicle_id.name, self.vehicle_id.license_plate or '-',
            f"{self.odometer_start:,.0f}", f"{self.odometer:,.0f}", unit,
            f"{self.km_driven:,.0f}", unit,
            fuel_row,
            damage_row,
            signature_row,
            return_link,
        )

    def action_confirm_return(self):
        """Confirmar y ejecutar la devolución del vehículo"""
        self.ensure_one()
        self._validate_return()

        contract = self.contract_id

        # 1. Crear el registro de devolución
        return_record = self.env['vehicle.contract.return'].create({
            'contract_id': contract.id,
            'vehicle_id': self.vehicle_id.id,
            'return_date': self.return_date,
            'odometer': self.odometer,
            'odometer_start': self.odometer_start,
            'fuel_level': self.fuel_level,
            'fuel_level_start': self.fuel_level_start,
            'inspection_done': self.inspection_done,
            'has_damage': self.has_damage,
            'damage_description': self.damage_description,
            'damage_amount': self.damage_amount,
            'painted_damage_image': self.painted_damage_image,
            'customer_signature': self.customer_signature,
            'company_signature': self.company_signature,
            'signature_date': fields.Datetime.now() if self.customer_signature else False,
            'notes': self.notes,
        })

        # 2. Registrar la lectura final del odómetro en la ficha del vehículo
        self.env['fleet.vehicle.odometer'].create({
            'vehicle_id': self.vehicle_id.id,
            'value': self.odometer,
            'date': self.return_date,
        })

        # 3. Liberar el vehículo y actualizar el contrato
        self.vehicle_id.write({'status': 'available'})
        contract.write({'last_odometer': self.odometer})
        if self.has_damage:
            contract.write({
                'damage_amount': self.damage_amount,
                'description': self.damage_description,
            })

        # 4. Cambiar el estado del contrato a devuelto
        contract._apply_return()

        # 5. Generar el acta y adjuntarla al chatter del contrato
        acta_attachment = None
        report = self.env.ref('vehicle_rental.action_report_vehicle_contract_return')
        pdf_content, _dummy = report.sudo()._render_qweb_pdf(
            report.report_name, res_ids=return_record.ids
        )
        if pdf_content:
            acta_attachment = self.env['ir.attachment'].create({
                'name': return_record.acta_filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'vehicle.contract',
                'res_id': contract.id,
                'mimetype': 'application/pdf',
            })
            return_record.write({
                'acta_generated': True,
                'acta_pdf': base64.b64encode(pdf_content),
            })

        # 6. Postear el resumen en el chatter del contrato
        message_body = self._build_chatter_message(return_record)
        if acta_attachment:
            contract.message_post(
                body=message_body,
                attachment_ids=[acta_attachment.id]
            )
        else:
            contract.message_post(body=message_body)

        # 7. Facturar los daños si se solicitó
        if self.has_damage and self.invoice_damage_now and self.damage_amount > 0:
            return_record.action_create_damage_invoice()

        # 8. Enviar al cliente el correo de cierre con el resumen del proceso
        if self.send_closing_email:
            attachment_ids = [acta_attachment.id] if acta_attachment else None
            sent = return_record.action_send_return_email(extra_attachment_ids=attachment_ids)
            if not sent:
                contract.message_post(
                    body=_('No se pudo enviar el email de cierre: el cliente no tiene '
                           'dirección de correo configurada.')
                )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrato de Alquiler'),
            'res_model': 'vehicle.contract',
            'res_id': contract.id,
            'view_mode': 'form',
            'target': 'current',
        }
