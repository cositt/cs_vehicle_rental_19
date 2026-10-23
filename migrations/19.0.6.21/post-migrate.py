# -*- coding: utf-8 -*-
"""General terms for the contracts made before they were filled by default.

Juan agreed on 2026-10-23: the existing contracts take the terms of the
company that signs them, like the new ones.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    contracts = env['vehicle.contract'].with_context(active_test=False).search(
        [('rental_agreement_terms_id', '=', False)])
    contracts._set_default_agreement_terms()
    _logger.info("General terms set on %s contracts", len(contracts.filtered('rental_agreement_terms_id')))
