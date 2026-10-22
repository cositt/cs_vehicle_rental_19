# -*- coding: utf-8 -*-
from odoo import api, models

RENTAL_VAT = 21.0
OPEN_CONTRACT_STATES = ('a_draft', 'b_in_progress')
# Products priced with VAT included in the tariff
VAT_INCLUDED_PRODUCTS = (
    'vehicle_rental.vehicle_day_wise_rent',
    'vehicle_rental.vehicle_km_wise_rent',
    'vehicle_rental.vehicle_mi_wise_rent',
    'vehicle_rental.vehicle_rent_charge',
    'vehicle_rental.vehicle_rent_extra_charge',
) + tuple(f'vehicle_rental.product_rental_tipo_{code}' for code in 'acfpgmbsqez')


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _vehicle_rental_sale_tax(self):
        """Sale tax of 21 % included in the price, or an empty recordset."""
        self.ensure_one()
        return self.env['account.tax'].sudo().search([
            ('company_id', '=', self.id),
            ('type_tax_use', '=', 'sale'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', RENTAL_VAT),
            ('price_include_override', '=', 'tax_included'),
        ], limit=1)

    def _vehicle_rental_ensure_sale_tax(self):
        """Tariff prices include VAT: copy the company's 21 % sale tax as included.

        The copy keeps the tax group and the repartition accounts of the
        original. Companies without a 21 % sale tax (no chart of accounts) get
        nothing, and their rentals stay without tax as before.
        """
        self.ensure_one()
        tax = self._vehicle_rental_sale_tax()
        if tax:
            return tax
        base = self.account_sale_tax_id
        if not base or base.amount_type != 'percent' or base.amount != RENTAL_VAT:
            base = self.env['account.tax'].sudo().search([
                ('company_id', '=', self.id), ('type_tax_use', '=', 'sale'),
                ('amount_type', '=', 'percent'), ('amount', '=', RENTAL_VAT),
            ], limit=1)
        if not base:
            return base
        return base.sudo().copy({
            'name': '21% IVA incluido (alquiler)',
            'price_include_override': 'tax_included',
        })

    def _vehicle_rental_apply_sale_tax(self):
        """Put the VAT-included tax on the rental products and the open contracts.

        Deposit, damages and cancellation products are left as they are. Other
        sale taxes of the same company are replaced on the rental products, so
        an extension no longer adds 21 % on top. Closed contracts keep their
        history.
        """
        for company in self:
            tax = company._vehicle_rental_ensure_sale_tax()
            if not tax:
                continue
            for xmlid in VAT_INCLUDED_PRODUCTS:
                record = self.env.ref(xmlid, raise_if_not_found=False)
                if not record:
                    continue
                template = record.product_tmpl_id if record._name == 'product.product' else record
                others = template.sudo().taxes_id.filtered(lambda t: t.company_id == company)
                template.sudo().write({'taxes_id': [(3, t.id) for t in others] + [(4, tax.id)]})
            contracts = self.env['vehicle.contract'].sudo().with_context(active_test=False).search([
                ('company_id', '=', company.id),
                ('status', 'in', OPEN_CONTRACT_STATES),
                ('tax_ids', '=', False),
            ])
            contracts.write({'tax_ids': [(6, 0, tax.ids)]})


SURCHARGES_VAT_INCLUDED = ('vehicle_rental.surcharge_out_of_hours', 'vehicle_rental.surcharge_fuel_not_full')
SURCHARGES_PLUS_VAT = ('vehicle_rental.surcharge_other_branch', 'vehicle_rental.surcharge_lost_beacon')


class ResCompanySurcharges(models.Model):
    _inherit = 'res.company'

    def _vehicle_rental_load_surcharges(self):
        """Set the VAT of the tariff surcharges in each company: included or + 21 %."""
        for company in self:
            included = company._vehicle_rental_ensure_sale_tax()
            excluded = self.env['account.tax'].sudo().search([
                ('company_id', '=', company.id), ('type_tax_use', '=', 'sale'),
                ('amount_type', '=', 'percent'), ('amount', '=', RENTAL_VAT),
                ('price_include_override', '!=', 'tax_included'),
            ], limit=1)
            for xmlids, tax in ((SURCHARGES_VAT_INCLUDED, included), (SURCHARGES_PLUS_VAT, excluded)):
                if not tax:
                    continue
                for xmlid in xmlids:
                    product = self.env.ref(xmlid, raise_if_not_found=False)
                    if not product:
                        continue
                    template = product.product_tmpl_id.sudo()
                    others = template.taxes_id.filtered(lambda t: t.company_id == company)
                    template.write({'taxes_id': [(3, t.id) for t in others] + [(4, tax.id)]})


class VehicleContractTax(models.Model):
    """Rental lines carry the VAT-included tax of the contract's company.

    Rent, insurance and extra km are priced with VAT included in the tariff,
    so they all take the contract tax; other products bring their own taxes,
    filtered by the company of the contract.
    """
    _inherit = 'vehicle.contract'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tax_ids'):
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                tax = company._vehicle_rental_sale_tax()
                if tax:
                    vals['tax_ids'] = [(6, 0, tax.ids)]
        return super().create(vals_list)

    def _taxes_for(self, product):
        """Taxes of the product that belong to the company of the contract."""
        self.ensure_one()
        return product.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

    def _extra_service_taxes(self, product):
        """Tax of the service product, or the VAT-included tax of the contract."""
        self.ensure_one()
        return self._taxes_for(product) or self.tax_ids
