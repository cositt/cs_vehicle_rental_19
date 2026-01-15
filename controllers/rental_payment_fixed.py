# -*- coding: utf-8 -*-
"""
Controlador para procesar pagos de alquiler de vehículos con Redsys
"""
from odoo import http
from odoo.http import request
import json
import logging
import base64
import hmac
import hashlib
import subprocess
import tempfile
import os
from datetime import datetime

_logger = logging.getLogger(__name__)

class RentalPaymentController(http.Controller):
    @http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_payment(self, **kw):
        """Procesar pago de alquiler con Redsys"""
        try:
            # Obtener datos
            category_id = int(kw.get('category_id', 0))
            
            # DEBUG: Log del valor raw de selected_price
            selected_price_raw = kw.get('selected_price', '')
            _logger.info(f"RENTAL_PAYMENT DEBUG: selected_price raw = '{selected_price_raw}'")
            
            # Convertir selected_price con validación
            try:
                selected_price = float(selected_price_raw) if selected_price_raw else 0
            except (ValueError, TypeError):
                selected_price = 0
                _logger.warning(f"RENTAL_PAYMENT: selected_price inválido: '{selected_price_raw}'")
            
            if selected_price <= 0:
                _logger.warning("RENTAL_PAYMENT: selected_price no recibido o inválido, usando fallback 135€")
                selected_price = 135.0
            
            customer_name = kw.get('customer_name', '')
            customer_email = kw.get('customer_email', '')
            customer_phone = kw.get('customer_phone', '')
            start_date = kw.get('start_date', '')
            end_date = kw.get('end_date', '')
            start_time = kw.get('start_time', '')
            end_time = kw.get('end_time', '')
            customer_dni = kw.get('customer_dni', '')
            customer_dni_expiry_date = kw.get('customer_dni_expiry_date', '')
            location = kw.get('location', '')
            
            # FIX 1: Calcular número de días de alquiler
            num_days = 1
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    num_days = (end_dt - start_dt).days
                    if num_days < 1:
                        num_days = 1
                    _logger.info(f"RENTAL_PAYMENT: Calculados {num_days} días ({start_date} → {end_date})")
                except Exception as e:
                    _logger.warning(f"RENTAL_PAYMENT: Error calculando días: {e}, usando 1 día")
                    num_days = 1
            
            # FIX 1: Calcular precio TOTAL (precio/día × días)
            total_price = selected_price * num_days
            _logger.info(f"RENTAL_PAYMENT: Precio/día={selected_price}€ × {num_days} días = {total_price}€ TOTAL")
            
            # Preparar datos de booking (guardar precio/día para el contrato)
            booking_data = {
                'category_id': category_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'start_date': start_date,
                'end_date': end_date,
                'start_time': start_time,
                'end_time': end_time,
                'customer_dni': customer_dni,
                'customer_dni_expiry_date': customer_dni_expiry_date,
                'location': location,
                'selected_price': selected_price,  # Precio por día (para el contrato)
                'total_price': total_price,        # Precio total cobrado
                'num_days': num_days,              # Número de días
            }
            
            # Guardar en sesión
            request.session['booking_data'] = booking_data
            
            # Obtener provider Redsys
            provider = request.env['payment.provider'].sudo().search([('code', '=', 'redsys')], limit=1)
            if not provider:
                return "Error: No Redsys provider found"
            
            # Obtener o crear payment_method
            payment_method = request.env['payment.method'].sudo().search([
                ('provider_ids', 'in', provider.id)
            ], limit=1)
            
            if not payment_method:
                payment_method = request.env['payment.method'].sudo().create({
                    'name': 'Credit/Debit Card',
                    'code': 'card',
                    'image': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==',
                    'provider_ids': [(4, provider.id)],
                })
            
            # Crear transacción de pago
            import time
            
            # Generar order_number PRIMERO (Redsys requiere 12 dígitos numéricos)
            timestamp_str = str(int(time.time()))
            order_number = timestamp_str[-12:].zfill(12)  # Últimos 12 dígitos rellenados a 12
            
            # FIX 1: Usar total_price en la transacción
            tx_vals = {
                'booking_data_json': json.dumps(booking_data),
                'provider_id': provider.id,
                'payment_method_id': payment_method.id,
                'amount': total_price,  # CAMBIADO: Usar precio TOTAL
                'currency_id': request.env.company.currency_id.id,
                'partner_id': request.env.user.partner_id.id if request.env.user.partner_id else request.env.ref('base.public_partner').id,
                'reference': order_number,
            }
            
            payment_tx = request.env['payment.transaction'].sudo().create(tx_vals)
            _logger.info(f"RENTAL_PAYMENT: Created transaction ID {payment_tx.id} with reference {order_number}, amount={total_price}€")
            
            # Ahora generar el formulario de Redsys
            merchant_code = '369056973'
            terminal = '1'
            secret_key_b64 = 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'
            
            # FIX 1: Usar total_price para Redsys
            amount_cents = int(total_price * 100)
            currency = '978'  # EUR
            
            # Preparar datos del merchant
            merchant_data = {
                'Ds_Merchant_Amount': str(amount_cents),
                'Ds_Merchant_Currency': currency,
                'Ds_Merchant_Order': order_number,
                'Ds_Merchant_MerchantCode': merchant_code,
                'Ds_Merchant_Terminal': terminal,
                'Ds_Merchant_TransactionType': '0',
                'Ds_Merchant_MerchantURL': 'https://sunsetrent.es/payment/redsys/webhook',
                'Ds_Merchant_UrlOK': 'https://sunsetrent.es/rental/success',
                'Ds_Merchant_UrlKO': 'https://sunsetrent.es/rental/error',
            }
            
            # Codificar a base64
            merchant_json = json.dumps(merchant_data, separators=(',', ':'))
            merchant_b64 = base64.b64encode(merchant_json.encode('utf-8')).decode('ascii')
            
            # Derivar clave 3DES-CBC
            secret_decoded = base64.b64decode(secret_key_b64)
            order_bytes = order_number.encode('utf-8')
            pad = (-len(order_bytes)) % 8
            order_padded = order_bytes + b'\x00' * pad
            
            with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f_order:
                f_order.write(order_padded)
                order_path = f_order.name
            
            try:
                derived_path = tempfile.mktemp()
                key_hex = secret_decoded.hex()
                
                subprocess.check_call([
                    'openssl', 'enc', '-des-ede3-cbc',
                    '-K', key_hex,
                    '-iv', '0000000000000000',
                    '-nopad',
                    '-in', order_path,
                    '-out', derived_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                with open(derived_path, 'rb') as f:
                    derived_key = f.read()
                
                os.unlink(derived_path)
            finally:
                os.unlink(order_path)
            
            # Generar firma
            signature = base64.b64encode(
                hmac.new(derived_key, merchant_b64.encode('ascii'), hashlib.sha256).digest()
            ).decode('ascii')
            
            # Generar formulario HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Redirigiendo a Redsys...</title>
            </head>
            <body onload="document.forms[0].submit()">
                <form name="redsys" method="POST" action="https://sis-t.redsys.es:25443/sis/realizarPago">
                    <input type="hidden" name="Ds_SignatureVersion" value="HMAC_SHA256_V1">
                    <input type="hidden" name="Ds_MerchantParameters" value="{merchant_b64}">
                    <input type="hidden" name="Ds_Signature" value="{signature}">
                    <noscript>
                        <input type="submit" value="Continuar">
                    </noscript>
                </form>
                <p>Redirigiendo a Redsys...</p>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            _logger.error(f"ERROR en rental_payment: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
