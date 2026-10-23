# -*- coding: utf-8 -*-
"""Let the booking mail template be reloaded from the module.

It was loaded once with noupdate and never edited in production, so the new
Spanish text with local dates would never reach the database otherwise.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_data SET noupdate = false
         WHERE module = 'vehicle_rental' AND model = 'mail.template'
           AND name = 'vehicle_rental_booking_mail_template'
    """)
