# -*- coding: utf-8 -*-
from odoo.addons.website.controllers.main import Website
from odoo import http
from odoo.http import request
import json

class RentalPaymentGateway(http.Controller):
    
    @http.route('/web/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_payment_gateway(self, **kw):
        """
        Create payment.transaction for vehicle rental booking.
        This endpoint creates a payment.transaction with Redsys provider.
        The payment_redsys module will handle the form generation and submission.
        """
        try:
            import logging
            import time
            _logger = logging.getLogger(__name__)
            
            # Obtener datos de la reserva desde el formulario
            category_id = int(kw.get('category_id', 0))
            selected_price = float(kw.get('selected_price', 0))
            customer_name = kw.get('customer_name', '')
            customer_email = kw.get('customer_email', '')
            customer_phone = kw.get('customer_phone', '')
            start_date = kw.get('start_date', '')
            end_date = kw.get('end_date', '')
            order_number = kw.get('order_number', f'RENT-{int(time.time())}')
            
            _logger.info(f"DEBUG RENTAL PAYMENT: Creating payment.transaction for order {order_number}")
            
            # Preparar datos de booking
            booking_data = {
                'category_id': category_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'start_date': start_date,
                'end_date': end_date,
            }
            
            # Guardar en sesión para que el webhook pueda acceder
            request.session['booking_data'] = booking_data
            
            # Crear payment.transaction
            payment_tx = request.env['payment.transaction'].sudo().create({
                'provider_id': request.env.ref('payment_redsys.payment_provider_redsys').id,
                'amount': selected_price,
                'currency_id': request.env.company.currency_id.id,
                'partner_id': request.env.user.partner_id.id,
                'reference': order_number,
                'state': 'draft',
                'booking_data_json': json.dumps(booking_data),
            })
            
            _logger.info(f"DEBUG RENTAL PAYMENT: payment.transaction created with ID {payment_tx.id}")
            
            # Redirigir al formulario de pago
            return request.redirect(f'/payment/process/{payment_tx.id}')
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"ERROR en rental_payment_gateway: {str(e)}", exc_info=True)
            return request.render('website.error', {
                'error': f'Error creating payment: {str(e)}'
            })
