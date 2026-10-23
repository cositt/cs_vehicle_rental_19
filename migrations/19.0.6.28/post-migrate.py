# -*- coding: utf-8 -*-
"""Reload the Spanish translations of the module over the existing ones.

A module update keeps translations already in the database, so labels fixed
in i18n/es.po ("Conductora" -> "Conductor", English labels) never reached
the screens.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    if env['res.lang']._lang_get('es_ES'):
        env['ir.module.module'].search([('name', '=', 'vehicle_rental')])._load_module_terms(
            ['vehicle_rental'], ['es_ES'], overwrite=True)
