# -*- coding: utf-8 -*-
"""Fase 2.2/2.3: create categories E and G1, categorise the vehicles imported on 2025-09-18.

Run with: odoo shell -d <db> < fase2_categorias.py   (idempotent)
Group per plate comes from LISTADO VEHICULOS PINVECO 15-09-2026.xlsx. G2 is parked.
"""
import re

NEW_CATEGORIES = {
    'E': 'Tipo E - Furgoneta Botellero',
    'G1': 'Tipo G1 - Turismo',
}
PLATE_GROUP = {'3224NBF': 'E', '0114NJP': 'T', '0115NJP': 'E', '0311NLD': 'B', '4669NLH': 'A', '4673NLH': 'A', '4672NLH': 'A', '4670NLH': 'A', '9416NLS': 'W', '9412NLS': 'W', '9419NLS': 'W', '9414NLS': 'W', '9415NLS': 'W', '4671NLH': 'A', '9294NKZ': 'F', '9293NKZ': 'F', '9292NKZ': 'F', '9289NKZ': 'F', '9295NKZ': 'F', '9490NMG': 'W', '9483NMG': 'W', '9494NMG': 'W', '9477NMG': 'W', '9480NMG': 'W', '9719NMZ': 'W', '9725NMZ': 'W', '9728NMZ': 'W', '9732NMZ': 'W', '9743NMZ': 'W', '1046NNC': 'K', '1042NNC': 'K', '9461NJM': 'G1', '1866NNY': 'F', '1894NNY': 'F', '1906NNY': 'F', '1913NNY': 'F', '9467NJM': 'G1', '7992NPJ': 'F', '7982NPJ': 'F', '7990NPJ': 'F', '7987NPJ': 'F', '7993NPJ': 'K', '7996NPJ': 'K', '7997NPJ': 'K', '3512NRN': 'G2', '3518NRN': 'G2', '3511NRN': 'G2', '3503NRN': 'G2', '5996NNC': 'G2', '4871NSH': 'B', '4879NSH': 'B'}

Category = env['fleet.vehicle.model.category'].sudo()
for code, name in NEW_CATEGORIES.items():
    if not Category.search([('name', '=like', 'Tipo %s - %%' % code)], limit=1):
        Category.create({'name': name})
        print('CREATED', name)

def category_for(code):
    return Category.search([('name', '=like', 'Tipo %s - %%' % code)], limit=1)

def normalise(plate):
    return re.sub(r'[\s-]', '', plate or '').upper()

vehicles = env['fleet.vehicle'].sudo().search([('category_id', '=', False)])
done, skipped = 0, []
for vehicle in vehicles:
    code = PLATE_GROUP.get(normalise(vehicle.license_plate))
    category = category_for(code) if code and code != 'G2' else Category
    if category:
        vehicle.category_id = category
        done += 1
    else:
        skipped.append((vehicle.license_plate, code))
env.cr.commit()
print('CATEGORISED', done)
print('LEFT_WITHOUT_CATEGORY', skipped)

