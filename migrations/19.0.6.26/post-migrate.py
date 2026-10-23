# -*- coding: utf-8 -*-
"""The imported fleet was left as "Nueva solicitud": every rental vehicle is registered."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE fleet_vehicle
           SET state_id = (SELECT res_id FROM ir_model_data
                            WHERE module = 'fleet' AND name = 'fleet_vehicle_state_registered')
         WHERE state_id = (SELECT res_id FROM ir_model_data
                            WHERE module = 'fleet' AND name = 'fleet_vehicle_state_new_request')
    """)
    _logger.info("vehicle_rental 19.0.6.26: %s vehicles moved to Matriculado", cr.rowcount)
