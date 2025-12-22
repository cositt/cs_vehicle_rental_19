# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class VehicleScratchReport(models.Model):
    """Vehicle Scratch Report"""
    _name = 'vehicle.scratch.report'
    _description = __doc__
    _rec_name = 'vehicle_id'

    name = fields.Char(string="Name")
    avatar = fields.Binary(string="Avatar")
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
