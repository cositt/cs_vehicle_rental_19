# -*- coding: utf-8 -*-
"""FLEXIRENT contracts move from a daily rate to the fee per 30 days.

Until now a FLEXIRENT contract kept the fee divided by 30 in `rent` and was
charged rent x days (contract 77: 72,67 x 731 days = 53.121,77 instead of
24 x 2.180 = 52.320). The PDF already showed round(rent x 30) as the fee: that
is the value kept. Contracts with instalments or an invoice are left alone.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

PACKAGES = {3000: '3000', 5000: '5000', 7500: '7500'}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'tracking_disable': True})
    contracts = env['vehicle.contract'].with_context(active_test=False).search([
        ('pricing_type', '=', 'flexirent'),
        ('installment_created', '!=', True),
        ('invoice_id', '=', False),
        ('vehicle_payment_option_ids', '=', False),
    ])
    for contract in contracts:
        fee = round(contract.rent * 30)
        package = PACKAGES.get(int(contract.flexirent_km_included or 0), '3000')
        _logger.info("vehicle_rental: FLEXIRENT contract %s rent %s/day -> %s per 30 days (%s km)",
                     contract.reference_no, contract.rent, fee, package)
        contract.write({'rent': fee, 'flexirent_km_package': package})
    env.flush_all()
