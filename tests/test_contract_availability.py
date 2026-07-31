# -*- coding: utf-8 -*-
"""Disponibilidad de vehículos al crear un contrato directo.

El contrato ofrecía cualquier vehículo operativo sin mirar categoría ni
reservas en borrador, así que se podía contratar un coche que otro ya tenía
apalabrado para esas fechas. Aquí se fija la misma lógica que en reservas.
"""
from datetime import timedelta

from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_availability')
class TestContractVehicleAvailability(VehicleRentalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_category = cls.env['fleet.vehicle.model.category'].create({
            'name': 'OtraCategoria',
        })
        cls.other_model = cls.env['fleet.vehicle.model'].create({
            'name': 'OtroModelo',
            'brand_id': cls.brand.id,
            'category_id': cls.other_category.id,
        })
        cls.other_vehicle = cls.env['fleet.vehicle'].create({
            'model_id': cls.other_model.id,
            'category_id': cls.other_category.id,
            'license_plate': 'TEST-0003',
            'status': 'available',
        })

    def _draft(self, **overrides):
        """Contrato en borrador listo para elegir vehículo."""
        values = {
            'customer_id': self.customer.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'vehicle_category_id': self.category.id,
        }
        values.update(overrides)
        contract = self.env['vehicle.contract'].create(values)
        contract.invalidate_recordset()
        return contract

    def test_without_category_it_offers_nothing(self):
        contract = self._draft(vehicle_category_id=False)

        self.assertFalse(contract.available_vehicle_ids)

    def test_without_dates_it_offers_nothing(self):
        contract = self._draft(start_date=False, end_date=False)

        self.assertFalse(contract.available_vehicle_ids)

    def test_it_offers_the_free_vehicles_of_the_category(self):
        contract = self._draft()

        self.assertIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_a_vehicle_of_another_category_is_not_offered(self):
        contract = self._draft()

        self.assertNotIn(self.other_vehicle, contract.available_vehicle_ids)

    def test_a_vehicle_on_a_running_contract_is_not_offered(self):
        """self.vehicle está en el contrato en curso del fixture."""
        contract = self._draft()

        self.assertNotIn(self.vehicle, contract.available_vehicle_ids)

    def test_a_vehicle_reserved_in_draft_is_not_offered(self):
        """Una reserva sin activar también bloquea: es el hueco peligroso."""
        self.env['vehicle.contract'].create({
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.start_date,
            'end_date': self.end_date,
        })

        contract = self._draft()

        self.assertNotIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_a_returned_contract_does_not_block(self):
        """Devuelto significa que el coche ya está de vuelta: queda libre."""
        returned = self.env['vehicle.contract'].create({
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.start_date,
            'end_date': self.end_date,
        })
        returned.write({'status': 'c_return'})

        contract = self._draft()

        self.assertIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_a_cancelled_contract_does_not_block(self):
        cancelled = self.env['vehicle.contract'].create({
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.start_date,
            'end_date': self.end_date,
        })
        cancelled.write({'status': 'd_cancel'})

        contract = self._draft()

        self.assertIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_a_vehicle_back_from_maintenance_is_offered_again(self):
        self.spare_vehicle.write({'status': 'in_maintenance'})
        self.assertNotIn(self.spare_vehicle, self._draft().available_vehicle_ids)

        self.spare_vehicle.in_maintenance_to_available()

        self.assertIn(self.spare_vehicle, self._draft().available_vehicle_ids)

    def test_a_reservation_on_other_dates_does_not_block(self):
        self.env['vehicle.contract'].create({
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.end_date + timedelta(days=10),
            'end_date': self.end_date + timedelta(days=15),
        })

        contract = self._draft()

        self.assertIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_a_vehicle_in_maintenance_is_not_offered(self):
        self.spare_vehicle.write({'status': 'in_maintenance'})

        contract = self._draft()

        self.assertNotIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_changing_the_dates_refreshes_the_list(self):
        contract = self._draft()
        self.assertIn(self.spare_vehicle, contract.available_vehicle_ids)

        self.env['vehicle.contract'].create({
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 50.0,
            'start_date': self.start_date,
            'end_date': self.end_date,
        })
        contract.invalidate_recordset()

        self.assertNotIn(self.spare_vehicle, contract.available_vehicle_ids)

    def test_choosing_a_vehicle_fills_the_category(self):
        """La categoría y el vehículo no pueden acabar diciendo cosas distintas."""
        contract = self._draft(vehicle_category_id=False)
        contract.vehicle_id = self.spare_vehicle

        contract._onchange_vehicle_sets_category()

        self.assertEqual(contract.vehicle_category_id, self.category)

    def test_the_category_survives_as_a_grouping_field(self):
        """Se sigue pudiendo agrupar por categoría, que es para lo que se usaba."""
        contract = self._draft()
        contract.vehicle_id = self.spare_vehicle

        groups = self.env['vehicle.contract'].read_group(
            [('id', '=', contract.id)],
            ['id'], ['vehicle_category_id'])

        self.assertEqual(groups[0]['vehicle_category_id'][0], self.category.id)
