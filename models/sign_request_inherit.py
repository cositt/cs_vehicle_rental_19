# -*- coding: utf-8 -*-
from odoo import models


class SignRequestInherit(models.Model):
    _inherit = 'sign.request'

    def _sign(self):
        res = super()._sign()
        for req in self:
            if not req.reference_doc:
                continue
            if req.reference_doc._name == 'vehicle.contract.extension':
                ext = req.reference_doc
                if ext.exists() and ext.state in ('draft', 'sent'):
                    ext.state = 'signed'
        return res
