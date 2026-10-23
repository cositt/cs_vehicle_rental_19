# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.


def _display_rental_notification(message, message_type):
    """Helper method to display a notification."""
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'type': message_type,
            'message': message,
            'sticky': False,
        }
    }


def format_es_number(value, decimals=0):
    """Number with Spanish separators: 18.000 or 1.234,50."""
    text = f"{value or 0.0:,.{decimals}f}"
    return text.translate(str.maketrans({',': '.', '.': ','}))
