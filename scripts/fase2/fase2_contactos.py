# -*- coding: utf-8 -*-
"""Fase 2.4/2.5: complete customers from Pinveco's customer list (15-09-2026).

Run with: odoo shell -d <db> < fase2_contactos.py   (idempotent)
Reads CSV_PATH (columns: numero, dni, street, zip, city, country, birth_date,
license_number, license_issue, license_expiry). The CSV holds personal data:
it is not versioned and must be deleted after the run. Card data is never in it.

Rules:
- Match by normalised DNI against res.partner.vat; a DNI shared by several
  contacts is skipped (no way to know which one is right).
- Same DNI repeated in the list: the last row wins (the list is in signing-up
  order; Numero is not always numeric, e.g. C100014).
- Only empty fields are filled, nothing is overwritten.
- Dates outside 1900..2100, birth dates in the future and licences that expire
  before being issued are dropped.
- No chatter, no tracking, no mail; the stored VAT is never modified.
"""
import collections
import csv
import datetime
import re
import unicodedata

CSV_PATH = '/tmp/contactos_backfill.csv'
BATCH = 1000


def norm(value):
    return re.sub(r'[^0-9A-Z]', '', (value or '').upper())


def plain(value):
    text = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', text).strip().upper()


def parse_date(value):
    try:
        parsed = datetime.datetime.strptime(value, '%d/%m/%Y').date()
    except (TypeError, ValueError):
        return None
    return parsed if 1900 <= parsed.year <= 2100 else None


latest = {}
with open(CSV_PATH, encoding='utf-8') as handle:
    for row in csv.DictReader(handle):
        if norm(row['dni']):
            latest[norm(row['dni'])] = row

countries = {plain(c.name): c.id for c in env['res.country'].with_context(lang='es_ES').search([])}
countries.update({plain(c.name): c.id for c in env['res.country'].with_context(lang='en_US').search([])})

Partner = env['res.partner'].with_context(
    tracking_disable=True, mail_notrack=True, mail_create_nolog=True, active_test=True,
    # Setting the country re-checks the VAT already stored; some DNIs in the
    # source have a wrong check letter. We never write vat, only keep it.
    no_vat_validation=True)
fields_read = ['vat', 'is_company', 'street', 'zip', 'city', 'country_id', 'birth_date',
               'driver_license_number', 'driver_license_issue_date', 'driver_license_expiry_date']
by_vat = collections.defaultdict(list)
for partner in Partner.search_read([('vat', '!=', False)], fields_read):
    by_vat[norm(partner['vat'])].append(partner)

today = datetime.date.today()
stats = collections.Counter()
unknown_countries = collections.Counter()


def flush_batch(touched):
    """Flush with the tracking-free context, put back any VAT Odoo reformatted, commit.

    Flushing from the plain shell env would recompute peppol_* (tracked) without
    tracking_disable and log one chatter message per contact.
    """
    Partner.env.flush_all()
    for current in Partner.browse(list(touched)).read(['vat']):
        if current['vat'] != touched[current['id']]:
            env.cr.execute("UPDATE res_partner SET vat = %s WHERE id = %s",
                           (touched[current['id']], current['id']))
            stats['vat_restored'] += 1
    env.invalidate_all()
    env.cr.commit()


def driver_values(partner, row):
    vals = {}
    birth = parse_date(row['birth_date'])
    if birth and birth <= today and not partner['birth_date']:
        vals['birth_date'] = birth
    if row['license_number'] and not partner['driver_license_number']:
        vals['driver_license_number'] = row['license_number']
    issue, expiry = parse_date(row['license_issue']), parse_date(row['license_expiry'])
    if issue and expiry and expiry < issue:
        stats['dropped_bad_licence_dates'] += 1
        return vals
    current_issue, current_expiry = partner['driver_license_issue_date'], partner['driver_license_expiry_date']
    if issue and not current_issue and not (current_expiry and current_expiry < issue):
        vals['driver_license_issue_date'] = issue
    if expiry and not current_expiry and not (current_issue and expiry < current_issue):
        vals['driver_license_expiry_date'] = expiry
    return vals


touched = {}
for dni, row in latest.items():
    matches = by_vat.get(dni, [])
    if len(matches) != 1:
        stats['skip_no_match' if not matches else 'skip_shared_vat'] += 1
        continue
    partner = matches[0]
    vals = {}
    for field in ('street', 'zip', 'city'):
        if not partner[field] and row[field]:
            vals[field] = row[field]
    if not partner['country_id'] and row['country']:
        country_id = countries.get(plain(row['country']))
        if country_id:
            vals['country_id'] = country_id
        else:
            unknown_countries[row['country']] += 1
    # Most customers were imported flagged as company: the list says whether
    # there is driver data, not is_company.
    vals.update(driver_values(partner, row))
    if not vals:
        stats['nothing_to_fill'] += 1
        continue
    for field in vals:
        stats['filled_' + field] += 1
    Partner.browse(partner['id']).write(dict(vals))
    stats['updated'] += 1
    touched[partner['id']] = partner['vat']
    if len(touched) >= BATCH:
        flush_batch(touched)
        touched = {}
flush_batch(touched)
for key in sorted(stats):
    print('STAT', key, stats[key])
print('UNKNOWN_COUNTRIES', dict(unknown_countries))
