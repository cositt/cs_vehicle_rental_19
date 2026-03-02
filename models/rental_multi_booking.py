# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import UserError


class RentalMultiBooking(models.Model):
    _name = 'rental.multi.booking'
    _description = 'Reserva Múltiple de Vehículos'
    _order = 'create_date desc'

    name = fields.Char(
        string='Referencia', readonly=True,
        default=lambda self: _('Borrador'))
    state = fields.Selection(
        [('draft', 'Borrador'),
         ('done', 'Completada'),
         ('cancel', 'Cancelada')],
        default='draft', string='Estado')
    customer_id = fields.Many2one('res.partner', string='Cliente', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    payment_type = fields.Selection(
        [('daily', 'Diario'),
         ('weekly', 'Semanal'),
         ('monthly', 'Mensual'),
         ('quarterly', 'Trimestral'),
         ('yearly', 'Anual'),
         ('full_payment', 'Pago Completo')],
        string='Tipo de Pago', default='full_payment')
    deposit_card_type = fields.Selection(
        [('debit', 'Tarjeta de Débito'),
         ('credit', 'Tarjeta de Crédito')],
        string='Tipo de Tarjeta', default='debit')
    notes = fields.Text(string='Observaciones')
    line_ids = fields.One2many('rental.multi.booking.line', 'booking_id', string='Vehículos')
    line_count = fields.Integer(compute='_compute_line_count')
    group_id = fields.Many2one(
        'vehicle.contract.group', string='Grupo Creado', readonly=True)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_add_vehicle(self):
        """Abre el wizard individual de reserva en modo multi-booking."""
        self.ensure_one()
        if not self.customer_id:
            raise UserError(_('Seleccione un cliente antes de añadir vehículos.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Añadir Vehículo'),
            'res_model': 'rental.contract.booking',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_customer_id': self.customer_id.id,
                'default_company_id': self.company_id.id,
                'default_multi_booking_id': self.id,
            },
        }

    def action_create_group(self):
        """Crear contrato grupo + contratos individuales por cada línea."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Añada al menos un vehículo.'))

        start_min = min(self.line_ids.mapped('start_date'))
        end_max = max(self.line_ids.mapped('end_date'))

        group = self.env['vehicle.contract.group'].create({
            'customer_id': self.customer_id.id,
            'company_id': self.company_id.id,
            'start_date': start_min,
            'end_date': end_max,
            'payment_type': self.payment_type,
            'deposit_card_type': self.deposit_card_type,
            'notes': self.notes,
        })

        for line in self.line_ids:
            self.env['vehicle.contract'].create({
                'vehicle_id': line.vehicle_id.id,
                'driver_id': line.vehicle_id.driver_id.id if line.vehicle_id.driver_id else False,
                'last_odometer': line.vehicle_id.odometer,
                'odometer_unit': line.vehicle_id.odometer_unit,
                'model_year': line.vehicle_id.model_year,
                'transmission': line.vehicle_id.transmission,
                'fuel_type': line.vehicle_id.fuel_type,
                'license_plate': line.license_plate,
                'customer_id': self.customer_id.id,
                'customer_phone': self.customer_id.phone,
                'customer_email': self.customer_id.email,
                'start_date': line.start_date,
                'end_date': line.end_date,
                'company_id': self.company_id.id,
                'rent': line.rent,
                'rent_type': 'days',
                'pricing_type': line.pricing_type,
                'payment_type': self.payment_type,
                'group_id': group.id,
                'deposit_card_type': self.deposit_card_type,
                'discount_reason': 'Reserva múltiple %s' % group.name,
            })

        self.write({'state': 'done', 'group_id': group.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contrato Grupo'),
            'res_model': 'vehicle.contract.group',
            'res_id': group.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'


class RentalMultiBookingLine(models.Model):
    _name = 'rental.multi.booking.line'
    _description = 'Línea de Reserva Múltiple'

    booking_id = fields.Many2one('rental.multi.booking', ondelete='cascade', required=True)
    company_id = fields.Many2one(related='booking_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo', required=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string='Matrícula')
    vehicle_category_id = fields.Many2one(
        related='vehicle_id.category_id', string='Categoría')

    start_date = fields.Datetime(string='Recogida', required=True)
    end_date = fields.Datetime(string='Devolución', required=True)

    pricing_type = fields.Selection(
        [('standard', 'Tarifa Estándar'),
         ('flexirent', 'FLEXIRENT')],
        string='Tipo Tarifa', default='standard')
    rent = fields.Monetary(string='Precio/día', currency_field='currency_id')

    selected_category_id = fields.Many2one(
        'fleet.vehicle.model.category', string='Categoría Seleccionada')
    duration_range = fields.Char(string='Duración')
    km_range = fields.Char(string='Rango Km')
