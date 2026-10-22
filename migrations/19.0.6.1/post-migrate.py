# -*- coding: utf-8 -*-
"""Remove orphan website views that break the public site.

On 2025-12-22 the module's template files were loaded into ``ir.ui.view`` by
script, whole file included (``<?xml ... encoding?><odoo><template ...>``).
Those copies have no xmlid, share the key of the real templates and win the
website's lookup by key, so /contactus, /sunset/flota, /sunset/seguros and
/our-services answer 500: Odoo 19 cannot parse an arch carrying an XML
declaration. The real templates (with xmlid) are untouched.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT v.id, v.key
          FROM ir_ui_view v
     LEFT JOIN ir_model_data d ON d.model = 'ir.ui.view' AND d.res_id = v.id
         WHERE v.key LIKE 'vehicle_rental.%%'
           AND v.arch_db::text LIKE '%%<?xml%%'
           AND d.id IS NULL
    """)
    rows = cr.fetchall()
    if not rows:
        return
    view_ids = tuple(row[0] for row in rows)
    # Children first, so no inherited view is left pointing at a deleted parent.
    cr.execute("DELETE FROM ir_ui_view WHERE inherit_id IN %s", (view_ids,))
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (view_ids,))
    _logger.info("vehicle_rental: removed %s orphan website views: %s",
                 len(view_ids), sorted({row[1] for row in rows}))
