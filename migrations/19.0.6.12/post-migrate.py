# -*- coding: utf-8 -*-
"""Fleet imported with the wrong fuel and one car in a van category.

Odoo 19 creates vehicle models as electric, so the imported fleet was
"Eléctrica". The fuel is read from the model name; the rest are diesel vans.
Only electric rows are touched, so a fuel set by hand is kept.
"""
import logging

_logger = logging.getLogger(__name__)

FUEL_BY_NAME = (
    ('%gasolina%', 'gasoline'),
    ('%hibrido%', 'full_hybrid'),
    ('%híbrido%', 'full_hybrid'),
)
CARS_IN_VAN_CATEGORY = ('4717MCJ',)  # Volkswagen Golf


def _fix_fuel(cr):
    for pattern, fuel in FUEL_BY_NAME:
        cr.execute("""
            UPDATE fleet_vehicle_model SET default_fuel_type = %s
             WHERE default_fuel_type = 'electric' AND name ILIKE %s
        """, (fuel, pattern))
    cr.execute("""
        UPDATE fleet_vehicle_model SET default_fuel_type = 'diesel'
         WHERE default_fuel_type = 'electric'
    """)
    cr.execute("""
        UPDATE fleet_vehicle v SET fuel_type = m.default_fuel_type
          FROM fleet_vehicle_model m
         WHERE m.id = v.model_id AND v.fuel_type = 'electric'
    """)
    _logger.info("vehicle_rental: fuel of %s vehicles taken from their model", cr.rowcount)


def _fix_cars_category(cr):
    cr.execute("""
        SELECT id FROM fleet_vehicle_model_category
         WHERE name LIKE 'Tipo G1%%' ORDER BY id LIMIT 1
    """)
    row = cr.fetchone()
    if not row:
        _logger.warning("vehicle_rental: no Tipo G1 category, cars left as they are")
        return
    cr.execute("""
        UPDATE fleet_vehicle SET category_id = %s
         WHERE license_plate IN %s AND category_id IS DISTINCT FROM %s
    """, (row[0], CARS_IN_VAN_CATEGORY, row[0]))
    _logger.info("vehicle_rental: %s cars moved to Tipo G1", cr.rowcount)


def migrate(cr, version):
    _fix_fuel(cr)
    _fix_cars_category(cr)
