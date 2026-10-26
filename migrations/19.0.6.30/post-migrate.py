# -*- coding: utf-8 -*-
"""Starter configuration: maintenance schedules, cancellation policies and manual lead enrichment.

Approximate values (Juan, 2026-10-26): each company adjusts them later.
Only created when missing, so running it again changes nothing.
"""
import re

from markupsafe import Markup

from odoo import SUPERUSER_ID, api

SCHEDULES = [
    ('Revisión cada 30 días', 30),
    ('Revisión cada 90 días', 90),
    ('Revisión cada 180 días', 180),
    ('Revisión anual (365 días)', 365),
]

POLICIES = [
    ('Cancelación gratuita (más de 48 h antes)', Markup(
        '<p>Si el cliente cancela con más de 48 horas de antelación a la recogida, '
        'no se aplica cargo y se devuelve lo pagado.</p>')),
    ('Cancelación con menos de 48 h', Markup(
        '<p>Si el cliente cancela con menos de 48 horas de antelación a la recogida, '
        'se cobra el importe de un día de alquiler.</p>')),
    ('No presentado', Markup(
        '<p>Si el cliente no se presenta a la recogida sin avisar, se cobra el 100 % '
        'del primer día y la reserva queda anulada.</p>')),
]


SUNSET_LESSOR = re.compile(r'M[áa]laga(?:\s|&nbsp;)+Sunset(?:\s|&nbsp;)+S\.?\s?L\.?', re.IGNORECASE)


def fix_lessor_in_terms(env, sunset=None):
    """Terms of other companies were copied from Sunset and name it as the lessor."""
    sunset = sunset or env['res.company'].search([('name', '=', 'Sunset')], limit=1)
    terms = env['rental.agreement.terms'].search([('company_id', '!=', False)])
    for record in terms.filtered(lambda t: t.company_id != sunset and t.rental_terms):
        company = record.company_id
        lessor = company.name + (', con CIF %s' % company.vat if company.vat else '')
        fixed = SUNSET_LESSOR.sub(lessor, str(record.rental_terms))
        if fixed != str(record.rental_terms):
            record.rental_terms = Markup(fixed)


def fix_damage_report_names(env):
    """«Scratch Report» was translated as «Informe preliminar»."""
    names = {'vehicle_rental.action_scratch_report_template': 'Informe de daños',
             'vehicle_rental.action_vehicle_scratch_report': 'Informes de daños'}
    for xmlid, name in names.items():
        record = env.ref(xmlid, raise_if_not_found=False)
        if record:
            record.with_context(lang='es_ES').name = name


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Schedule = env['maintenance.schedule']
    for name, days in SCHEDULES:
        if not Schedule.search_count([('name', '=', name)]):
            Schedule.create({'name': name, 'maintenance_days': days})

    Policy = env['cancellation.policy']
    for company in env['res.company'].search([]):
        for title, terms in POLICIES:
            if not Policy.search_count([('title', '=', title), ('company_id', '=', company.id)]):
                Policy.create({'title': title, 'terms_and_conditions': terms, 'company_id': company.id})

    fix_lessor_in_terms(env)
    fix_damage_report_names(env)

    # Automatic enrichment spends IAP credits and overwrites customer data
    env['ir.config_parameter'].set_param('crm.iap.lead.enrich.setting', 'manual')
    cron = env.ref('crm_iap_enrich.ir_cron_lead_enrichment', raise_if_not_found=False)
    if cron:
        cron.with_context(active_test=False).active = False
    env.flush_all()
