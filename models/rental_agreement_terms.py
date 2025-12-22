# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class RentalAgreementTerms(models.Model):
    """Rental Agreement Terms"""
    _name = 'rental.agreement.terms'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Title")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    rental_terms = fields.Html(string="Terms and Conditions")
