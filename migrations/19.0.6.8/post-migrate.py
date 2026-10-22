# -*- coding: utf-8 -*-
"""Rental prices include VAT (21 %), as the tariff says on every page.

Each company gets a 21 % sale tax included in the price, set on the rental
products and on the contracts still open. Invoices already issued are not
touched. A company without a chart of accounts (no 21 % sale tax) is skipped
and logged: it needs its chart installed first.

Deposit rules are loaded from the general conditions: credit card 300 EUR,
debit card and cash 750 EUR, one rule per category and company. The test
rules already there are corrected. The no-excess insurance tariff 2026 (V3)
is loaded per day, VAT included, by duration and driver type.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'tracking_disable': True})
    for company in env['res.company'].search([]):
        company._vehicle_rental_apply_sale_tax()
        tax = company._vehicle_rental_sale_tax()
        if tax:
            _logger.info("vehicle_rental: company %s uses VAT-included tax %s", company.name, tax.id)
        else:
            _logger.warning("vehicle_rental: company %s has no 21%% sale tax, rentals stay without VAT",
                            company.name)
        company._vehicle_rental_load_deposit_rules()
        _logger.info("vehicle_rental: company %s has %s deposit rules", company.name,
                     env['vehicle.deposit.rule'].search_count([('company_id', '=', company.id)]))
        company._vehicle_rental_load_insurance_pricing()
    env.flush_all()
