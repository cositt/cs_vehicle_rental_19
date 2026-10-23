# -*- coding: utf-8 -*-
"""Number the contracts left as "Nueva".

The default reference was translated when the form opened and compared
untranslated when saving, so some contracts never got their number. They take
the next numbers of the sequence, oldest first.
"""
import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.vehicle_rental.models.vehicle_contract import NEW_REFERENCES

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    contracts = env['vehicle.contract'].with_context(active_test=False).search(
        [('reference_no', 'in', NEW_REFERENCES)], order='id')
    for contract in contracts:
        sequence = env['ir.sequence'].with_company(contract.company_id).with_context(
            ir_sequence_date=contract.create_date)
        contract.reference_no = sequence.next_by_code('vehicle.contract')
        _logger.info("Contract %s numbered %s", contract.id, contract.reference_no)
