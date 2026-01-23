# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json, logging, base64, hmac, hashlib, subprocess, tempfile, os
from datetime import datetime

_logger = logging.getLogger(__name__)

class RentalPaymentController(http.Controller):
    @http.route('/rental/payment', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def rental_payment(self, **kw):
        try:
            category_id = int(kw.get('category_id', 0))
            selected_price_raw = kw.get('selected_price', '')
            _logger.info(f"RENTAL_PAYMENT DEBUG: selected_price raw = '{selected_price_raw}'")
            
            try:
                selected_price = float(selected_price_raw) if selected_price_raw else 0
            except (ValueError, TypeError):
                selected_price = 0
                _logger.warning(f"RENTAL_PAYMENT: selected_price invalido: '{selected_price_raw}'")
            
            if selected_price <= 0:
                _logger.warning("RENTAL_PAYMENT: selected_price no recibido o invalido, usando fallback 135")
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
            card_type = kw.get('card_type', 'debit')
            card_bin = kw.get('card_bin', '')
            
            num_days = 1
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    num_days = (end_dt - start_dt).days
                    if num_days < 1:
                        num_days = 1
                    _logger.info(f"RENTAL_PAYMENT: Calculados {num_days} dias ({start_date} - {end_date})")
                except Exception as e:
                    _logger.warning(f"RENTAL_PAYMENT: Error calculando dias: {e}, usando 1 dia")
                    num_days = 1
            
            total_price = selected_price * num_days
            _logger.info(f"RENTAL_PAYMENT: Precio/dia={selected_price}EUR x {num_days} dias = {total_price}EUR TOTAL")
            
            deposit_amount = 0
            if category_id:
                try:
                    deposit_rule = request.env['vehicle.deposit.rule'].get_deposit_amount(
                        category_id, card_type, total_price
                    )
                    deposit_amount = float(deposit_rule) if deposit_rule else 0
                    if deposit_amount > 0:
                        _logger.info(f"RENTAL_PAYMENT: Deposito calculado = {deposit_amount}EUR para tarjeta {card_type}")
                except Exception as e:
                    _logger.warning(f"RENTAL_PAYMENT: Error calculando deposito: {e}, usando 0EUR")
                    deposit_amount = 0
            
            total_with_deposit = total_price + deposit_amount
            _logger.info(f"RENTAL_PAYMENT: Total = {total_price}EUR (alquiler) + {deposit_amount}EUR (deposito) = {total_with_deposit}EUR")
            
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
                'selected_price': selected_price,
                'total_price': total_price,
                'deposit_amount': deposit_amount,
                'total_with_deposit': total_with_deposit,
                'card_type': card_type,
                'card_bin': card_bin,
                'num_days': num_days,
                'company_id': request.website.company_id.id,
            }
            
            request.session['booking_data'] = booking_data
            
            company_id = request.website.company_id.id
            redsys_provider = request.env['payment.provider'].sudo().search([
                ('code', '=', 'redsys'),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not redsys_provider:
                return "Error: No Redsys provider configured for this company"
            
            provider = redsys_provider
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
            
            import time
            timestamp_str = str(int(time.time()))
            order_number = timestamp_str[-12:].zfill(12)
            
            tx_vals = {
                'booking_data_json': json.dumps(booking_data),
                'provider_id': redsys_provider.id,
                'payment_method_id': payment_method.id,
                'amount': total_with_deposit,
                'currency_id': request.env.company.currency_id.id,
                'partner_id': request.env.user.partner_id.id if request.env.user.partner_id else request.env.ref('base.public_partner').id,
                'reference': order_number,
            }
            
            payment_tx = request.env['payment.transaction'].sudo().create(tx_vals)
            _logger.info(f"RENTAL_PAYMENT: Created transaction ID {payment_tx.id} with reference {order_number}, amount={total_with_deposit}EUR")
            
            merchant_code = redsys_provider.redsys_merchant_code
            terminal = '1'
            secret_key_b64 = redsys_provider.redsys_secret_key
            
            amount_cents = int(total_with_deposit * 100)
            currency = '978'
            
            domain = request.httprequest.host
            merchant_data = {
                'Ds_Merchant_Amount': str(amount_cents),
                'Ds_Merchant_Currency': currency,
                'Ds_Merchant_Order': order_number,
                'Ds_Merchant_MerchantCode': merchant_code,
                'Ds_Merchant_Terminal': terminal,
                'Ds_Merchant_TransactionType': '0',
                'Ds_Merchant_MerchantURL': f'https://{domain}/payment/redsys/webhook',
                'Ds_Merchant_UrlOK': f'https://{domain}/rental/success',
                'Ds_Merchant_UrlKO': f'https://{domain}/rental/error',
            }
            
            _logger.info(f"RENTAL_PAYMENT: Merchant data = {merchant_data}")
            
            merchant_json = json.dumps(merchant_data, separators=(',', ':'))
            merchant_b64 = base64.b64encode(merchant_json.encode('utf-8')).decode('ascii')
            
            _logger.info(f"RENTAL_PAYMENT: Merchant JSON = {merchant_json}")
            _logger.info(f"RENTAL_PAYMENT: Merchant B64 = {merchant_b64}")
            
            secret_key_str = str(secret_key_b64).strip()
            padding = 4 - len(secret_key_str) % 4
            if padding != 4:
                secret_key_str += '=' * padding
            
            try:
                secret_decoded = base64.b64decode(secret_key_str)
            except Exception as e:
                _logger.error(f"RENTAL_PAYMENT: Error decodificando secret_key: {e}")
                return f"<h1>Error: Configuracion de Redsys invalida</h1><p>La clave secreta de Redsys no es valida. Por favor, contacte con el administrador.</p>"
            
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
            
            signature = base64.b64encode(
                hmac.new(derived_key, merchant_b64.encode('ascii'), hashlib.sha256).digest()
            ).decode('ascii')
            
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
    
    @http.route('/rental/success', auth='public', website=True, type='http', methods=['GET', 'POST'])
    def rental_payment_success(self, **kw):
        try:
            _logger.info(f"RENTAL_PAYMENT SUCCESS: Parametros recibidos = {kw}")
            booking_data = request.session.get('booking_data')
            
            return f"""
            <html>
                <head>
                    <title>Pago Exitoso</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .success {{ color: green; font-size: 24px; }}
                        .info {{ margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="success">OK Pago realizado correctamente</div>
                    <div class="info">
                        <p>Tu reserva ha sido procesada exitosamente.</p>
                        <p>Pronto recibiras un correo de confirmacion.</p>
                        <a href="/">Volver a inicio</a>
                    </div>
                </body>
            </html>
            """
        except Exception as e:
            _logger.error(f"ERROR en rental_payment_success: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    @http.route('/rental/error', auth='public', website=True, type='http', methods=['GET', 'POST'])
    def rental_payment_error(self, **kw):
        try:
            _logger.error(f"RENTAL_PAYMENT ERROR: Parametros de error recibidos = {kw}")
            
            return f"""
            <html>
                <head>
                    <title>Pago Cancelado</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .error {{ color: red; font-size: 24px; }}
                        .info {{ margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="error">X El pago ha sido cancelado o ha fallado</div>
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

    @http.route('/rental/validate-bin', auth='public', type='http', methods=['POST'], csrf=False)
    def validate_bin(self):
        """Valida un BIN de tarjeta usando Freebinchecker desde el servidor"""
        try:
            import json
            # Obtener los datos del body JSON
            try:
                body_data = json.loads(request.httprequest.data.decode('utf-8'))
                bin_number = body_data.get('bin', '')
            except:
                bin_number = request.params.get('bin', '')
            
            _logger.info(f"VALIDATE_BIN: body_data = {request.httprequest.data}")
            _logger.info(f"VALIDATE_BIN: BIN recibido = '{bin_number}'")
            
            if not bin_number or len(bin_number) < 6:
                _logger.warning(f"VALIDATE_BIN: BIN inválido o muy corto: '{bin_number}'")
                return request.make_response(json.dumps({'error': 'BIN inválido', 'card_type': None}), 
                                          [('Content-Type', 'application/json')])
            
            # Llamar a Freebinchecker desde el servidor (sin problemas CORS)
            import requests
            try:
                url = f'https://lookup.binlist.net/{bin_number}'
                _logger.info(f"VALIDATE_BIN: Llamando a {url}")
                response = requests.get(url, timeout=5)
                _logger.info(f"VALIDATE_BIN: Response status = {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    _logger.info(f"VALIDATE_BIN: Response data = {response_data}")
                    card_type = response_data.get('type', 'unknown').lower()
                    _logger.info(f"VALIDATE_BIN: Card type detectado = '{card_type}'")
                    
                    if card_type in ['credit', 'debit']:
                        result = {
                            'success': True,
                            'card_type': card_type,
                            'bin': bin_number,
                            'scheme': response_data.get('scheme', 'unknown'),
                            'type': response_data.get('type', 'unknown'),
                        }
                        _logger.info(f"VALIDATE_BIN: Retornando resultado exitoso: {result}")
                        return request.make_response(json.dumps(result), 
                                                  [('Content-Type', 'application/json')])
                    else:
                        _logger.warning(f"VALIDATE_BIN: Tipo de tarjeta no soportado: '{card_type}'")
                        return request.make_response(json.dumps({'error': 'Tipo de tarjeta no soportado', 'card_type': None}), 
                                                  [('Content-Type', 'application/json')])
                else:
                    _logger.warning(f"VALIDATE_BIN: BIN no encontrado (status {response.status_code})")
                    return request.make_response(json.dumps({'error': f'BIN no encontrado (status {response.status_code})', 'card_type': None}), 
                                              [('Content-Type', 'application/json')])
            except requests.exceptions.RequestException as e:
                _logger.error(f"VALIDATE_BIN: Error de requests con Freebinchecker: {e}", exc_info=True)
                return request.make_response(json.dumps({'error': 'Error al validar BIN', 'card_type': None}), 
                                          [('Content-Type', 'application/json')])
        
        except Exception as e:
            _logger.error(f"ERROR en validate_bin: {str(e)}", exc_info=True)
            return request.make_response(json.dumps({'error': str(e), 'card_type': None}), 
                                      [('Content-Type', 'application/json')])
