# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VehicleSubstitutionWizard(models.TransientModel):
    """Wizard para realizar la sustitución de un vehículo en un contrato activo"""
    _name = 'vehicle.substitution.wizard'
    _description = 'Asistente de Sustitución de Vehículo'

    # Información general
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
    
    # Paso actual del wizard
    step = fields.Selection([
        ('1_old_vehicle', 'Paso 1: Inspección Vehículo Actual'),
        ('2_select_new', 'Paso 2: Seleccionar Vehículo Sustituto'),
        ('3_new_vehicle', 'Paso 3: Inspección Vehículo Sustituto'),
        ('4_confirm', 'Paso 4: Confirmación y Documentos')
    ], string='Paso', default='1_old_vehicle', required=True)
    
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
    ], string='Motivo de Sustitución', required=True, default='breakdown')
    
    reason_notes = fields.Text(string='Notas del Motivo')
    
    # === VEHÍCULO ORIGINAL (Devolución) ===
    old_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Actual',
        compute='_compute_old_vehicle',
        store=True,
        readonly=True
    )
    old_vehicle_license_plate = fields.Char(
        string='Matrícula',
        related='old_vehicle_id.license_plate',
        readonly=True
    )
    old_vehicle_odometer = fields.Float(
        string='Kilometraje de Devolución',
        required=False,  # Se calculará automáticamente en _compute_old_vehicle
    )
    old_vehicle_fuel_level = fields.Selection([
        ('0', 'Vacío'),
        ('1', '1/4'),
        ('2', '2/4 (Medio)'),
        ('3', '3/4'),
        ('4', 'Lleno')
    ], string='Nivel de Combustible', required=True, default='2')
    
    old_vehicle_has_damage = fields.Boolean(
        string='¿El vehículo tiene daños?',
        default=False
    )
    old_vehicle_damage_description = fields.Html(
        string='Descripción de Daños'
    )
    old_vehicle_damage_amount = fields.Monetary(
        string='Monto Estimado de Daños',
        currency_field='currency_id'
    )
    old_vehicle_painted_damage_image = fields.Binary(
        string='Imagen de Daños Pintada'
    )
    
    # === VEHÍCULO NUEVO (Entrega) ===
    new_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Sustituto',
        domain="[('status', '=', 'available'), ('id', '!=', old_vehicle_id), ('id', 'in', available_vehicle_ids)]"
    )
    available_vehicle_ids = fields.Many2many(
        'fleet.vehicle',
        compute='_compute_available_vehicles',
        store=False,
        string='Vehículos Disponibles'
    )
    new_vehicle_license_plate = fields.Char(
        string='Matrícula Sustituto',
        related='new_vehicle_id.license_plate',
        readonly=True
    )
    new_vehicle_category_id = fields.Many2one(
        'fleet.vehicle.model.category',
        string='Categoría',
        related='new_vehicle_id.category_id',
        readonly=True
    )
    new_vehicle_odometer = fields.Float(
        string='Kilometraje de Entrega',
        compute='_compute_new_vehicle_odometer',
        store=True,
        readonly=False
    )
    new_vehicle_fuel_level = fields.Selection([
        ('0', 'Vacío'),
        ('1', '1/4'),
        ('2', '2/4 (Medio)'),
        ('3', '3/4'),
        ('4', 'Lleno')
    ], string='Nivel de Combustible', default='4')
    
    new_vehicle_has_damage = fields.Boolean(
        string='¿El vehículo tiene daños previos?',
        default=False
    )
    new_vehicle_damage_description = fields.Html(
        string='Descripción de Daños Previos'
    )
    new_vehicle_painted_damage_image = fields.Binary(
        string='Imagen de Daños Pintada'
    )
    
    # === DIFERENCIA DE PRECIO ===
    old_vehicle_rent = fields.Monetary(
        string='Tarifa Vehículo Actual',
        related='contract_id.rent',
        readonly=True
    )
    new_vehicle_rent = fields.Monetary(
        string='Tarifa Vehículo Sustituto',
        compute='_compute_new_vehicle_rent',
        store=True
    )
    has_price_difference = fields.Boolean(
        string='¿Hay diferencia de precio?',
        compute='_compute_price_difference',
        store=True
    )
    price_difference = fields.Monetary(
        string='Diferencia de Precio',
        compute='_compute_price_difference',
        store=True,
        help='Positivo = cliente debe pagar más, Negativo = devolución al cliente'
    )
    apply_price_difference = fields.Boolean(
        string='Aplicar diferencia de precio al contrato',
        default=True
    )
    
    # === DOCUMENTACIÓN ===
    generate_addendum = fields.Boolean(
        string='Generar Addendum al Contrato',
        default=True
    )
    customer_signature = fields.Binary(string='Firma del Cliente')
    company_signature = fields.Binary(string='Firma de la Empresa')
    
    # Campos auxiliares
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
    def _compute_available_vehicles(self):
        """Calcular vehículos disponibles en el período del contrato"""
        for wizard in self:
            available_ids = []
            
            if wizard.contract_id and wizard.contract_id.start_date and wizard.contract_id.end_date:
                # Obtener todos los vehículos operacionales
                all_vehicles = self.env['fleet.vehicle'].search([
                    ('status', '=', 'available'),
                    ('id', '!=', wizard.old_vehicle_id.id if wizard.old_vehicle_id else False)
                ])
                
                # Filtrar los que NO tienen contratos superpuestos en el período
                for vehicle in all_vehicles:
                    overlapping_contracts = self.env['vehicle.contract'].search([
                        ('vehicle_id', '=', vehicle.id),
                        ('status', 'in', ['a_draft', 'b_in_progress']),  # Contratos activos o en borrador
                        ('id', '!=', wizard.contract_id.id),  # Excluir el contrato actual
                        '|',
                        '&', ('start_date', '<=', wizard.contract_id.end_date),
                             ('end_date', '>=', wizard.contract_id.start_date),
                        '&', ('start_date', '<=', wizard.contract_id.start_date),
                             ('end_date', '>=', wizard.contract_id.end_date),
                    ])
                    
                    # Si NO hay contratos superpuestos, el vehículo está disponible
                    if not overlapping_contracts:
                        available_ids.append(vehicle.id)
            
            wizard.available_vehicle_ids = [(6, 0, available_ids)]
    
    @api.depends('contract_id', 'contract_id.vehicle_id', 'contract_id.substitution_ids')
    def _compute_old_vehicle(self):
        """Obtener el vehículo actualmente asignado (considerando sustituciones previas)"""
        for wizard in self:
            if wizard.contract_id:
                # Si hay sustituciones previas, tomar el último vehículo sustituto
                if wizard.contract_id.substitution_ids:
                    last_sub = wizard.contract_id.substitution_ids.sorted('substitution_date', reverse=True)[0]
                    wizard.old_vehicle_id = last_sub.new_vehicle_id
                else:
                    # Si no hay sustituciones, usar el vehículo original del contrato
                    wizard.old_vehicle_id = wizard.contract_id.vehicle_id
                    
                # Obtener el último odómetro conocido del contrato
                if wizard.contract_id.last_odometer:
                    wizard.old_vehicle_odometer = wizard.contract_id.last_odometer
                elif wizard.old_vehicle_id and wizard.old_vehicle_id.odometer:
                    wizard.old_vehicle_odometer = wizard.old_vehicle_id.odometer
                else:
                    wizard.old_vehicle_odometer = 0.0
    
    @api.depends('new_vehicle_id')
    def _compute_new_vehicle_odometer(self):
        """Obtener el último odómetro del vehículo sustituto"""
        for wizard in self:
            if wizard.new_vehicle_id and wizard.new_vehicle_id.odometer:
                wizard.new_vehicle_odometer = wizard.new_vehicle_id.odometer
            else:
                wizard.new_vehicle_odometer = 0.0
    
    @api.depends('new_vehicle_id')
    def _compute_new_vehicle_rent(self):
        """Calcular la tarifa del nuevo vehículo basado en su categoría"""
        for wizard in self:
            if wizard.new_vehicle_id and wizard.new_vehicle_id.category_id:
                # Aquí podrías tener una tarifa por categoría
                # Por ahora usamos la misma tarifa del contrato
                wizard.new_vehicle_rent = wizard.contract_id.rent
            else:
                wizard.new_vehicle_rent = 0.0
    
    @api.depends('old_vehicle_rent', 'new_vehicle_rent')
    def _compute_price_difference(self):
        """Calcular la diferencia de precio"""
        for wizard in self:
            wizard.price_difference = wizard.new_vehicle_rent - wizard.old_vehicle_rent
            wizard.has_price_difference = abs(wizard.price_difference) > 0.01
    
    @api.constrains('old_vehicle_odometer', 'contract_id')
    def _check_old_vehicle_odometer(self):
        """Validar que el odómetro no sea menor al registrado anteriormente"""
        for wizard in self:
            if wizard.old_vehicle_odometer and wizard.contract_id.last_odometer:
                if wizard.old_vehicle_odometer < wizard.contract_id.last_odometer:
                    raise ValidationError(
                        _('El kilometraje de devolución (%s km) no puede ser menor al último registrado (%s km)') %
                        (wizard.old_vehicle_odometer, wizard.contract_id.last_odometer)
                    )
    
    @api.constrains('new_vehicle_id', 'old_vehicle_id')
    def _check_vehicles_different(self):
        """Validar que el vehículo sustituto sea diferente al actual"""
        for wizard in self:
            if wizard.new_vehicle_id and wizard.old_vehicle_id:
                if wizard.new_vehicle_id == wizard.old_vehicle_id:
                    raise ValidationError(
                        _('El vehículo sustituto debe ser diferente al vehículo actual')
                    )
    
    # === MÉTODOS DE NAVEGACIÓN ===
    
    def action_next_step(self):
        """Avanzar al siguiente paso"""
        self.ensure_one()
        
        if self.step == '1_old_vehicle':
            # Validar que se haya completado la inspección del vehículo actual
            if not self.old_vehicle_odometer:
                raise UserError(_('Debe ingresar el kilometraje del vehículo actual'))
            if not self.old_vehicle_fuel_level:
                raise UserError(_('Debe seleccionar el nivel de combustible'))
            self.step = '2_select_new'
        
        elif self.step == '2_select_new':
            # Validar que se haya seleccionado un vehículo sustituto
            if not self.new_vehicle_id:
                raise UserError(_('Debe seleccionar un vehículo sustituto'))
            if not self.reason:
                raise UserError(_('Debe indicar el motivo de la sustitución'))
            self.step = '3_new_vehicle'
        
        elif self.step == '3_new_vehicle':
            # Validar que se haya completado la inspección del vehículo sustituto
            if not self.new_vehicle_fuel_level:
                raise UserError(_('Debe seleccionar el nivel de combustible del vehículo sustituto'))
            self.step = '4_confirm'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.substitution.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # Mantener vista completa
        }
    
    def action_previous_step(self):
        """Volver al paso anterior"""
        self.ensure_one()
        
        if self.step == '2_select_new':
            self.step = '1_old_vehicle'
        elif self.step == '3_new_vehicle':
            self.step = '2_select_new'
        elif self.step == '4_confirm':
            self.step = '3_new_vehicle'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.substitution.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',  # Mantener vista completa
        }
    
    def action_open_old_damage_painter(self):
        """Abrir editor de daños para el vehículo actual (devolución)"""
        self.ensure_one()
        # Crear wizard de damage painter
        painter_wizard = self.env['vehicle.substitution.damage.painter'].create({
            'substitution_wizard_id': self.id,
            'vehicle_id': self.old_vehicle_id.id,
            'damage_type': 'old',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Editor de Daños - Vehículo Devuelto'),
            'res_model': 'vehicle.substitution.damage.painter',
            'res_id': painter_wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_substitution_wizard_id': self.id,
                'default_vehicle_id': self.old_vehicle_id.id,
                'default_damage_type': 'old',
            },
        }
    
    def action_open_new_damage_painter(self):
        """Abrir editor de daños para el vehículo sustituto (entrega)"""
        self.ensure_one()
        if not self.new_vehicle_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _('Primero debe seleccionar un vehículo sustituto'),
                }
            }
        # Crear wizard de damage painter
        painter_wizard = self.env['vehicle.substitution.damage.painter'].create({
            'substitution_wizard_id': self.id,
            'vehicle_id': self.new_vehicle_id.id,
            'damage_type': 'new',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Editor de Daños - Vehículo Sustituto'),
            'res_model': 'vehicle.substitution.damage.painter',
            'res_id': painter_wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_substitution_wizard_id': self.id,
                'default_vehicle_id': self.new_vehicle_id.id,
                'default_damage_type': 'new',
            },
        }
    
    # === MÉTODO PRINCIPAL: CONFIRMAR SUSTITUCIÓN ===
    
    def action_confirm_substitution(self):
        """Confirmar y ejecutar la sustitución del vehículo"""
        self.ensure_one()
        
        # Validaciones finales
        if self.step != '4_confirm':
            raise UserError(_('Debe completar todos los pasos antes de confirmar'))
        
        if not self.new_vehicle_id:
            raise UserError(_('Debe seleccionar un vehículo sustituto'))
        
        # Verificar que el contrato esté en progreso
        if self.contract_id.status != 'b_in_progress':
            raise UserError(_('Solo se pueden sustituir vehículos en contratos en progreso'))
        
        # Verificar que el nuevo vehículo esté disponible
        if self.new_vehicle_id.status != 'available':
            raise UserError(_('El vehículo sustituto seleccionado no está disponible'))
        
        # Verificar que el vehículo NO tenga contratos superpuestos
        overlapping_contracts = self.env['vehicle.contract'].search([
            ('vehicle_id', '=', self.new_vehicle_id.id),
            ('status', 'in', ['a_draft', 'b_in_progress']),
            ('id', '!=', self.contract_id.id),
            '|',
            '&', ('start_date', '<=', self.contract_id.end_date),
                 ('end_date', '>=', self.contract_id.start_date),
            '&', ('start_date', '<=', self.contract_id.start_date),
                 ('end_date', '>=', self.contract_id.end_date),
        ])
        
        if overlapping_contracts:
            conflict_contracts = ', '.join(overlapping_contracts.mapped('reference_no'))
            raise UserError(_(
                'El vehículo %s NO está disponible en el período del contrato.\n'
                'Tiene contratos superpuestos: %s\n\n'
                'Por favor, seleccione otro vehículo.'
            ) % (self.new_vehicle_id.name, conflict_contracts))
        
        # 1. Crear el registro de sustitución
        substitution_vals = {
            'contract_id': self.contract_id.id,
            'substitution_date': self.substitution_date,
            'reason': self.reason,
            'reason_notes': self.reason_notes,
            
            # Vehículo original
            'old_vehicle_id': self.old_vehicle_id.id,
            'old_vehicle_odometer': self.old_vehicle_odometer,
            'old_vehicle_fuel_level': self.old_vehicle_fuel_level,
            'old_vehicle_has_damage': self.old_vehicle_has_damage,
            'old_vehicle_damage_description': self.old_vehicle_damage_description,
            'old_vehicle_damage_amount': self.old_vehicle_damage_amount,
            'old_vehicle_painted_damage_image': self.old_vehicle_painted_damage_image,
            
            # Vehículo nuevo
            'new_vehicle_id': self.new_vehicle_id.id,
            'new_vehicle_odometer': self.new_vehicle_odometer,
            'new_vehicle_fuel_level': self.new_vehicle_fuel_level,
            'new_vehicle_has_damage': self.new_vehicle_has_damage,
            'new_vehicle_damage_description': self.new_vehicle_damage_description,
            'new_vehicle_painted_damage_image': self.new_vehicle_painted_damage_image,
            
            # Diferencia de precio
            'has_price_difference': self.has_price_difference,
            'price_difference': self.price_difference if self.apply_price_difference else 0.0,
            
            # Firmas
            'customer_signature': self.customer_signature,
            'company_signature': self.company_signature,
            'signature_date': fields.Datetime.now(),
        }
        
        substitution = self.env['vehicle.contract.substitution'].create(substitution_vals)
        
        # 2. Actualizar estados de los vehículos
        # Liberar el vehículo original (vuelve a estar disponible)
        self.old_vehicle_id.write({
            'status': 'available',
        })
        
        # El nuevo vehículo ya debe estar disponible y operacional
        # No necesitamos cambiar su status ya que sigue operacional en el contrato
        
        # 3. Actualizar el odómetro del vehículo devuelto
        self.env['fleet.vehicle.odometer'].create({
            'vehicle_id': self.old_vehicle_id.id,
            'value': self.old_vehicle_odometer,
            'date': self.substitution_date,
        })
        
        # 4. Registrar el odómetro inicial del nuevo vehículo
        self.env['fleet.vehicle.odometer'].create({
            'vehicle_id': self.new_vehicle_id.id,
            'value': self.new_vehicle_odometer,
            'date': self.substitution_date,
        })
        
        # 5. Actualizar información del contrato
        # IMPORTANTE: Actualizar el vehículo del contrato al nuevo vehículo
        self.contract_id.write({
            'vehicle_id': self.new_vehicle_id.id,  # Actualizar al nuevo vehículo
            'last_odometer': self.new_vehicle_odometer,
        })
        
        # 6. Generar factura de daños si aplica
        if self.old_vehicle_has_damage and self.old_vehicle_damage_amount > 0:
            substitution.action_create_damage_invoice()
        
        # 7. Generar factura de diferencia de precio si aplica
        if self.has_price_difference and self.apply_price_difference and abs(self.price_difference) > 0:
            substitution.action_create_price_difference_invoice()
        
        # 8. Generar addendum si se solicitó
        addendum_attachment = None
        if self.generate_addendum:
            substitution.action_generate_addendum()
            # Obtener el PDF del addendum para adjuntarlo al chatter
            if substitution.addendum_pdf:
                addendum_attachment = self.env['ir.attachment'].create({
                    'name': substitution.addendum_filename or f'Addendum_Sustitucion_{self.contract_id.reference_no}.pdf',
                    'type': 'binary',
                    'datas': substitution.addendum_pdf,
                    'res_model': 'vehicle.contract',
                    'res_id': self.contract_id.id,
                    'mimetype': 'application/pdf',
                })
        
        # 9. Enviar mensaje al chatter del contrato con formato limpio
        from markupsafe import Markup
        
        reason_label = dict(self._fields['reason'].selection).get(self.reason, self.reason)
        date_str = self.substitution_date.strftime('%d/%m/%Y %H:%M')
        
        price_row = ''
        if self.has_price_difference and self.apply_price_difference:
            price_row = Markup('''
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Diferencia de precio:</td>
                        <td style="padding: 5px;">%s %s</td>
                    </tr>
            ''') % (f"{self.price_difference:,.2f}", self.currency_id.symbol)
        
        # Agregar enlace al addendum/anexo
        substitution_link = Markup('''
                    <tr>
                        <td colspan="2" style="padding: 10px 5px; text-align: center;">
                            <a href="/web#id=%s&model=vehicle.contract.substitution&view_type=form" 
                               style="color: #007bff; text-decoration: none; font-weight: bold;">
                                <i class="fa fa-file-text-o"></i> Ver Addendum/Anexo
                            </a>
                        </td>
                    </tr>
        ''') % substitution.id
        
        message_body = Markup('''
            <div style="padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px;">
                <h4 style="color: #155724; margin: 0 0 10px 0;">
                    <i class="fa fa-check-circle"></i> Sustitución de Vehículo Realizada
                </h4>
                <table style="width: 100%%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; font-weight: bold; width: 40%%;">Fecha:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Motivo:</td>
                        <td style="padding: 5px;">%s</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 5px; font-weight: bold;">Vehículo anterior:</td>
                        <td style="padding: 5px;">%s (%s)</td>
                    </tr>
                    <tr style="background-color: #d1f2eb;">
                        <td style="padding: 5px; font-weight: bold;">Vehículo sustituto:</td>
                        <td style="padding: 5px;">%s (%s)</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; font-weight: bold;">Kilometraje:</td>
                        <td style="padding: 5px;">%s km → %s km</td>
                    </tr>
                    %s
                    %s
                </table>
            </div>
        ''') % (
            date_str,
            reason_label,
            self.old_vehicle_id.name, self.old_vehicle_id.license_plate,
            self.new_vehicle_id.name, self.new_vehicle_id.license_plate,
            f"{self.old_vehicle_odometer:,.0f}", f"{self.new_vehicle_odometer:,.0f}",
            price_row,
            substitution_link
        )
        
        # Enviar mensaje con o sin adjunto del addendum
        if addendum_attachment:
            self.contract_id.message_post(
                body=message_body,
                attachment_ids=[addendum_attachment.id]
            )
        else:
            self.contract_id.message_post(body=message_body)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrato de Alquiler'),
            'res_model': 'vehicle.contract',
            'res_id': self.contract_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

