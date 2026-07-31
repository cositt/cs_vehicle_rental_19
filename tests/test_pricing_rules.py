# -*- coding: utf-8 -*-
"""Tarifas por categoría, kilometraje y duración.

El cliente reportó que un alquiler de 1 día con 350 km salía a 95 €, que es
el precio de la tarifa de 4 horas, y que ampliar el contrato no cambiaba el
importe. Estos tests fijan lo que la tabla de tarifas debe devolver.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests.common import tagged

from .common import VehicleRentalCase


@tagged('post_install', '-at_install', 'vehicle_pricing')
class TestPricingRuleLookup(VehicleRentalCase):
    """La tarifa aplicable sale de categoría + kilometraje + duración."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rule_model = cls.env['vehicle.pricing.rule']
        cls.today = fields.Date.today()

        # Precios distintos a propósito: si la búsqueda ignora la duración,
        # el importe delata cuál ha elegido.
        cls.prices = {
            '4h': 95.0,
            '1-2d': 120.0,
            '3-5d': 110.0,
            '6-10d': 100.0,
            '11-20d': 90.0,
            '21-29d': 80.0,
        }
        cls.rules = {}
        for duration, price in cls.prices.items():
            cls.rules[duration] = cls.rule_model.create({
                'vehicle_category_id': cls.category.id,
                'pricing_type': 'standard',
                'km_range': '350',
                'duration_range': duration,
                'price_per_unit': price,
                'valid_from': cls.today - timedelta(days=1),
            })

    def _find(self, total_km, total_days):
        return self.rule_model.find_pricing_rule(
            category_id=self.category.id,
            total_km=total_km,
            total_days=total_days,
        )

    def test_half_day_uses_the_four_hour_rate(self):
        self.assertEqual(self._find(350, 0.5), self.rules['4h'])

    def test_one_day_does_not_use_the_four_hour_rate(self):
        """El caso exacto que reportó el cliente."""
        rule = self._find(350, 1)

        self.assertTrue(rule, 'no se encontró tarifa para 1 día y 350 km')
        self.assertNotEqual(rule.price_per_unit, self.prices['4h'])
        self.assertEqual(rule, self.rules['1-2d'])

    def test_each_duration_band_finds_its_own_rate(self):
        for days, duration in ((2, '1-2d'), (4, '3-5d'), (8, '6-10d'),
                               (15, '11-20d'), (25, '21-29d')):
            with self.subTest(days=days):
                self.assertEqual(self._find(350, days), self.rules[duration])

    def test_the_km_band_is_respected(self):
        cheap_km = self.rule_model.create({
            'vehicle_category_id': self.category.id,
            'pricing_type': 'standard',
            'km_range': '100',
            'duration_range': '1-2d',
            'price_per_unit': 70.0,
            'valid_from': self.today - timedelta(days=1),
        })

        self.assertEqual(self._find(80, 1), cheap_km)
        self.assertEqual(self._find(300, 1), self.rules['1-2d'])

    def test_km_bands_take_the_upper_bound(self):
        self.assertEqual(self.rule_model._get_km_range_from_total(100), '100')
        self.assertEqual(self.rule_model._get_km_range_from_total(101), '350')
        self.assertEqual(self.rule_model._get_km_range_from_total(350), '350')
        self.assertEqual(self.rule_model._get_km_range_from_total(900), 'unlimited')

    def test_duration_bands_match_the_stored_values(self):
        """El mapeo debe devolver los valores que existen en la tabla."""
        valid = dict(self.rule_model._fields['duration_range'].selection)

        for days in (0.5, 1, 2, 4, 8, 15, 25):
            with self.subTest(days=days):
                band = self.rule_model._get_duration_range_from_days(days)
                self.assertIn(
                    band, valid,
                    '"%s" no es un valor válido de duration_range' % band)

    def test_an_expired_rate_is_ignored(self):
        self.rules['1-2d'].valid_until = self.today - timedelta(days=1)

        self.assertNotEqual(self._find(350, 1), self.rules['1-2d'])

    def test_an_archived_rate_is_ignored(self):
        self.rules['1-2d'].active = False

        self.assertNotEqual(self._find(350, 1), self.rules['1-2d'])


@tagged('post_install', '-at_install', 'vehicle_pricing')
class TestContractCalculatedRent(VehicleRentalCase):
    """El importe del contrato sale de la tarifa que corresponde."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        rule_model = cls.env['vehicle.pricing.rule']
        cls.rate_4h = rule_model.create({
            'vehicle_category_id': cls.category.id,
            'pricing_type': 'standard',
            'km_range': '350',
            'duration_range': '4h',
            'price_per_unit': 95.0,
            'valid_from': cls.today - timedelta(days=1),
        })
        cls.rate_1_2d = rule_model.create({
            'vehicle_category_id': cls.category.id,
            'pricing_type': 'standard',
            'km_range': '350',
            'duration_range': '1-2d',
            'price_per_unit': 120.0,
            'valid_from': cls.today - timedelta(days=1),
        })
        cls.rate_6_10d = rule_model.create({
            'vehicle_category_id': cls.category.id,
            'pricing_type': 'standard',
            'km_range': '350',
            'duration_range': '6-10d',
            'price_per_unit': 100.0,
            'valid_from': cls.today - timedelta(days=1),
        })

    def _contract(self, days, total_km=350):
        contract = self.env['vehicle.contract'].create({
            'customer_id': self.customer.id,
            'vehicle_id': self.spare_vehicle.id,
            'rent_type': 'days',
            'rent': 1.0,
            # El contrato exige motivo cuando la tarifa introducida no coincide
            # con la calculada, que es justo lo que hacen estos tests.
            'discount_reason': 'Tarifa fijada por el test',
            'start_date': self.start_date,
            'end_date': self.start_date + timedelta(days=days),
            'total_km': total_km,
        })
        contract.invalidate_recordset()
        return contract

    def test_one_day_is_not_charged_the_four_hour_rate(self):
        contract = self._contract(days=1)

        self.assertEqual(contract.calculated_rent, self.rate_1_2d.price_per_unit)

    def test_extending_the_contract_changes_the_rate(self):
        """Ampliar de 1 a 8 días debe cambiar el importe de tramo."""
        contract = self._contract(days=1)
        first = contract.calculated_rent

        contract.end_date = self.start_date + timedelta(days=8)
        contract.invalidate_recordset()

        self.assertNotEqual(contract.calculated_rent, first)
        self.assertEqual(contract.calculated_rent, self.rate_6_10d.price_per_unit)

    def test_the_applied_rule_is_recorded(self):
        contract = self._contract(days=1)

        self.assertEqual(contract.applied_pricing_rule_id, self.rate_1_2d)
