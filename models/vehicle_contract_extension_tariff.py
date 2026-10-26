# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class VehicleContractExtensionTariff(models.Model):
    """An extension re-prices the whole rental with the band of its new length.

    Jesús Muñoz, 2026-10-22: 2 days at 97 €/day extended to 3 must cost 3 x 85 €
    (band 3-5 days), so only 255 - 194 = 61 € are missing. The extension kept
    97 €/day and charged the 21,5 hours between 10:30 and 08:00 as 0,9 days.
    Days are calendar days, the same way the contract counts them.
    """
    _inherit = 'vehicle.contract.extension'

    contract_days = fields.Float(
        string='Días ya contratados', compute='_compute_extension_days', store=True)
    charged_amount = fields.Monetary(
        string='Importe ya contratado', currency_field='currency_id',
        compute='_compute_extension_amount', store=True,
        help='Días ya contratados por la tarifa del contrato.')
    daily_rate = fields.Monetary(
        help='Tarifa por día de todo el alquiler con la nueva duración. Se propone la '
             'del tramo de días que corresponde; se puede cambiar.')
    extension_amount = fields.Monetary(
        help='Lo que falta por cobrar: todos los días a la nueva tarifa, menos lo ya contratado.')

    @api.depends('original_end_date', 'contract_id.end_date', 'contract_id.start_date', 'new_end_date')
    def _compute_extension_days(self):
        for rec in self:
            base_end_date = rec._get_base_end_date()
            start = rec.contract_id.start_date
            rec.contract_days = (base_end_date.date() - start.date()).days if base_end_date and start else 0.0
            if base_end_date and rec.new_end_date and rec.new_end_date > base_end_date:
                days = (rec.new_end_date.date() - base_end_date.date()).days
                # Later the same day: no calendar day to count, keep the hours
                rec.extension_days = days or (rec.new_end_date - base_end_date).total_seconds() / (24.0 * 3600)
            else:
                rec.extension_days = 0.0

    @api.depends('extension_days', 'contract_days', 'daily_rate', 'contract_id.rent')
    def _compute_extension_amount(self):
        for rec in self:
            rec.charged_amount = rec.contract_days * (rec.contract_id.rent or 0.0)
            total = (rec.contract_days + rec.extension_days) * (rec.daily_rate or 0.0)
            rec.extension_amount = max(total - rec.charged_amount, 0.0)

    def _tariff_daily_rate(self):
        """Rate of the band for the total days after the extension, or False."""
        self.ensure_one()
        contract = self.contract_id
        if contract.pricing_type == 'flexirent' or not contract.km_range or not contract.vehicle_id:
            return False
        Rule = self.env['vehicle.pricing.rule']
        band = Rule._get_duration_range_from_days(int(self.contract_days + self.extension_days))
        rental_date = contract.start_date.date() if contract.start_date else fields.Date.today()
        rule = Rule.search([
            ('vehicle_category_id', '=', contract.vehicle_id.category_id.id),
            ('pricing_type', '=', 'standard'),
            ('km_range', '=', contract.km_range),
            ('duration_range', '=', band),
            ('active', '=', True),
        ] + Rule._in_force_domain(rental_date), limit=1, order='valid_from desc')
        return rule.price_per_unit if rule else False

    @api.onchange('new_end_date')
    def _onchange_new_end_date_tariff(self):
        for rec in self:
            if rec.contract_id and rec.new_end_date:
                rec.daily_rate = rec._tariff_daily_rate() or rec.contract_id.rent

    def _extension_invoice_line_values(self):
        """One line with the missing amount, explained."""
        self.ensure_one()
        days = self.extension_days or 1.0
        name = _('Ampliación de alquiler – %(ref)s – %(days)s día(s). Total %(total)s días a %(rate)s '
                 '= %(new)s, menos %(charged)s ya contratados',
                 ref=self.contract_id.reference_no, days=round(self.extension_days, 2),
                 total=round(self.contract_days + self.extension_days, 2), rate=self.daily_rate,
                 new=round((self.contract_days + self.extension_days) * self.daily_rate, 2),
                 charged=round(self.charged_amount, 2))
        return {'name': name, 'quantity': days, 'price_unit': self.extension_amount / days}

    def action_create_extension_invoice(self):
        rate = self.daily_rate
        action = super().action_create_extension_invoice()
        # The whole rental now goes at the rate of its new length
        self.contract_id.write({'rent': rate})
        return action
