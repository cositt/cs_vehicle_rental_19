# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class MaintenanceSchedule(models.Model):
    """Maintenance Schedule"""
    _name = 'maintenance.schedule'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    maintenance_days = fields.Integer(string="Maintenance Days")
    # Shared by every company unless one is set: Sunset and Pinveco use the same intervals
    company_id = fields.Many2one('res.company')

    @api.constrains('maintenance_days')
    def _check_maintenance_days(self):
        """Check maintenance days"""
        for record in self:
            if record.maintenance_days <= 0:
                raise ValidationError(_("Please add a Maintenance Days greater than zero."))
