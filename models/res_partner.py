# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """Datos de conductor del cliente: los lee el contrato y el conductor autorizado."""
    _inherit = 'res.partner'

    birth_date = fields.Date(string="Fecha de Nacimiento")
    driver_license_number = fields.Char(string="Carnet de Conducir", help="Número del permiso de conducir")
    driver_license_issue_date = fields.Date(string="Fecha Expedición Carnet")
    driver_license_expiry_date = fields.Date(string="Fecha Caducidad Carnet")

    @api.constrains('driver_license_issue_date', 'driver_license_expiry_date')
    def _check_driver_license_dates(self):
        for partner in self:
            issue, expiry = partner.driver_license_issue_date, partner.driver_license_expiry_date
            if issue and expiry and expiry < issue:
                raise ValidationError(_("La caducidad del carnet no puede ser anterior a su expedición."))
