# -*- coding: utf-8 -*-
"""Forms of the module use the Odoo 19 chatter.

The pre-17 ``<div class="oe_chatter">`` with loose message fields renders as
two bare lists that cover the whole form.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'vehicle_views')
class TestFormChatter(TransactionCase):

    def test_no_form_uses_the_old_chatter(self):
        views = self.env['ir.ui.view'].search([
            ('type', '=', 'form'), ('model_data_id.module', '=', 'vehicle_rental')])
        old = views.filtered(lambda view: 'oe_chatter' in view.arch_db)
        self.assertFalse(old, old.mapped('name'))
