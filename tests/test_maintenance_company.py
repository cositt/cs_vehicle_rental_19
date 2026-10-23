# -*- coding: utf-8 -*-
"""Maintenance of a vehicle belongs to the company that owns the vehicle.

Pinveco owns almost the whole fleet, but the staff act as Sunset: requests
and workshop bills were created in the company of the user, so the cost of a
Pinveco van ended up in the books of Sunset.
"""
from odoo.exceptions import UserError
from odoo.tests.common import new_test_user, tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_maintenance')
class TestMaintenanceCompany(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sunset = cls.env.company
        cls.owner = cls.env['res.company'].create({'name': 'Dueña Flota Test'})
        cls.env['account.chart.template'].try_loading('es_pymes', company=cls.owner, install_demo=False)
        cls.user = new_test_user(
            cls.env, login='taller_multi',
            groups='base.group_user,fleet.fleet_group_manager,maintenance.group_equipment_manager,'
                   'account.group_account_invoice',
            company_id=cls.sunset.id, company_ids=[cls.sunset.id, cls.owner.id])
        cls.owned_vehicle = cls._create_vehicle('DUE-0001', odometer=1000)
        cls.owned_vehicle.company_id = cls.owner
        cls.schedule = cls.env['maintenance.schedule'].create({
            'name': 'Revisión compartida', 'maintenance_days': 90})
        cls.owned_vehicle.maintenance_schedule_id = cls.schedule
        cls.vendor = cls.env['res.partner'].create({'name': 'Taller de Pruebas'})
        cls.service = cls.env['product.product'].create({'name': 'Revisión de prueba', 'type': 'service'})

    def _as_sunset(self, model):
        """The clerk acts as Sunset only, as in the company switcher."""
        return self.env[model].with_user(self.user).with_context(allowed_company_ids=[self.sunset.id])

    def _request(self):
        vehicle = self._as_sunset('fleet.vehicle').browse(self.owned_vehicle.id)
        action = vehicle.action_create_maintenance_request()
        return self._as_sunset('maintenance.request').browse(action['res_id'])

    def test_request_takes_the_company_of_the_vehicle(self):
        self.assertEqual(self._request().company_id, self.owner)

    def test_request_of_the_other_company_is_readable_acting_as_sunset(self):
        request = self._request()
        self.assertTrue(request.name)
        found = self._as_sunset('maintenance.request').search([('fleet_vehicle_id', '=', self.owned_vehicle.id)])
        self.assertEqual(found, request)

    def test_bill_opens_when_the_company_is_active(self):
        request = self._request()
        request.write({'vehicle_maintenance_service_ids': [(0, 0, {
            'product_id': self.service.id, 'service_charge': 100.0})]})
        wizard = self.env['maintenance.request.bill'].with_user(self.user).with_context(
            allowed_company_ids=[self.sunset.id, self.owner.id], active_id=request.id,
        ).create({'vendor_id': self.vendor.id})
        action = wizard.action_create_vendor_bill()
        self.assertEqual(action['res_model'], 'account.move')

    def test_scheduled_request_is_preventive(self):
        request = self._request()
        self.assertEqual(request.maintenance_type, 'preventive')

    def test_workshop_bill_goes_to_the_company_of_the_vehicle(self):
        request = self._request()
        request.write({'vehicle_maintenance_service_ids': [(0, 0, {
            'product_id': self.service.id, 'service_charge': 100.0})]})
        wizard = self._as_sunset('maintenance.request.bill').with_context(
            active_id=request.id).create({'vendor_id': self.vendor.id})
        action = wizard.action_create_vendor_bill()
        bill = request.sudo().bill_id
        self.assertEqual(bill.company_id, self.owner)
        self.assertEqual(action['tag'], 'display_notification',
                         'the bill is in a company that is not active: say so instead of opening it')
        self.assertIn(self.owner.name, action['params']['message'])
        self.assertEqual(bill.journal_id.company_id, self.owner)
        self.assertEqual(request.bill_count, 1, 'the bill counts although its company is not active')
        self.assertEqual(request.action_vendor_bill_views()['tag'], 'display_notification')
        sections = bill.invoice_line_ids.filtered(lambda l: l.display_type == 'line_section')
        self.assertEqual(sections.mapped('name'), ['Servicios de mantenimiento'])

    def test_schedule_of_another_company_is_refused(self):
        foreign = self.env['maintenance.schedule'].create({
            'name': 'Solo Sunset', 'maintenance_days': 30, 'company_id': self.sunset.id})
        with self.assertRaises(UserError):
            self.owned_vehicle.maintenance_schedule_id = foreign

    def test_new_schedule_is_shared_by_every_company(self):
        schedule = self._as_sunset('maintenance.schedule').create({'name': 'Nueva', 'maintenance_days': 60})
        self.assertFalse(schedule.company_id)


@tagged('post_install', '-at_install', 'vehicle_maintenance')
class TestWorkshopServices(VehicleRentalCase):
    """The workshop has its own services, booked as repairs (622)."""

    SERVICES = ('workshop_service_revision', 'workshop_service_repair', 'workshop_service_tyres',
                'workshop_service_itv', 'workshop_service_bodywork', 'workshop_service_brakes',
                'workshop_service_oil')

    def test_workshop_services_exist_for_every_company(self):
        for xmlid in self.SERVICES:
            product = self.env.ref(f'vehicle_rental.{xmlid}')
            self.assertEqual(product.type, 'service')
            self.assertFalse(product.company_id, 'shared by Sunset and Pinveco')
            self.assertFalse(product.sale_ok)

    def test_service_line_offers_only_workshop_services(self):
        lines = self.env['vehicle.maintenance.service']
        domain = lines._fields['product_id'].domain
        offered = self.env['product.product'].search(domain(lines) if callable(domain) else domain)
        self.assertIn(self.env.ref('vehicle_rental.workshop_service_revision'), offered)
        self.assertNotIn(self.env.ref('vehicle_rental.vehicle_rent_charge'), offered)

    def test_workshop_bill_is_booked_as_repairs(self):
        request = self.env['maintenance.request'].create({
            'name': 'Revisión taller', 'fleet_vehicle_id': self.vehicle.id})
        request.write({'vehicle_maintenance_service_ids': [(0, 0, {
            'product_id': self.env.ref('vehicle_rental.workshop_service_revision').id,
            'service_charge': 120.0})]})
        vendor = self.env['res.partner'].create({'name': 'Taller 622'})
        self.env['maintenance.request.bill'].with_context(active_id=request.id).create(
            {'vendor_id': vendor.id}).action_create_vendor_bill()
        line = request.bill_id.invoice_line_ids.filtered('product_id')
        self.assertEqual(line.account_id.code, '622000')
