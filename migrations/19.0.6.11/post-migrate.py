# -*- coding: utf-8 -*-
"""Drop the old translations of the contract mails.

The templates are now written in Spanish; the stored es_ES translation was the
old text with raw UTC dates and would still be shown to Spanish users.
"""

TEMPLATES = ('vehicle_rental_booking_mail_template', 'email_template_vehicle_contract')


def migrate(cr, version):
    cr.execute("""
        UPDATE mail_template t
           SET body_html = jsonb_build_object('en_US', t.body_html -> 'en_US'),
               subject = jsonb_build_object('en_US', t.subject -> 'en_US'),
               name = jsonb_build_object('en_US', t.name -> 'en_US')
          FROM ir_model_data d
         WHERE d.res_id = t.id AND d.model = 'mail.template'
           AND d.module = 'vehicle_rental' AND d.name IN %s
    """, (TEMPLATES,))
