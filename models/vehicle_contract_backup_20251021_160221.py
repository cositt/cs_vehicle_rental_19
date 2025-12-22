# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from ..utils import _display_rental_notification
from odoo import models, fields, api, _


class RentalVehicleImage(models.Model):
    """Rental Vehicle Image"""
    _name = "rental.vehicle.image"
    _description = __doc__

    avatar = fields.Binary(string="Avatar")
    name = fields.Char(string="Name", required=True, translate=True, size=20)
    vehicle_contract_id = fields.Many2one('vehicle.contract', ondelete="cascade")


class VehicleDamageImage(models.Model):
    """Vehicle Damage Image"""
    _name = "vehicle.damage.image"
    _description = __doc__

    avatar = fields.Binary(string="Avatar")
    name = fields.Char(string="Name", required=True, translate=True, size=20)
    vehicle_contract_id = fields.Many2one('vehicle.contract', ondelete="cascade")


class VehicleContract(models.Model):
    """Vehicle Contract"""
    _name = 'vehicle.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = __doc__
    _rec_name = 'reference_no'

    reference_no = fields.Char(string='Reference No', required=True, readonly=True,
                               default=lambda self: _('New'), copy=False)
    vehicle_ids = fields.Many2many('fleet.vehicle', string="Vehicles",
                                   compute='_compute_available_vehicles')
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string="Vehicle", copy=False,
        domain="[('id', 'not in', vehicle_ids), ('status', '=', 'available')]")
    license_plate = fields.Char(string="License Plate")

    is_driver_required = fields.Boolean(string="Driver Required")
    driver_id = fields.Many2one('res.partner', string="Driver")
    driver_charge_type = fields.Selection([('including', "Including in rent charge"),
                                           ('excluding', "Excluding in rent charge")],
                                          string="Charges Type", default='including')
    driver_charge = fields.Monetary(string="Charges", default=1.0)

    last_odometer = fields.Float(string="Last Odometer", copy=False)
    odometer_unit = fields.Selection([('kilometers', 'km'), ('miles', 'mi')], 'Odometer Unit',
                                     default='kilometers', copy=False)
    model_year = fields.Char(string="Model", copy=False)

    fuel_type = fields.Selection([('diesel', 'Diesel'),
                                  ('gasoline', 'Gasoline'),
                                  ('full_hybrid', 'Full Hybrid'),
                                  ('plug_in_hybrid_diesel', 'Plug-in Hybrid Diesel'),
                                  ('plug_in_hybrid_gasoline', 'Plug-in Hybrid Gasoline'),
                                  ('cng', 'CNG'),
                                  ('lpg', 'LPG'),
                                  ('hydrogen', 'Hydrogen'),
                                  ('electric', 'Electric')],
                                 string="Fuel Type")
    transmission = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic')],
        string="Transmission", copy=False)
    
    vehicle_category = fields.Char(string="Categoría del Vehículo", compute='_compute_vehicle_category', store=True)

    customer_id = fields.Many2one("res.partner")
    customer_phone = fields.Char(string="Phone")
    customer_email = fields.Char(string="Email")
    customer_document_id = fields.Many2one("customer.documents", string="Document")
    document_count = fields.Integer(compute='_compute_document_count')

    rent_type = fields.Selection([
        ('hour', "Hours"),
        ('days', "Days"),
        ('week', "Weeks"),
        ('month', "Months"),
        ('year', "Years"),
        ('km', "Kilometers"),
        ('mi', 'Miles')
    ], string="Rent Type")
    
    pricing_type = fields.Selection([
        ('standard', "Tarifa Estándar"),
        ('flexirent', "FLEXIRENT")
    ], string="Tipo de Tarifa", default='standard')
    
    flexirent_available = fields.Boolean(
        string="FLEXIRENT Disponible",
        compute='_compute_flexirent_availability',
        help="Indica si FLEXIRENT está disponible para esta duración de alquiler"
    )
    
    flexirent_min_days = fields.Integer(
        string="Días Mínimos FLEXIRENT",
        compute='_compute_flexirent_availability',
        help="Número mínimo de días requeridos para FLEXIRENT"
    )
    total_days = fields.Float(string="Total Days", compute="_compute_total_rental_days")
    total_km = fields.Float(string="Total Kilometers", default=1)
    total_mi = fields.Float(string="Total Miles", default=1)
    rent = fields.Monetary(string="Rent")
    total_vehicle_rent = fields.Monetary(string="Total Rental Charges",
                                         compute='_compute_total_vehicle_rent')

    is_any_extra_charges = fields.Boolean(string="If any extra charges")
    total_extra_days = fields.Integer(string="Total Extra Days", default=1)
    total_extra_week = fields.Integer(string="Total Extra Weeks", default=1)
    total_extra_month = fields.Integer(string="Total Extra Months", default=1)

    total_extra_hour = fields.Integer(string="Total Extra Hours", default=1)
    total_extra_year = fields.Integer(string="Total Extra Years", default=1)

    total_extra_km = fields.Float(string="Total Extra KM", default=1)
    total_extra_mi = fields.Float(string="Total Extra Miles", default=1)
    extra_charge = fields.Monetary(string="Extra Charge")
    total_extra_charges = fields.Monetary(string="Total Extra Charges",
                                          compute='_compute_total_extra_charges')

    start_date = fields.Datetime(string="Pick-up Date", copy=False)
    pick_up_street = fields.Char(translate=True)
    pick_up_street2 = fields.Char(translate=True)
    pick_up_city = fields.Char(translate=True)
    pick_up_state_id = fields.Many2one("res.country.state", string='State',
                                       domain="[('country_id', '=?', pick_up_country_id)]")
    pick_up_country_id = fields.Many2one("res.country")
    pick_up_zip = fields.Char()

    end_date = fields.Datetime(string="Drop-off Date", copy=False)
    drop_off_street = fields.Char(translate=True)
    drop_off_street2 = fields.Char(translate=True)
    drop_off_city = fields.Char(translate=True)
    drop_off_state_id = fields.Many2one("res.country.state", string=' State',
                                        domain="[('country_id', '=?', drop_off_country_id)]")
    drop_off_country_id = fields.Many2one("res.country")
    drop_off_zip = fields.Char()

    responsible_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    cancellation_policy_id = fields.Many2one("cancellation.policy", string="Policy")
    terms_and_conditions = fields.Html(string="Terms and Conditions")
    cancellation_reason = fields.Html(string="Cancellation Reason")
    cancellation_charge = fields.Monetary(string="Cancellation Charge")
    cancellation_invoice_id = fields.Many2one('account.move')
    cancellation_invoice_state = fields.Selection(related='cancellation_invoice_id.payment_state',
                                                  string="Cancellation Invoice State")

    rental_agreement_terms_id = fields.Many2one('rental.agreement.terms', string="Acuerdo de Alquiler")
    rental_terms = fields.Html()
    rental_vehicle_image_ids = fields.One2many('rental.vehicle.image', 'vehicle_contract_id')
    vehicle_damage_image_ids = fields.One2many('vehicle.damage.image', 'vehicle_contract_id')
    insurance_policy_ids = fields.One2many('insurance.policy', 'vehicle_contract_id')
    extra_service_ids = fields.One2many('extra.service', 'vehicle_contract_id')
    extra_service_charge = fields.Monetary(compute="_compute_total_extra_service_charge",
                                           store=True)

    description = fields.Html(string="Description")
    damage_amount = fields.Monetary(string="Damage Amount")
    painted_damage_image = fields.Binary(string="Imagen de Daños Pintada")
    
    # Sustituciones de vehículos
    substitution_ids = fields.One2many(
        'vehicle.contract.substitution',
        'contract_id',
        string='Sustituciones de Vehículo'
    )
    substitution_count = fields.Integer(
        string='Número de Sustituciones',
        compute='_compute_substitution_count'
    )
    current_vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo Actual',
        compute='_compute_current_vehicle',
        help='El vehículo actualmente asignado al contrato (considerando sustituciones)'
    )

    def open_damage_painter(self):
        """Abrir ventana para pintar daños"""
        self.ensure_one()
        # Crear el wizard primero para tener un res_id
        wizard = self.env['vehicle.contract.damage.painter'].create({
            'contract_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Editor de Daños del Vehículo',
            'res_model': 'vehicle.contract.damage.painter',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'active_id': self.id,  # ID del contrato como active_id
            },
        }

    def clear_damage_image(self):
        """Limpiar imagen de daños"""
        self.painted_damage_image = False
        return True

    @api.depends('substitution_ids')
    def _compute_substitution_count(self):
        """Compute substitution count"""
        for rec in self:
            rec.substitution_count = len(rec.substitution_ids)

    @api.depends('vehicle_id', 'substitution_ids', 'substitution_ids.new_vehicle_id')
    def _compute_current_vehicle(self):
        """Compute current vehicle considering substitutions"""
        for rec in self:
            # Si hay sustituciones, tomar el último vehículo sustituto
            if rec.substitution_ids:
                last_substitution = rec.substitution_ids.sorted('substitution_date', reverse=True)[0]
                rec.current_vehicle_id = last_substitution.new_vehicle_id
            else:
                # Si no hay sustituciones, usar el vehículo original
                rec.current_vehicle_id = rec.vehicle_id

    @api.depends('vehicle_id', 'vehicle_id.category_id')
    def _compute_vehicle_category(self):
        """Compute vehicle category"""
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.category_id:
                rec.vehicle_category = rec.vehicle_id.category_id.name
            else:
                rec.vehicle_category = False

    @api.depends('vehicle_id', 'vehicle_id.category_id', 'total_days')
    def _compute_flexirent_availability(self):
        """Compute FLEXIRENT availability based on minimum days required"""
        for rec in self:
            rec.flexirent_available = False
            rec.flexirent_min_days = 0
            
            if rec.vehicle_id and rec.vehicle_id.category_id and rec.total_days:
                # Buscar la tarifa FLEXIRENT con menor duración para esta categoría
                pricing_rules = self.env['vehicle.pricing.rule'].search([
                    ('vehicle_category_id', '=', rec.vehicle_id.category_id.id),
                    ('pricing_type', '=', 'flexirent'),
                    ('active', '=', True)
                ], order='flexirent_duration_days asc', limit=1)
                
                if pricing_rules:
                    min_days = pricing_rules.flexirent_duration_days
                    rec.flexirent_min_days = min_days
                    rec.flexirent_available = rec.total_days >= min_days
                    
                    # Si FLEXIRENT no está disponible y está seleccionado, cambiar a standard
                    if not rec.flexirent_available and rec.pricing_type == 'flexirent':
                        rec.pricing_type = 'standard'

    def action_open_substitution_wizard(self):
        """Abrir wizard de sustitución de vehículo"""
        self.ensure_one()
        # Crear el wizard primero
        wizard = self.env['vehicle.substitution.wizard'].create({
            'contract_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sustitución de Vehículo'),
            'res_model': 'vehicle.substitution.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'current',  # Vista completa, NO modal
            'context': {
                'default_contract_id': self.id,
            },
        }

    def action_view_substitutions(self):
        """Ver todas las sustituciones del contrato"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sustituciones de Vehículo'),
            'res_model': 'vehicle.contract.substitution',
            'domain': [('contract_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'default_contract_id': self.id,
            },
        }

    tax_ids = fields.Many2many('account.tax', string='Taxes')
    invoice_id = fields.Many2one('account.move')
    is_invoice_done = fields.Boolean()
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    status = fields.Selection([
        ('a_draft', 'New'),
        ('b_in_progress', 'In Progress'),
        ('c_return', 'Return'),
        ('d_cancel', 'Cancel')],
        default="a_draft", copy=False)
    if_any_deposit = fields.Boolean()
    deposit = fields.Monetary(string="Deposit")
    deposit_invoice_id = fields.Many2one('account.move', string="Deposit Invoice")
    deposit_payment_state = fields.Selection(related="deposit_invoice_id.payment_state",
                                             string=" Payment State")

    return_deposit_invoice_id = fields.Many2one('account.move', string="Return Deposit Invoice")
    return_deposit_state = fields.Selection(related="return_deposit_invoice_id.payment_state",
                                            string="Return Payment State")

    date = fields.Date(string="Date")
    signature = fields.Binary(string="Signature")

    payment_type = fields.Selection(
        [('daily', "Daily"),
         ('weekly', "Weekly"),
         ('monthly', "Monthly"),
         ('quarterly', "Quarterly"),
         ('yearly', "Yearly"),
         ('full_payment', "Full Payment")],
        string="Payment Type")
    vehicle_payment_option_ids = fields.One2many('vehicle.payment.option', 'vehicle_contract_id')
    invoice_item_id = fields.Many2one(
        'product.product', string="Invoice Item", required=True,
        default=lambda self: self.env.ref('vehicle_rental.vehicle_rent_charge',
                                          raise_if_not_found=False))
    installment_created = fields.Boolean()
    extra_charge_invoice_id = fields.Many2one('account.move', string="Extra Charge Invoice")
    extra_charge_payment_state = fields.Selection(related='extra_charge_invoice_id.payment_state',
                                                  string="Extra Charge Payment State")
    extra_service_invoice_id = fields.Many2one('account.move', string="Extra Service Invoice")
    payment_state = fields.Selection(related="extra_service_invoice_id.payment_state",
                                     string="Payment State")

    is_scratch_report = fields.Boolean(string="Custom Scratch Report")
    vehicle_scratch_report_id = fields.Many2one('vehicle.scratch.report',
                                                string="Scratch Report")

    # Contract Expanses
    is_any_trip_expense = fields.Boolean()
    contract_expense_ids = fields.One2many(comodel_name='hr.expense',
                                           inverse_name='vehicle_contract_id')
    crm_lead_id = fields.Many2one('crm.lead', string="Lead")

    # DEPRECATED
    total_day_rent = fields.Monetary()
    total_km_rent = fields.Monetary()
    total_mi_rent = fields.Monetary()

    account_payment_id = fields.Many2one('account.payment', string="Deposit Payment")
    account_payment_state = fields.Selection(related='account_payment_id.state',
                                             string="Account Payment State")
    journal_id = fields.Many2one('account.journal', domain=[('type', 'in', ('bank', 'cash'))],
                                 string="Deposit Journal")

    @api.model_create_multi
    def create(self, vals_list):
        """Create vehicle contract record"""
        # Llenar ubicaciones con datos de la compañía si no están ya definidos
        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            company = self.env['res.company'].browse(company_id)
            
            # Llenar pick-up si no están definidos
            if not vals.get('pick_up_street') and company.street:
                vals['pick_up_street'] = company.street
            if not vals.get('pick_up_street2') and company.street2:
                vals['pick_up_street2'] = company.street2
            if not vals.get('pick_up_city') and company.city:
                vals['pick_up_city'] = company.city
            if not vals.get('pick_up_state_id') and company.state_id:
                vals['pick_up_state_id'] = company.state_id.id
            if not vals.get('pick_up_country_id') and company.country_id:
                vals['pick_up_country_id'] = company.country_id.id
            if not vals.get('pick_up_zip') and company.zip:
                vals['pick_up_zip'] = company.zip
            
            # Llenar drop-off si no están definidos
            if not vals.get('drop_off_street') and company.street:
                vals['drop_off_street'] = company.street
            if not vals.get('drop_off_street2') and company.street2:
                vals['drop_off_street2'] = company.street2
            if not vals.get('drop_off_city') and company.city:
                vals['drop_off_city'] = company.city
            if not vals.get('drop_off_state_id') and company.state_id:
                vals['drop_off_state_id'] = company.state_id.id
            if not vals.get('drop_off_country_id') and company.country_id:
                vals['drop_off_country_id'] = company.country_id.id
            if not vals.get('drop_off_zip') and company.zip:
                vals['drop_off_zip'] = company.zip
        
        records = super().create(vals_list)
        for record in records:
            if record.reference_no == _('New'):
                record.reference_no = self.env['ir.sequence'].next_by_code('vehicle.contract') or _(
                    'New')
        return records

    @api.constrains('start_date', 'end_date', 'rent_type')
    def _check_date_rent_type(self):
        """Check rent type"""
        rent_min_days = {
            'week': 7,
            'month': 28,
            'year': 365,
        }
        for rec in self:
            if rec.start_date and rec.end_date:
                diff_days = (rec.end_date - rec.start_date).days
                min_days = rent_min_days.get(rec.rent_type)
                if min_days and diff_days < min_days:
                    raise ValidationError(
                        f"Rent Type '{rec.rent_type.capitalize()}' "
                        f"requires at least {min_days} days duration.")

    @api.constrains('rent_type', 'rent')
    def _validate_non_positive_values(self):
        """Validate rent is greater than zero based on rent type"""
        type_labels = {
            'hour': _("Hour"),
            'days': _("Day"),
            'week': _("Week"),
            'month': _("Month"),
            'year': _("Year"),
            'km': _("KM"),
            'mi': _("MI"),
        }
        for record in self:
            if record.rent_type in type_labels and record.rent <= 0:
                raise ValidationError(
                    _("The Rent per %s must be greater than zero.") % type_labels[record.rent_type])

    def a_draft_to_b_in_progress(self):
        """Change status from draft to in-progress."""
        for rec in self:
            # Validate if rental type is selected
            if not rec.rent_type:
                message = _display_rental_notification(
                    message="""Elija su unidad de alquiler preferida (horas, días, semanas,
                     meses, años, kilómetros o millas) y proceda en consecuencia.""",
                    message_type='warning')
                return message
            vehicle_id = rec.vehicle_id.id
            # Check for existing in-progress contracts for the same vehicle
            existing_contract = self.env['vehicle.contract'].search(
                [('vehicle_id', '=', vehicle_id),
                 ('status', '=', 'b_in_progress')], limit=1)
            if existing_contract:
                message = _display_rental_notification(
                    message="""Ya existe un contrato en ejecución para este vehículo. Por favor
                     devuelva el coche antes de seleccionar un nuevo contrato.""",
                    message_type='warning')
                return message
            # Proceed to update status and prepare email context
            rec.ensure_one()
            template_id = self.env.ref("vehicle_rental.vehicle_rental_booking_mail_template").sudo()
            email_context = {
                'default_model': 'vehicle.contract',
                'default_res_ids': rec.ids,
                'default_partner_ids': [rec.customer_id.id],
                'default_use_template': bool(template_id),
                'default_template_id': template_id.id,
                'default_composition_mode': 'comment',
                'default_email_from': self.env.company.email,
                'default_reply_to': self.env.company.email,
                'custom_layout': False,
                'force_email': True,
            }
            rec.status = 'b_in_progress'
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(False, 'form')],
                'view_id': False,
                'target': 'new',
                'context': email_context,
            }
        return True

    def b_in_progress_to_c_return(self):
        """In progress to return"""
        self.status = 'c_return'

    def c_return_to_d_cancel(self):
        """Return to cancel"""
        self.status = 'd_cancel'

    def action_vehicle_rent_deposit(self):
        """Handle vehicle rent deposit process."""
        if self.if_any_deposit and not self.deposit:
            message = _display_rental_notification(
                message="""Por favor, tenga en cuenta: Se requiere un depósito para el vehículo alquilado.""",
                message_type='warning')
            return message
        if self.if_any_deposit and self.deposit:
            invoice_lines = []
            invoice_line_vals = {
                'product_id': self.env.ref('vehicle_rental.vehicle_rent_deposit').id,
                'name': f"Deposit for - {self.reference_no} - {self.vehicle_id.name}",
                'quantity': 1,
                'price_unit': self.deposit,
            }
            invoice_lines.append((0, 0, invoice_line_vals))
            data = {
                'partner_id': self.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'vehicle_contract_id': self.id
            }
            deposit_invoice_id = self.env['account.move'].sudo().create(data)
            self.deposit_invoice_id = deposit_invoice_id.id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Deposit Invoice'),
                'res_model': 'account.move',
                'res_id': deposit_invoice_id.id,
                'view_mode': 'form',
                'target': 'current'
            }
        return True

    @api.constrains('start_date')
    def _check_start_date(self):
        """Check start date"""
        today = fields.Datetime.now()
        for record in self:
            if record.start_date and record.start_date < today:
                raise ValidationError(
                    _("Ensure start date is greater than or equal to today's date."))

    @api.constrains('date')
    def _check_date(self):
        """Check that the sign date is not before today"""
        today = fields.Date.today()
        for record in self:
            if record.date and record.date < today:
                raise ValidationError(_("The sign date cannot be earlier than today."))

    @api.onchange('start_date', 'end_date')
    def get_vehicle_select(self):
        """Vehicle select"""
        for rec in self:
            if not rec.start_date or not rec.end_date:
                rec.vehicle_id = False

    def vehicle_details_update(self):
        """Update vehicle details"""
        if self.vehicle_id:
            if self.last_odometer <= self.vehicle_id.odometer:
                message = _display_rental_notification(
                    message="""Por favor, añada un valor de odómetro final mayor que el valor actual""",
                    message_type='warning')
                return message
            self.vehicle_id.write({
                'model_year': self.model_year,
                'transmission': self.transmission,
                'fuel_type': self.fuel_type,
                'odometer': self.last_odometer,
                'odometer_unit': self.odometer_unit,
            })
        return True  # Ensuring consistent return values

    @api.onchange('customer_id')
    def onchange_customer_details(self):
        """Onchange customer details"""
        for rec in self:
            rec.customer_phone = rec.customer_id.phone
            rec.customer_email = rec.customer_id.email

    @api.onchange('vehicle_id')
    def onchange_vehicle_details(self):
        """Onchange vehicle details"""
        for rec in self:
            rec.driver_id = rec.vehicle_id.driver_id
            rec.last_odometer = rec.vehicle_id.odometer
            rec.odometer_unit = rec.vehicle_id.odometer_unit
            rec.model_year = rec.vehicle_id.model_year
            rec.transmission = rec.vehicle_id.transmission
            rec.fuel_type = rec.vehicle_id.fuel_type
            rec.license_plate = rec.vehicle_id.license_plate

    @api.onchange('cancellation_policy_id')
    def onchange_policy_terms(self):
        """Onchange policy terms"""
        for rec in self:
            rec.terms_and_conditions = rec.cancellation_policy_id.terms_and_conditions

    @api.onchange('rental_agreement_terms_id')
    def onchange_rental_agreement(self):
        """Onchange rental agreement"""
        for rec in self:
            rec.rental_terms = rec.rental_agreement_terms_id.rental_terms
    
    @api.onchange('company_id')
    def onchange_company_location(self):
        """Llenar ubicaciones de recogida y devolución con datos de la compañía"""
        for rec in self:
            if rec.company_id:
                # Llenar ubicación de recogida
                rec.pick_up_street = rec.company_id.street
                rec.pick_up_street2 = rec.company_id.street2
                rec.pick_up_city = rec.company_id.city
                rec.pick_up_state_id = rec.company_id.state_id
                rec.pick_up_country_id = rec.company_id.country_id
                rec.pick_up_zip = rec.company_id.zip
                
                # Llenar ubicación de devolución con los mismos datos
                rec.drop_off_street = rec.company_id.street
                rec.drop_off_street2 = rec.company_id.street2
                rec.drop_off_city = rec.company_id.city
                rec.drop_off_state_id = rec.company_id.state_id
                rec.drop_off_country_id = rec.company_id.country_id
                rec.drop_off_zip = rec.company_id.zip

    @api.constrains('total_km')
    def _check_total_km(self):
        """Ensure total kilometers are greater than zero."""
        for record in self:
            if record.total_km <= 0:
                raise ValidationError(_("The total kilometers must be greater than zero."))

    @api.constrains('total_mi')
    def _check_total_mi(self):
        """Ensure total miles are greater than zero."""
        for record in self:
            if record.total_mi <= 0:
                raise ValidationError(_("The total miles must be greater than zero."))

    @api.onchange('rent_type', 'vehicle_id')
    def onchange_vehicle_rent_details(self):
        """Onchange vehicle renta details"""
        for rec in self:
            if rec.rent_type == 'days':
                rec.rent = rec.vehicle_id.rent_day
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_day
            elif rec.rent_type == 'week':
                rec.rent = rec.vehicle_id.rent_week
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_week
            elif rec.rent_type == 'month':
                rec.rent = rec.vehicle_id.rent_month
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_month
            elif rec.rent_type == 'hour':
                rec.rent = rec.vehicle_id.rent_hour
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_hour
            elif rec.rent_type == 'year':
                rec.rent = rec.vehicle_id.rent_year
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_year
            elif rec.rent_type == 'km':
                rec.rent = rec.vehicle_id.rent_km
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_km
            elif rec.rent_type == 'mi':
                rec.rent = rec.vehicle_id.rent_mi
                if rec.is_any_extra_charges:
                    rec.extra_charge = rec.vehicle_id.extra_charge_mi

    @api.depends('extra_service_ids.amount', 'extra_service_ids.product_qty')
    def _compute_total_extra_service_charge(self):
        """Total extra service charge"""
        for rec in self:
            rec.extra_service_charge = sum(
                charge.amount * charge.product_qty for charge in rec.extra_service_ids)

    @api.depends('vehicle_id', 'start_date', 'end_date')
    def _compute_available_vehicles(self):
        """Compute available vehicles"""
        for rec in self:
            contract_id = self.env['vehicle.contract'].search(
                [('start_date', '<=', rec.end_date), ('end_date', '>=', rec.start_date),
                 ('status', '=', 'b_in_progress')]).mapped('vehicle_id').mapped('id')
            rec.vehicle_ids = contract_id

    @api.constrains('start_date', 'end_date')
    def _contract_check_dates(self):
        """Rental contract dates"""
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(
                    _("Please ensure that the Drop-off Date is greater than the Pick-up Date"))

    @api.onchange('start_date', 'end_date', 'vehicle_id')
    def _onchange_dates_vehicle(self):
        """Recalcular precios cuando cambien las fechas o el vehículo"""
        if self.start_date and self.end_date and self.vehicle_id:
            self._compute_total_rental_days()

    @api.depends('rent_type', 'pricing_type', 'start_date', 'end_date', 'vehicle_id', 'vehicle_id.category_id')
    def _compute_total_rental_days(self):
        """Total rental days"""
        for rec in self:
            rec.total_days = 0.0
            if rec.start_date and rec.end_date and rec.start_date <= rec.end_date:
                delta = rec.end_date - rec.start_date
                
                # Calcular días reales independientemente del tipo de renta
                real_days = delta.days + 1
                
                # SIEMPRE calcular días reales si hay fechas válidas
                if rec.rent_type == 'days' or rec.pricing_type == 'flexirent' or rec.rent_type == False:
                    # Para días, FLEXIRENT, o sin rent_type definido, usar días reales
                    rec.total_days = real_days
                elif rec.rent_type == 'week':
                    rec.total_days = delta.days / 7
                elif rec.rent_type == 'month':
                    delta_months = (rec.end_date.year - rec.start_date.year) * 12 + (
                            rec.end_date.month - rec.start_date.month)
                    rec.total_days = delta_months + (rec.end_date.day - rec.start_date.day) / 30
                elif rec.rent_type == 'hour':
                    rec.total_days = delta.total_seconds() / 3600
                elif rec.rent_type == 'year':
                    delta_years = rec.end_date.year - rec.start_date.year
                    remaining_months = rec.end_date.month - rec.start_date.month
                    remaining_days = (rec.end_date.day - rec.start_date.day) / 30
                    rec.total_days = delta_years + remaining_months / 12 + remaining_days / 365
                else:
                    # Si no hay rent_type definido pero hay fechas, usar días reales
                    rec.total_days = real_days
                    
                rec.total_days = round(rec.total_days, 2)
                



    @api.constrains('driver_charge')
    def _check_driver_charge(self):
        """Ensure driver charge are greater than zero."""
        for record in self:
            if record.is_driver_required:
                if record.driver_charge <= 0:
                    raise ValidationError(_("The driver charges must be greater than zero."))

    @api.depends('total_vehicle_rent', 'rent_type', 'rent', 'total_days', 'driver_charge',
                 'total_km',
                 'driver_charge_type', 'total_mi')
    def _compute_total_vehicle_rent(self):
        """Compute total vehicle rent"""
        for rec in self:
            total_vehicle_rent = 0.0
            # Calculate rent based on rent type
            rent_mapping = {
                'days': rec.total_days,
                'week': rec.total_days,
                'month': rec.total_days,
                'hour': rec.total_days,
                'year': rec.total_days,
                'km': rec.total_km,
                'mi': rec.total_mi,
            }
            if rec.rent and rec.rent_type in rent_mapping:
                total_vehicle_rent = rec.rent * rent_mapping[rec.rent_type]
            # Add driver charges if applicable
            if rec.driver_charge_type == 'excluding':
                total_vehicle_rent += rec.driver_charge
            # Set the total vehicle rent
            rec.total_vehicle_rent = round(total_vehicle_rent, 2)

    @api.depends('extra_charge', 'rent_type',
                 'total_extra_days', 'total_extra_week',
                 'total_extra_month', 'total_extra_hour',
                 'total_extra_year', 'total_extra_km',
                 'total_extra_mi')
    def _compute_total_extra_charges(self):
        """Compute total extra charge"""
        for rec in self:
            total_extra_charges = 0.0
            if rec.extra_charge and rec.rent_type:
                rent_type_map = {
                    'days': rec.total_extra_days,
                    'week': rec.total_extra_week,
                    'month': rec.total_extra_month,
                    'hour': rec.total_extra_hour,
                    'year': rec.total_extra_year,
                    'km': rec.total_extra_km,
                    'mi': rec.total_extra_mi,
                }
                total_extra_charges = rec.extra_charge * rent_type_map.get(rec.rent_type, 0.0)
            rec.total_extra_charges = total_extra_charges

    @api.constrains(
        'is_any_extra_charges', 'rent_type', 'total_extra_hour', 'total_extra_days',
        'total_extra_week', 'total_extra_month', 'total_extra_year', 'total_extra_km',
        'total_extra_mi')
    def _validate_extra_charge_positive_values(self):
        """Validate extra charge positive values"""
        for record in self:
            if not record.is_any_extra_charges:
                continue
            if record.rent_type == 'hour' and record.total_extra_hour <= 0:
                raise ValidationError(_("The total extra hours must be greater than zero."))
            elif record.rent_type == 'days' and record.total_extra_days <= 0:
                raise ValidationError(_("The total extra days must be greater than zero."))
            elif record.rent_type == 'week' and record.total_extra_week <= 0:
                raise ValidationError(_("The total extra weeks must be greater than zero."))
            elif record.rent_type == 'month' and record.total_extra_month <= 0:
                raise ValidationError(_("The total extra months must be greater than zero."))
            elif record.rent_type == 'year' and record.total_extra_year <= 0:
                raise ValidationError(_("The total extra years must be greater than zero."))
            elif record.rent_type == 'km' and record.total_extra_km <= 0:
                raise ValidationError(_("The total extra km must be greater than zero."))
            elif record.rent_type == 'mi' and record.total_extra_mi <= 0:
                raise ValidationError(_("The total extra miles must be greater than zero."))

    @api.constrains('rent_type', 'extra_charge', 'is_any_extra_charges')
    def _validate_extra_charge_values(self):
        """Validate extra charge greater than zero based on rent type"""
        type_labels = {
            'hour': _("Hour"),
            'days': _("Day"),
            'week': _("Week"),
            'month': _("Month"),
            'year': _("Year"),
            'km': _("KM"),
            'mi': _("MI"),
        }
        for record in self:
            if record.is_any_extra_charges and record.rent_type in type_labels and record.extra_charge <= 0:
                raise ValidationError(
                    _("The extra charge per %s must be greater than zero.") % type_labels[
                        record.rent_type])

    def action_create_extra_charge_invoice(self):
        """Create an extra charge invoice if applicable."""
        rent_type_mapping = {
            'days': self.total_extra_days,
            'week': self.total_extra_week,
            'month': self.total_extra_month,
            'hour': self.total_extra_hour,
            'year': self.total_extra_year,
            'km': self.total_extra_km,
            'mi': self.total_extra_mi,
        }
        # Get quantity for the selected rent type
        quantity = rent_type_mapping.get(self.rent_type, 0)
        if quantity <= 0:
            return None  # Ensure consistent return values
        # Prepare invoice line
        extra_charge_line = {
            'product_id': self.env.ref('vehicle_rental.vehicle_rent_extra_charge').id,
            'name': self.vehicle_id.name,
            'quantity': quantity,
            'price_unit': self.extra_charge,
        }
        invoice_lines = [(0, 0, extra_charge_line)]
        # Prepare invoice data
        data = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'vehicle_contract_id': self.id,
        }
        # Create and post the invoice
        extra_charge_invoice = self.env['account.move'].sudo().create(data)
        # Store the invoice reference
        self.extra_charge_invoice_id = extra_charge_invoice.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Extra Charge Invoice'),
            'res_model': 'account.move',
            'res_id': extra_charge_invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_vehicle_payment(self):
        """Create vehicle payment"""
        for rec in self:
            # Ensure payment type is selected
            if not rec.payment_type:
                message = _display_rental_notification(
                    message="""Seleccione su método de pago preferido para continuar.""",
                    message_type='warning')
                return message
            if not rec.total_vehicle_rent:
                message = _display_rental_notification(
                    message="""Por favor, totalice los cargos de alquiler que sean mayores que cero.""",
                    message_type='warning')
                return message
            # Calculate time differences
            if rec.end_date and rec.start_date:
                days_diff = rec.end_date - rec.start_date
                diff = relativedelta(rec.end_date, rec.start_date)
                total_days = days_diff.days
                total_months = (diff.years * 12) + diff.months
                total_weeks = total_days // 7
                quarter = (
                        (rec.end_date.year - rec.start_date.year) * 12
                        + rec.end_date.month - rec.start_date.month
                )
                total_quarters = quarter // 3
                year_diff = relativedelta(rec.end_date, rec.start_date)
                total_years = year_diff.years + year_diff.months / 12 + year_diff.days / 365
                amount = self.total_vehicle_rent
                # Create payment options based on the payment type
                if self.payment_type == 'full_payment':
                    payment_data = {
                        'invoice_item_id': self.invoice_item_id.id,
                        'name': 'Full Payment Invoice',
                        'payment_date': fields.Date.today(),
                        'payment_amount': amount,
                        'vehicle_contract_id': self.id,
                    }
                    self.env['vehicle.payment.option'].create(payment_data)
                elif self.payment_type == 'daily':
                    day_amount = amount / total_days if total_days else 0
                    invoice_date = self.start_date.date()
                    for i in range(total_days):
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': f'Installment {i + 1}',
                            'payment_date': invoice_date,
                            'payment_amount': day_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                        invoice_date = invoice_date + relativedelta(days=1)
                elif self.payment_type == 'monthly':
                    day_amount = amount / total_days
                    remain_amount = amount
                    invoice_date = self.start_date.date()
                    for i in range(total_months):
                        current_month_days = \
                            calendar.monthrange(invoice_date.year, invoice_date.month)[1]
                        monthly_payment_amount = current_month_days * day_amount
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': f'Installment {i + 1}',
                            'payment_date': invoice_date,
                            'payment_amount': monthly_payment_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                        invoice_date = invoice_date + relativedelta(months=1)
                        remain_amount -= monthly_payment_amount
                    # If there's remaining amount, create a last payment for the remaining balance
                    if remain_amount > 0:
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': 'Remain Days',
                            'payment_date': invoice_date,
                            'payment_amount': remain_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                elif self.payment_type == 'weekly':
                    day_amount = amount / total_days
                    remain_amount = amount
                    invoice_date = self.start_date.date()
                    for i in range(total_weeks):
                        q_end_date = invoice_date + relativedelta(days=7)
                        q_days = (q_end_date - invoice_date).days
                        weekly_payment_amount = q_days * day_amount
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': f'Installment {i + 1}',
                            'payment_date': invoice_date,
                            'payment_amount': weekly_payment_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                        invoice_date = invoice_date + relativedelta(days=7)
                        remain_amount -= weekly_payment_amount
                    # If there's remaining amount, create a last payment for the remaining balance
                    if remain_amount > 0:
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': 'Remain Days',
                            'payment_date': invoice_date,
                            'payment_amount': remain_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                elif self.payment_type == 'quarterly':
                    day_amount = amount / total_days
                    remain_amount = amount
                    start_date = self.start_date
                    for i in range(total_quarters):
                        q_end_date = start_date + relativedelta(months=3)
                        q_days = (q_end_date - start_date).days
                        quarterly_payment_amount = q_days * day_amount
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': f'Installment {i + 1}',
                            'payment_date': start_date,
                            'payment_amount': quarterly_payment_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                        start_date = q_end_date + relativedelta(days=1)
                        remain_amount -= quarterly_payment_amount
                    # If there's remaining amount, create a last payment for the remaining balance
                    if remain_amount > 0:
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': 'Remain Days',
                            'payment_date': start_date,
                            'payment_amount': remain_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                elif self.payment_type == 'yearly':
                    day_amount = amount / total_days
                    current_year = self.start_date.year
                    current_year_start_date = datetime(current_year, 1, 1)
                    current_year_end_date = datetime(current_year + 1, 1, 1)
                    number_of_days_in_current_year = (
                            current_year_end_date - current_year_start_date).days
                    full_year_amount = round(number_of_days_in_current_year * day_amount, 2)
                    remain_amount = amount
                    start_date = self.start_date
                    for i in range(int(total_years)):
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': f'Installment {i + 1}',
                            'payment_date': start_date,
                            'payment_amount': full_year_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
                        start_date = start_date + relativedelta(years=1)
                        remain_amount -= full_year_amount
                    # If there's remaining amount, create a last payment for the remaining balance
                    if remain_amount > 0:
                        payment_data = {
                            'invoice_item_id': self.invoice_item_id.id,
                            'name': 'Remain Days',
                            'payment_date': start_date,
                            'payment_amount': remain_amount,
                            'vehicle_contract_id': self.id,
                        }
                        self.env['vehicle.payment.option'].create(payment_data)
            # Mark installment creation as complete
            self.installment_created = True
        return True

    def action_create_extra_service_charge_invoice(self):
        """Action ctrate extra service charge invoice"""
        invoice_lines = []
        for record in self.extra_service_ids:
            extra_service = {
                'product_id': record.product_id.id,
                'name': record.description,
                'quantity': record.product_qty,
                'price_unit': record.amount,
            }
            invoice_lines.append((0, 0, extra_service))
        data = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'vehicle_contract_id': self.id
        }
        extra_service_invoice_id = self.env['account.move'].sudo().create(data)
        self.extra_service_invoice_id = extra_service_invoice_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Extra Service Invoice'),
            'res_model': 'account.move',
            'res_id': extra_service_invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _compute_document_count(self):
        """Compute document count"""
        for rec in self:
            rec.document_count = self.env['customer.documents'].search_count(
                [('vehicle_contract_id', '=', rec.id)])

    def action_customer_document(self):
        """Action view customer documents"""
        context = {
            'default_vehicle_contract_id': self.id,
        }
        if self.status == 'c_return':
            context['create'] = False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents'),
            'res_model': 'customer.documents',
            'domain': [('vehicle_contract_id', '=', self.id)],
            'view_mode': 'list',
            'target': 'current',
            'context': context,
        }

    def _compute_invoice_count(self):
        """Compute invoice count"""
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count(
                [('vehicle_contract_id', '=', rec.id)])

    def view_customer_invoice(self):
        """View customer invoice"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'domain': [('vehicle_contract_id', '=', self.id)],
            'context': {
                'default_vehicle_contract_id': self.id,
                'create': False,
            },
            'view_mode': 'list,form',
            'target': 'current',
        }

    def cancellation_charge_invoice(self):
        """Cancellation charge invoice"""
        invoice_line = []
        for rec in self:
            if not rec.cancellation_charge:
                message = _display_rental_notification(
                    message="""Por favor, tenga en cuenta: Se requiere un cargo por cancelación del contrato de vehículo.""",
                    message_type='warning')
                return message
            cancellation_data = {
                'product_id': self.env.ref(
                    'vehicle_rental.vehicle_contract_cancellation_charge').id,
                'name': rec.cancellation_policy_id.title,
                'quantity': 1,
                'price_unit': rec.cancellation_charge
            }
            invoice_line = [(0, 0, cancellation_data)]
        data = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_line,
            'vehicle_contract_id': self.id
        }
        cancellation_invoice_id = self.env['account.move'].sudo().create(data)
        self.cancellation_invoice_id = cancellation_invoice_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancellation Invoice'),
            'res_model': 'account.move',
            'res_id': cancellation_invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('driver_id')
    def _check_driver_is_rental_employee(self):
        """Check driver is also employee"""
        for record in self:
            if record.driver_id and not record.driver_id.employee_ids:
                raise ValidationError(
                    _("The selected driver must be one of the allowed employees."))

    def create_contract_trip_expense_report(self):
        """Create Trip Expense Reports"""
        all_draft_expenses = self.contract_expense_ids.filtered(lambda e: e.state == 'draft')
        if not all_draft_expenses:
            message = _display_rental_notification(
                message="""Todos los gastos ya han sido enviados.""",
                message_type='warning')
            return message
        all_draft_expenses.action_submit_expenses()
        message = _display_rental_notification(
            message="""Borradores de gastos enviados exitosamente.""",
            message_type='warning')
        return message

    @api.model
    def action_create_rent_payment_invoice(self):
        """Action create rent payment invoice"""
        rental_contract = self.env['vehicle.contract'].sudo().search(
            [('status', '=', 'b_in_progress')])
        today_date = fields.Date.today()
        for data in rental_contract:
            for rec in data.vehicle_payment_option_ids:
                if rec.payment_date == today_date:
                    rec.action_create_payment_invoice()
