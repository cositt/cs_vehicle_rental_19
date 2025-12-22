# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class CancellationPolicy(models.Model):
    """Cancellation Policy"""
    _name = 'cancellation.policy'
    _description = __doc__
    _rec_name = 'title'

    title = fields.Char(string="Title", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    terms_and_conditions = fields.Html(string="Terms and Conditions")

    # DEPRECATED
    created_on = fields.Date(string="Created On")
