# -*- coding: utf-8 -*-
"""Printed contract must warn about annexes, and the acta must adapt its wording."""
from datetime import timedelta

from odoo.tests.common import tagged

from .common import VehicleRentalCase

CONTRACT_REPORT = 'vehicle_rental.vehicle_contract_report_template'
RETURN_REPORT = 'vehicle_rental.vehicle_contract_return_report_template'
WARNING = 'CONTRATO MODIFICADO'


@tagged('post_install', '-at_install', 'vehicle_report')
class TestContractReportAnnexes(VehicleRentalCase):

    def _render_contract(self, contract=None):
        contract = contract or self.contract
        html, _dummy = self.env['ir.actions.report']._render_qweb_html(
            CONTRACT_REPORT, contract.ids)
        return html.decode() if isinstance(html, bytes) else html

    def _render_acta(self, record):
        html, _dummy = self.env['ir.actions.report']._render_qweb_html(
            RETURN_REPORT, record.ids)
        return html.decode() if isinstance(html, bytes) else html

    def test_clean_contract_has_no_warning(self):
        html = self._render_contract()

        self.assertNotIn(WARNING, html)

    def test_return_adds_the_warning_and_is_listed(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.action_confirm_return()

        html = self._render_contract()

        self.assertIn(WARNING, html)
        self.assertIn('Devolución de vehículo', html)
        self.assertIn(self.vehicle.license_plate, html)
        self.assertIn('sin daños', html)

    def test_damaged_return_is_flagged_in_the_annex_table(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({
            'has_damage': True,
            'damage_description': '<p>Rayón</p>',
        })
        wizard.action_confirm_return()

        html = self._render_contract()

        self.assertIn('con daños', html)

    def test_extension_is_listed(self):
        extension = self.env['vehicle.contract.extension'].create({
            'contract_id': self.contract.id,
            'new_end_date': self.contract.end_date + timedelta(days=3),
            'daily_rate': 50.0,
        })
        extension.action_mark_signed()

        html = self._render_contract()

        self.assertIn(WARNING, html)
        self.assertIn('Ampliación de contrato', html)

    def test_substitution_is_listed(self):
        self.env['vehicle.contract.substitution'].create({
            'contract_id': self.contract.id,
            'reason': 'breakdown',
            'old_vehicle_id': self.vehicle.id,
            'new_vehicle_id': self.spare_vehicle.id,
        })

        html = self._render_contract()

        self.assertIn(WARNING, html)
        self.assertIn('Sustitución de vehículo', html)
        self.assertIn(self.spare_vehicle.license_plate, html)

    def test_live_template_is_the_one_carrying_the_warning(self):
        """Two files declare this template id; the loaded one must have the block.

        ``reports/vehicle_contract_report.xml`` is dead code overwritten by
        ``report/vehicle_contract_report_views.xml``. If the manifest order ever
        flips, the warning silently disappears from printed contracts.
        """
        self.env['vehicle.contract.substitution'].create({
            'contract_id': self.contract.id,
            'reason': 'breakdown',
            'old_vehicle_id': self.vehicle.id,
            'new_vehicle_id': self.spare_vehicle.id,
        })
        view = self.env.ref('vehicle_rental.vehicle_contract_report_template')

        self.assertIn(WARNING, view.arch)

    def test_acta_states_the_amount_when_appraised(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({
            'has_damage': True,
            'damage_description': '<p>Espejo roto</p>',
            'damage_amount': 180.0,
        })
        wizard.action_confirm_return()

        html = self._render_acta(self.contract.return_ids)

        self.assertIn('importe estimado', html)
        self.assertNotIn('se determinará mediante la correspondiente valoración', html)

    def test_acta_uses_the_pending_appraisal_clause_when_amount_is_zero(self):
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.write({
            'has_damage': True,
            'damage_description': '<p>Espejo roto</p>',
            'damage_amount': 0.0,
        })
        wizard.action_confirm_return()

        html = self._render_acta(self.contract.return_ids)

        self.assertIn('se determinará mediante la correspondiente valoración', html)

    def test_acta_renders_as_pdf(self):
        """Test mode renders reports as HTML unless rendering is forced."""
        wizard = self._fill_valid_return(self._open_return_wizard())
        wizard.action_confirm_return()
        record = self.contract.return_ids

        pdf, content_type = self.env['ir.actions.report'].sudo().with_context(
            force_report_rendering=True)._render_qweb_pdf(RETURN_REPORT, record.ids)

        self.assertEqual(content_type, 'pdf')
        self.assertTrue(pdf.startswith(b'%PDF'))
