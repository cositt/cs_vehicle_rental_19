# -*- coding: utf-8 -*-
"""Rental income to 705000 "Prestaciones de servicios" instead of 700000.

The Spanish chart books income on 700000 "Ventas de mercaderías" by default
(company income account and sales journal). Renting a vehicle is a service.
The invoices booked so far are test data (Juan, 2026-10-23), so their customer
invoice lines move too, posted ones included.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

GOODS, SERVICES = '700000', '705000'


def _account(env, company, code):
    return env['account.account'].with_company(company).search([
        ('code', '=', code), ('company_ids', 'in', company.ids)], limit=1)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([]):
        goods, services = _account(env, company, GOODS), _account(env, company, SERVICES)
        if not (goods and services):
            continue
        if company.income_account_id == goods:
            company.income_account_id = services
        journals = env['account.journal'].search([
            ('company_id', '=', company.id), ('type', '=', 'sale'), ('default_account_id', '=', goods.id)])
        journals.default_account_id = services
        env.flush_all()
        cr.execute("""
            UPDATE account_move_line l SET account_id = %s
              FROM account_move m
             WHERE m.id = l.move_id AND l.account_id = %s AND l.company_id = %s
               AND m.move_type IN ('out_invoice', 'out_refund')
        """, (services.id, goods.id, company.id))
        _logger.info("vehicle_rental: %s: income to %s, %s journals, %s invoice lines",
                     company.name, SERVICES, len(journals), cr.rowcount)
    env.invalidate_all()
