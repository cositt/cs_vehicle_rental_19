# -*- coding: utf-8 -*-
"""Starter configuration loaded by 19.0.6.30.

Prod, 2026-10-26: no cancellation policy and no maintenance schedule existed,
so maintenance requests could not be created and every cancellation charge
was typed by hand. Juan: set approximate values, the companies will adjust
them. Saving a lead also ran the automatic IAP enrichment, which spends
credits and wrote the company phone on the customer: it becomes manual.
"""
import importlib.util

from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_starter_config')
class TestStarterConfiguration(VehicleRentalCase):

    def _migrate(self):
        path = file_path('vehicle_rental/migrations/19.0.6.30/post-migrate.py')
        spec = importlib.util.spec_from_file_location('vehicle_starter_config', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, '19.0.6.29')
        self.env.invalidate_all()

    def test_maintenance_schedules_shared_by_both_companies(self):
        self.env['maintenance.schedule'].search([]).write({'active': False}) \
            if 'active' in self.env['maintenance.schedule']._fields else None
        self._migrate()
        schedules = self.env['maintenance.schedule'].search([('name', 'like', 'Revisión cada')])
        self.assertTrue(schedules)
        self.assertFalse(schedules.company_id, 'shared, no company')
        self.assertIn(30, schedules.mapped('maintenance_days'))

    def test_cancellation_policies_per_company(self):
        self._migrate()
        for company in self.env['res.company'].search([]):
            policies = self.env['cancellation.policy'].search([('company_id', '=', company.id)])
            self.assertTrue(policies, company.name)
            self.assertTrue(all(p.terms_and_conditions for p in policies))

    def test_migration_does_not_duplicate(self):
        self._migrate()
        count = (self.env['maintenance.schedule'].search_count([]),
                 self.env['cancellation.policy'].search_count([]))
        self._migrate()
        self.assertEqual(count, (self.env['maintenance.schedule'].search_count([]),
                                 self.env['cancellation.policy'].search_count([])))

    def test_lead_enrichment_is_manual(self):
        self._migrate()
        param = self.env['ir.config_parameter'].sudo().get_param('crm.iap.lead.enrich.setting')
        self.assertEqual(param, 'manual')
        cron = self.env.ref('crm_iap_enrich.ir_cron_lead_enrichment', raise_if_not_found=False)
        if cron:
            self.assertFalse(cron.with_context(active_test=False).active)

    def test_schedule_company_is_optional_in_the_form(self):
        arch = self.env.ref('vehicle_rental.maintenance_schedule_form_view').arch_db
        self.assertNotIn('name="company_id" required="1"', arch)
