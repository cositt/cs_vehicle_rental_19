# -*- coding: utf-8 -*-
"""Price every tariff in the currency of its company.

The 274 tariffs imported on 2025-12-19 were stored in USD, so the back office
showed them with "$". The amounts are already euros: only the currency is wrong.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE vehicle_pricing_rule r
           SET currency_id = c.currency_id
          FROM res_company c
         WHERE c.id = r.company_id
           AND r.currency_id IS DISTINCT FROM c.currency_id
    """)
    _logger.info("vehicle_rental: %s tariffs moved to their company currency", cr.rowcount)
