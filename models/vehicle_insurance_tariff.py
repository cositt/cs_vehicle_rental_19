# -*- coding: utf-8 -*-
"""No-excess insurance tariff 2026 (V3), per day, VAT included."""
from datetime import date

from odoo import models

INSURANCE_TARIFF_FROM = date(2026, 1, 1)
# duration range: (normal driver, special driver < 25 or > 60 years)
NO_FRANCHISE_PER_DAY = {
    '1_3': (36.0, 46.0),
    '4_7': (27.0, 35.0),
    '8_15': (24.0, 31.0),
    '16_30': (19.0, 28.0),
    '31_60': (15.0, 24.0),
    '61_180': (12.0, 21.0),
    '181_365': (9.0, 19.0),
}


class ResCompanyInsurance(models.Model):
    _inherit = 'res.company'

    def _vehicle_rental_load_insurance_pricing(self):
        """Load the no-excess tariff, correcting the rows already there."""
        Pricing = self.env['vehicle.insurance.pricing'].sudo().with_context(active_test=False)
        for company in self:
            for duration, prices in NO_FRANCHISE_PER_DAY.items():
                for driver_type, price in zip(('normal', 'special'), prices):
                    key = [('company_id', '=', company.id), ('insurance_type', '=', 'no_franchise'),
                           ('duration_range', '=', duration), ('driver_type', '=', driver_type)]
                    row = Pricing.search(key, limit=1, order='valid_from desc')
                    if row:
                        row.write({'price_per_day': price, 'active': True})
                    else:
                        Pricing.create({
                            'company_id': company.id, 'currency_id': company.currency_id.id,
                            'insurance_type': 'no_franchise', 'duration_range': duration,
                            'driver_type': driver_type, 'price_per_day': price,
                            'valid_from': INSURANCE_TARIFF_FROM,
                        })
