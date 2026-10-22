# -*- coding: utf-8 -*-
"""Fase 5.1: load the FLEXIRENT 2026 tariffs (Tarifas completas Pinveco JUN26, V3).

Run with: odoo shell -d <db> < fase5_flexirent.py   (idempotent)
- Needs module version 19.0.6.4: FLEXIRENT priced as a fee per 30 days. With
  the old daily logic these fees would be multiplied by the days.
- Fee per 30 days for each km package, VAT included. Km above the package:
  0,29 EUR + VAT (0,35 EUR VAT included) for every package.
- Valid from 01/01/2026 ("Tarifa 2026"): there were no FLEXIRENT tariffs
  before, and contracts signed earlier this year (contract 77, 17/09/2026) must
  find theirs. Open FLEXIRENT tariffs of earlier dates are closed, not deleted.
- Draft FLEXIRENT contracts are re-priced against the new tariffs.
"""
from datetime import date, timedelta

FLEXIRENT_2026 = {
    'G1': (695.0, 890.0, 1251.0),
    'A': (695.0, 890.0, 1251.0),
    'C': (695.0, 890.0, 1251.0),
    'F': (895.0, 1150.0, 1410.0),
    'D': (995.0, 1246.0, 1570.0),
    'V': (1150.0, 1350.0, 1650.0),
    'W': (1190.0, 1390.0, 1690.0),
    'K': (1350.0, 1690.0, 1990.0),
    'T': (1670.0, 1950.0, 2350.0),
    'X': (1670.0, 1950.0, 2350.0),
    'B': (1770.0, 2150.0, 2600.0),
    'E': (1670.0, 1950.0, 2350.0),
    'Z': (2180.0, 2600.0, 3200.0),
}  # {category code: fee per 30 days for 3.000 / 5.000 / 7.500 km}, VAT included
PACKAGES = (3000, 5000, 7500)
VAT = 1.21
EXTRA_KM_PRICE = round(0.29 * VAT, 2)
COMPANY = env.ref('base.main_company')

valid_from = date(2026, 1, 1)
Rule = env['vehicle.pricing.rule'].sudo().with_context(active_test=False)
Category = env['fleet.vehicle.model.category'].sudo()
Contract = env['vehicle.contract'].sudo().with_context(tracking_disable=True)

old = Rule.search([('pricing_type', '=', 'flexirent'), ('valid_from', '<', valid_from),
                   ('valid_until', '=', False)])
old.write({'valid_until': valid_from - timedelta(days=1)})

created = 0
for code, fees in sorted(FLEXIRENT_2026.items()):
    category = Category.search([('name', '=like', 'Tipo %s - %%' % code)], limit=1)
    if not category:
        raise SystemExit('Missing category Tipo %s' % code)
    for km, fee in zip(PACKAGES, fees):
        if Rule.search_count([
            ('vehicle_category_id', '=', category.id), ('pricing_type', '=', 'flexirent'),
            ('flexirent_km_total', '=', km), ('valid_from', '=', valid_from),
        ]):
            continue
        Rule.create({
            'vehicle_category_id': category.id,
            'pricing_type': 'flexirent',
            'flexirent_km_total': km,
            'flexirent_duration_days': 30,
            'km_included': km,
            'package_days': 30,
            'price_per_unit': fee,
            'price_without_vat': round(fee / VAT, 2),
            'extra_km_price': EXTRA_KM_PRICE,
            'currency_id': COMPANY.currency_id.id,
            'company_id': COMPANY.id,
            'valid_from': valid_from,
            'notes': 'FLEXIRENT 2026 V3 (Tarifas completas Pinveco JUN26)',
        })
        created += 1

drafts = Contract.search([('pricing_type', '=', 'flexirent'), ('status', '=', 'a_draft')])
for field_name in ('calculated_rent', 'applied_pricing_rule_id'):
    env.add_to_compute(Contract._fields[field_name], drafts)
env.flush_all()
env.cr.commit()
print('VALID_FROM', valid_from)
print('CLOSED_OLD', len(old))
print('CREATED_FLEXIRENT', created)
for contract in drafts:
    print('CONTRACT', contract.reference_no, contract.vehicle_id.category_id.name,
          contract.flexirent_km_package, contract.rent, contract.calculated_rent,
          contract.flexirent_months, contract.total_vehicle_rent,
          contract.applied_pricing_rule_id.display_name)
