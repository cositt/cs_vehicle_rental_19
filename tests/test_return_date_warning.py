# -*- coding: utf-8 -*-
"""A return dated in the future or before the start warns, it does not block.

Prod, 2026-10-26: a return dated 6-dic (before the rental even started) was
accepted silently. Juan: "añadele un aviso antes de proceder pero no lo bloquees".
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_return_date_warning')
class TestReturnDateWarning(VehicleRentalCase):

    def test_future_return_date_warns(self):
        wizard = self._open_return_wizard()
        wizard.return_date = fields.Datetime.now() + timedelta(days=10)
        result = wizard._onchange_return_date_warning()
        self.assertIn('futura', result['warning']['message'])

    def test_return_before_start_warns(self):
        wizard = self._open_return_wizard()
        wizard.return_date = self.contract.start_date - timedelta(days=1)
        result = wizard._onchange_return_date_warning()
        self.assertIn('anterior', result['warning']['message'])

    def test_return_now_has_no_warning(self):
        wizard = self._open_return_wizard()
        wizard.return_date = max(fields.Datetime.now(), self.contract.start_date)
        self.assertFalse(wizard._onchange_return_date_warning())

    def test_future_return_is_not_blocked(self):
        wizard = self._fill_valid_return(self._open_return_wizard(),
                                         return_date=fields.Datetime.now() + timedelta(days=10))
        wizard.action_confirm_return()
        self.assertEqual(self.contract.status, 'c_return')
