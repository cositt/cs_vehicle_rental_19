# -*- coding: utf-8 -*-
"""Deposits to 560000 "Fianzas recibidas a corto plazo".

A deposit is owed back to the customer, it is not income; it was booked on
the income account of the company (700000, then 705000). This covers the
deposit product of the module and the "FIANZA" product created by hand. The
customer invoice lines booked so far are test data (Juan, 2026-10-23) and move
too.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

DEPOSITS = '560000'


def _account(env, company, code):
    return env['account.account'].with_company(company).search([
        ('code', '=', code), ('company_ids', 'in', company.ids)], limit=1)


def _deposit_products(env):
    module_product = env.ref('vehicle_rental.vehicle_rent_deposit', raise_if_not_found=False)
    by_hand = env['product.product'].with_context(active_test=False).search([('name', '=ilike', 'fianza')])
    return (module_product or env['product.product']) | by_hand


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    products = _deposit_products(env)
    if not products:
        return
    for company in env['res.company'].search([]):
        deposits = _account(env, company, DEPOSITS)
        if not deposits:
            continue
        products.product_tmpl_id.with_company(company).property_account_income_id = deposits
        env.flush_all()
        cr.execute("""
            UPDATE account_move_line l SET account_id = %s
              FROM account_move m
             WHERE m.id = l.move_id AND l.company_id = %s AND l.product_id IN %s
               AND l.account_id != %s AND m.move_type IN ('out_invoice', 'out_refund')
        """, (deposits.id, company.id, tuple(products.ids), deposits.id))
        _logger.info("vehicle_rental: %s: deposits to %s, %s invoice lines", company.name, DEPOSITS, cr.rowcount)
    env.invalidate_all()
