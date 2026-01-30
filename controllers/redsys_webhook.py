# -*- coding: utf-8 -*-
"""
Webhook para recibir confirmaciones de pago de Redsys
"""
from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class RedsysWebhookController(http.Controller):
    
    @http.route('/payment/redsys/webhook', auth='public', type='json', methods=['POST'], csrf=False)
    def redsys_webhook(self, **kw):
        """Recibir confirmación de pago de Redsys"""
        try:
            _logger.info(f"REDSYS WEBHOOK: Datos recibidos = {kw}")
            
            # Buscar la transacción por número de pedido (order_number)
            order_number = kw.get('Ds_Order') or kw.get('order_number')
            
            if not order_number:
                _logger.error("REDSYS WEBHOOK: No order_number recibido")
                return {'status': 'error', 'message': 'No order_number'}
            
            # Buscar la transacción de pago
            payment_tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', order_number)
            ], limit=1)
            
            if not payment_tx:
                _logger.error(f"REDSYS WEBHOOK: Transacción no encontrada para order {order_number}")
                return {'status': 'error', 'message': 'Transaction not found'}
            
            _logger.info(f"REDSYS WEBHOOK: Transacción encontrada TX:{payment_tx.id}")
            
            # Si el pago está confirmado en Redsys, marcar como done
            if payment_tx.state != 'done':
                payment_tx.write({'state': 'done'})
                _logger.info(f"REDSYS WEBHOOK: Transacción marcada como done TX:{payment_tx.id}")
            
            # Trigger manual de _apply_updates para crear el lead
            payment_tx._apply_updates({})
            
            return {'status': 'success', 'transaction_id': payment_tx.id}
            
        except Exception as e:
            _logger.error(f"REDSYS WEBHOOK: Error {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
    
    @http.route('/rental/manual-webhook', auth='public', type='http', methods=['GET'], csrf=False)
    def manual_webhook_trigger(self, **kw):
        """Endpoint para disparar manualmente el webhook (SOLO PARA TESTING)"""
        try:
            # Obtener el últim order_number de los logs o parámetro
            order_number = kw.get('order_number')
            
            if not order_number:
                # Buscar la transacción más reciente sin booking_created
                payment_tx = request.env['payment.transaction'].sudo().search([
                    ('provider_code', '=', 'redsys'),
                    ('booking_created', '=', False),
                    ('state', 'in', ['authorized', 'done'])
                ], limit=1, order='create_date desc')
            else:
                payment_tx = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', order_number)
                ], limit=1)
            
            if not payment_tx:
                return "<h1>No transaction found</h1>"
            
            _logger.info(f"MANUAL WEBHOOK: Disparando para TX:{payment_tx.id}")
            
            # Marcar como done si no lo está
            if payment_tx.state != 'done':
                payment_tx.write({'state': 'done'})
            
            # Crear el lead
            payment_tx._apply_updates({})
            
            return f"<h1>Webhook disparado para TX:{payment_tx.id}</h1><p>Lead debería haber sido creado.</p>"
            
        except Exception as e:
            _logger.error(f"MANUAL WEBHOOK: Error {str(e)}", exc_info=True)
            return f"<h1>Error: {str(e)}</h1>"
