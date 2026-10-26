# -*- coding: utf-8 -*-
from odoo import models


class VehicleContractMailRecipients(models.Model):
    """The customer receives the contract mails.

    Templates with «use default recipients» (the default in Odoo 19) look for
    partner_id on the record. The contract keeps it in customer_id, so mails
    sent from several contracts at once had no recipient (production,
    2026-10-26: «Entregar todos» of a group, mail_email_missing).
    """
    _inherit = 'vehicle.contract'

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']
