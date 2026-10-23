# -*- coding: utf-8 -*-
"""The cancelled status reads "Cancelado".

It was labelled "Cancel" and translated as the verb "Cancelar". Updating the
module does not overwrite a translation already loaded, so it is set here.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    selection = env.ref('vehicle_rental.selection__vehicle_contract__status__d_cancel')
    selection.update_field_translations('name', {'es_ES': 'Cancelado'})
