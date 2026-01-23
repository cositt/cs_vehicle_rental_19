# -*- coding: utf-8 -*-
"""
Controlador para las páginas de éxito y error de Redsys
"""
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class RentalPaymentSuccessController(http.Controller):
    
    @http.route('/rental/success', auth='public', website=True, type='http', methods=['GET', 'POST'])
    def rental_payment_success(self, **kw):
        """Página de éxito después del pago con Redsys"""
        _logger.warning(f"RENTAL_PAYMENT SUCCESS: ENDPOINT LLAMADO - Parámetros recibidos = {kw}")
        try:
            # Obtener booking_data de la sesión
            booking_data = request.session.get('booking_data')
            _logger.warning(f"RENTAL_PAYMENT SUCCESS: Booking data = {booking_data}")
            
            if booking_data:
                _logger.info(f"RENTAL_PAYMENT SUCCESS: Booking data encontrado en sesión")
                
                # Buscar la transacción de pago más reciente SIN booking creado
                payment_tx = request.env['payment.transaction'].sudo().search([
                    ('provider_code', '=', 'redsys'),
                    ('booking_created', '=', False),
                ], limit=1, order='create_date desc')
                
                _logger.warning(f"RENTAL_PAYMENT SUCCESS: Payment TX encontrada: {payment_tx}")
                
                if payment_tx:
                    _logger.info(f"RENTAL_PAYMENT SUCCESS: Transacción encontrada TX:{payment_tx.id}")
                    
                    # Marcar como done si aún no lo está
                    if payment_tx.state != 'done':
                        payment_tx.write({'state': 'done'})
                        _logger.info(f"RENTAL_PAYMENT SUCCESS: Transacción marcada como done TX:{payment_tx.id}")
                    
                    # Llamar al método que crea el lead
                    try:
                        payment_tx._apply_updates({})
                        _logger.info(f"RENTAL_PAYMENT SUCCESS: Lead creado desde _apply_updates TX:{payment_tx.id}")
                    except Exception as e:
                        _logger.error(f"RENTAL_PAYMENT SUCCESS: Error en _apply_updates: {str(e)}", exc_info=True)
                else:
                    _logger.warning("RENTAL_PAYMENT SUCCESS: No se encontró transacción de pago")
            else:
                _logger.warning("RENTAL_PAYMENT SUCCESS: No hay booking_data en sesión")
            
            return request.redirect('/')
        except Exception as e:
            _logger.error(f"ERROR en rental_payment_success: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    @http.route('/rental/error', auth='public', website=True, type='http', methods=['GET', 'POST'])
    def rental_payment_error(self, **kw):
        """Página de error después del pago con Redsys"""
        try:
            _logger.error(f"RENTAL_PAYMENT ERROR: Parámetros de error recibidos = {kw}")
            
            return """
            <html>
                <head>
                    <title>Pago Cancelado</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .error { color: red; font-size: 24px; }
                        .info { margin-top: 20px; }
                    </style>
                </head>
                <body>
                    <div class="error">✗ El pago ha sido cancelado o ha fallado</div>
                    <div class="info">
                        <p>Puedes intentar de nuevo.</p>
                        <a href="/web/booking-enquiry">Volver a reservar</a>
                    </div>
                </body>
            </html>
            """
        except Exception as e:
            _logger.error(f"ERROR en rental_payment_error: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
