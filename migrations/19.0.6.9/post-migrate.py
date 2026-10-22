# -*- coding: utf-8 -*-
"""Surcharges of the tariff conditions get their VAT in each company."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company'].search([])._vehicle_rental_load_surcharges()
    env.flush_all()
