# -*- coding: utf-8 -*-
"""The availability chart and the numbering of contracts.

Found in the Phase 7 regression:
- five contracts were left named "Nueva": the placeholder was translated when
  the form opened and compared untranslated when saving, so no number was
  given; clicking any of them on the chart opened the first "Nueva";
- the chart showed hours in UTC and trusted the company cookie with sudo.
"""
import importlib.util
from datetime import datetime

from odoo.tests.common import new_test_user, tagged
from odoo.tools.misc import file_path

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_availability')
class TestContractNumbering(VehicleRentalCase):

    def _contract(self, reference, lang='en_US'):
        return self.env['vehicle.contract'].with_context(lang=lang).create({
            'customer_id': self.customer.id, 'vehicle_id': self.spare_vehicle.id, 'rent_type': 'days',
            'rent': 50.0, 'start_date': self.start_date, 'end_date': self.end_date,
            'reference_no': reference})

    def test_translated_placeholder_gets_a_number(self):
        for placeholder in ('Nueva', 'Nuevo', 'New'):
            contract = self._contract(placeholder)
            self.assertNotEqual(contract.reference_no, placeholder)
            self.assertTrue(contract.reference_no.startswith('VC'), contract.reference_no)
            contract.unlink()

    def test_migration_numbers_the_contracts_left_unnumbered(self):
        contract = self._contract('VC-TEMP')
        self.env.cr.execute("UPDATE vehicle_contract SET reference_no = 'Nueva' WHERE id = %s", [contract.id])
        self.env.invalidate_all()
        path = file_path('vehicle_rental/migrations/19.0.6.17/post-migrate.py')
        spec = importlib.util.spec_from_file_location('numbering_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.migrate(self.env.cr, '19.0.6.16')
        self.env.invalidate_all()
        self.assertTrue(contract.reference_no.startswith('VC'), contract.reference_no)
        created = contract.create_date
        self.assertIn(f'{created.year}/{created.month:02d}/', contract.reference_no, 'numbered by its creation date')


@tagged('post_install', '-at_install', 'vehicle_availability')
class TestAvailabilityChart(VehicleRentalCase):

    def _rows(self, contracts_env):
        return {row['contract_id']: row for row in contracts_env._availability_chart_data()}

    def test_row_opens_its_own_contract(self):
        row = self._rows(self.env['vehicle.contract'])[self.contract.id]
        self.assertEqual(row['name'], self.contract.reference_no)

    def test_dates_are_in_the_user_timezone(self):
        year = self.now.year + 1  # summer: Madrid is UTC+2
        self.contract.write({'start_date': datetime(year, 7, 1, 22, 30), 'end_date': datetime(year, 7, 3, 8, 0)})
        rows = self._rows(self.env['vehicle.contract'].with_context(tz='Europe/Madrid'))
        self.assertEqual(rows[self.contract.id]['start_date'], f'02-07-{year} 00:30:00')

    def test_only_allowed_companies(self):
        other = self.env['res.company'].create({'name': 'Ajena Disponibilidad'})
        foreign = self._create_contract(self.spare_vehicle, self.customer, status='a_draft')
        foreign.company_id = other
        clerk = new_test_user(self.env, login='dispo_sunset', groups='base.group_user,fleet.fleet_group_manager',
                              company_id=self.company.id, company_ids=[self.company.id])
        contracts = self.env['vehicle.contract'].with_user(clerk).with_context(
            allowed_company_ids=[self.company.id, other.id])
        rows = self._rows(contracts)
        self.assertIn(self.contract.id, rows)
        self.assertNotIn(foreign.id, rows)

    def test_menu_is_in_spanish(self):
        action = self.env.ref('vehicle_rental.action_vehicle_availability')
        self.assertEqual(action.with_context(lang='en_US').name, 'Disponibilidad')
