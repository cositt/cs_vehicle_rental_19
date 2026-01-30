# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import json
import time
import traceback

_logger = logging.getLogger(__name__)

class PaymentGatewayController(http.Controller):
    @http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_payment_gateway(self, **kw):
        """Create payment transaction for vehicle rental"""
        
        try:
            # Obtener datos de la reserva
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
            
            # Guardar en sesión
            request.session['booking_data'] = booking_data
            
            # Obtener provider Redsys
            providers = request.env['payment.provider'].search([('code', '=', 'redsys')], limit=1)
            if not providers:
                providers = request.env['payment.provider'].search([], limit=1)
            
            if not providers:
                raise Exception("No payment provider available")
            
            _logger.info(f"DEBUG: Using provider {providers.name} (ID {providers.id})")
            
            # Obtener payment_method para el provider
            payment_methods = request.env['payment.method'].search([
                ('provider_ids', 'in', providers.id)
            ], limit=1)
            
            if not payment_methods:
                _logger.info(f"DEBUG: No payment.method found for provider {providers.id}, creating one")
                # Si no existe, crear uno genérico
                # Imagen base64 mínima (1x1 PNG blanco)
                minimal_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
                
                payment_methods = request.env['payment.method'].sudo().create({
                    'name': 'Credit/Debit Card',
                    'code': 'card',
                    'image': minimal_image,
                    'provider_ids': [(4, providers.id)],
                })
                _logger.info(f"DEBUG: Created payment.method {payment_methods.id}")
            else:
                _logger.info(f"DEBUG: Found payment.method {payment_methods.id}")
            
            # Crear payment.transaction
            tx_vals = {
                'booking_data_json': json.dumps(booking_data),
                'provider_id': providers.id,
                'payment_method_id': payment_methods.id,
                'amount': selected_price,
                'currency_id': request.env.company.currency_id.id,
                'partner_id': request.env.user.partner_id.id,
                'reference': order_number,
            }
            
            _logger.info(f"DEBUG: Creating payment.transaction with values: {tx_vals}")
            
            payment_tx = request.env['payment.transaction'].sudo().create(tx_vals)
            
            _logger.info(f"DEBUG RENTAL PAYMENT: payment.transaction created with ID {payment_tx.id}")
            
            # Redirigir al formulario de pago
            return request.redirect(f'/payment/process/{payment_tx.id}')
            
        except Exception as e:
            error_detail = traceback.format_exc()
            _logger.error(f"ERROR en rental_payment_gateway:\n{error_detail}")
            # Devolver como texto plano para ver el error en curl
            return error_detail, 500, [('Content-Type', 'text/plain')]

