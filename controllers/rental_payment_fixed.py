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
            # VALIDACIÓN DE SEGURIDAD: Verificar que el BIN sea el mismo que fue validado
            validated_bin = request.session.get('validated_bin')
            validated_card_type = request.session.get('validated_card_type')
            card_bin_received = kw.get('card_bin', '')
            card_type_received = kw.get('card_type', '')
            
            _logger.info(f"RENTAL_PAYMENT: Validando tarjeta - BIN validado={validated_bin}, BIN recibido={card_bin_received}")
            
            # Si no hay BIN validado en sesión o no coincide, rechazar el pago
            if not validated_bin or validated_bin != card_bin_received:
                _logger.warning(f"RENTAL_PAYMENT SEGURIDAD: Intento de pago con BIN diferente o no validado")
                return """
                <html>
                    <head>
                        <title>Error de Seguridad</title>
                        <meta charset="UTF-8">
                        <style>
                            body { font-family: Arial, sans-serif; padding: 40px; background-color: #f5f5f5; }
                            .error-container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                            h1 { color: #dc3545; margin-top: 0; }
                            p { color: #666; line-height: 1.6; }
                            .error-details { background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 4px; margin: 20px 0; }
                            a { color: #0c63e4; text-decoration: none; }
                            a:hover { text-decoration: underline; }
                        </style>
                    </head>
                    <body>
                        <div class="error-container">
                            <div style="font-size: 60px; margin-bottom: 20px;">⚠️</div>
                            <h1>Error de Seguridad</h1>
                            <p>Lo sentimos, no pudimos procesar tu pago por motivos de seguridad.</p>
                            <div class="error-details">
                                <strong>Razón:</strong> Debes usar la misma tarjeta que validaste anteriormente.
                                <br><br>
                                Por favor, regresa al formulario de reserva y valida nuevamente con la tarjeta que deseas usar para el pago.
                            </div>
                            <p><a href="/web/booking-enquiry">← Volver al formulario de reserva</a></p>
                        </div>
                    </body>
                </html>
                """
            
            # Validar que el card_type sea válido
            if card_type_received not in ['credit', 'debit']:
                _logger.warning(f"RENTAL_PAYMENT SEGURIDAD: card_type inválido: {card_type_received}")
                return "Error: Tipo de tarjeta no válido"
            
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
                    deposit_rule = request.env['vehicle.deposit.rule'].sudo().get_deposit_amount(
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
            is_development = 'localhost' in domain or '127.0.0.1' in domain
            
            # Para desarrollo, usar localhost. Para producción, usar SUNSETRENT_DOMAIN
            if is_development:
                success_url = f'http://{domain}/rental/success'
                error_url = f'http://{domain}/rental/error'
                _logger.info(f"RENTAL_PAYMENT: Modo DESARROLLO - URLs locales: success={success_url}")
            else:
                # TODO PRODUCCIÓN: Reemplazar con dominio real
                # success_url = f'https://sunsetrent.com/rental/success'
                # error_url = f'https://sunsetrent.com/rental/error'
                success_url = f'https://{domain}/rental/success'
                error_url = f'https://{domain}/rental/error'
                _logger.warning(f"RENTAL_PAYMENT: Modo PRODUCCIÓN - Asegúrate de que el dominio sea correcto: {success_url}")
            
            merchant_data = {
                'Ds_Merchant_Amount': str(amount_cents),
                'Ds_Merchant_Currency': currency,
                'Ds_Merchant_Order': order_number,
                'Ds_Merchant_MerchantCode': merchant_code,
                'Ds_Merchant_Terminal': terminal,
                'Ds_Merchant_TransactionType': '0',
                'Ds_Merchant_MerchantURL': f'https://{domain}/payment/redsys/webhook',
                'Ds_Merchant_UrlOK': success_url,
                'Ds_Merchant_UrlKO': error_url,
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
            
            if booking_data:
                try:
                    # Crear lead automáticamente desde los datos de booking
                    lead_vals = {
                        'name': f"Reserva: {booking_data.get('customer_name', 'N/A')} ({booking_data.get('start_date', 'N/A')})",
                        'partner_name': booking_data.get('customer_name', ''),
                        'email_from': booking_data.get('customer_email', ''),
                        'phone': booking_data.get('customer_phone', ''),
                        'description': f"""
Reserva de vehículo completada:
- Categoría: {booking_data.get('category_id', 'N/A')}
- Fechas: {booking_data.get('start_date', 'N/A')} a {booking_data.get('end_date', 'N/A')}
- Ubicación: {booking_data.get('location', 'N/A')}
- Precio alquiler: {booking_data.get('total_price', 0)}€
- Depósito: {booking_data.get('deposit_amount', 0)}€
- Total pagado: {booking_data.get('total_with_deposit', 0)}€
- Tipo tarjeta: {booking_data.get('card_type', 'N/A')}
- DNI: {booking_data.get('customer_dni', 'N/A')}
                        """,
                        'type': 'opportunity',
                    }
                    
                    lead = request.env['crm.lead'].sudo().create(lead_vals)
                    _logger.info(f"RENTAL_PAYMENT SUCCESS: Lead creado exitosamente - ID {lead.id}")
                    
                except Exception as e:
                    _logger.warning(f"RENTAL_PAYMENT SUCCESS: Error creando lead: {e}")
                    # Continuar incluso si falla la creación del lead
            
            success_html = """
            <html>
                <head>
                    <title>Pago Exitoso</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .success { color: green; font-size: 24px; }
                        .info { margin-top: 20px; }
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
            
            return success_html
        except Exception as e:
            _logger.error(f"ERROR en rental_payment_success: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"
    
    @http.route('/rental/error', auth='public', website=True, type='http', methods=['GET', 'POST'])
    def rental_payment_error(self, **kw):
        try:
            _logger.error(f"RENTAL_PAYMENT ERROR: Parametros de error recibidos = {kw}")
            
            error_html = """
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
                    <div class="error">X El pago ha sido cancelado o ha fallado</div>
                    <div class="info">
                        <p>Puedes intentar de nuevo.</p>
                        <a href="/web/booking-enquiry">Volver a reservar</a>
                    </div>
                </body>
            </html>
            """
            
            return error_html
        except Exception as e:
            _logger.error(f"ERROR en rental_payment_error: {str(e)}", exc_info=True)
            return f"Error: {str(e)}"

    @http.route('/rental/validate-bin', auth='public', type='http', methods=['POST'], csrf=False)
    def validate_bin(self):
        """Valida un BIN de tarjeta usando binlist.net (5 solicitudes/hora) con cache indefinido"""
        try:
            import json
            import requests
            
            # Obtener los datos del body JSON
            try:
                body_data = json.loads(request.httprequest.data.decode('utf-8'))
                bin_number = body_data.get('bin', '')
            except:
                bin_number = request.params.get('bin', '')
            
            _logger.info(f"VALIDATE_BIN: BIN recibido = '{bin_number}'")
            
            if not bin_number or len(bin_number) < 6:
                _logger.warning(f"VALIDATE_BIN: BIN inválido o muy corto: '{bin_number}'")
                return request.make_response(json.dumps({'error': 'BIN inválido', 'card_type': None}), 
                                          [('Content-Type', 'application/json')])
            
            # PASO 1: Verificar si existe resultado en cache
            try:
                cached_result = request.env['ir.config_parameter'].sudo().get_param(
                    f'bin_validation_cache_{bin_number}', default=None
                )
                if cached_result:
                    _logger.info(f"✅ VALIDATE_BIN: **USANDO CACHE** para BIN {bin_number}")
                    _logger.info(f"✅ VALIDATE_BIN: Resultado del cache = {cached_result}")
                    # Guardar BIN validado en sesión cuando se usa cache
                    request.session['validated_bin'] = bin_number
                    parsed_result = json.loads(cached_result)
                    request.session['validated_card_type'] = parsed_result.get('card_type', 'debit')
                    return request.make_response(cached_result, 
                                              [('Content-Type', 'application/json')])
            except Exception as e:
                _logger.debug(f"VALIDATE_BIN: Cache read error (no crítico): {e}")
            
            # PASO 2: Llamar a binlist.net (máximo 5 solicitudes por hora)
            try:
                url = f'https://lookup.binlist.net/{bin_number}'
                _logger.info(f"VALIDATE_BIN: Llamando a binlist.net: {url}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                }
                
                response = requests.get(url, timeout=8, headers=headers)
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
                        }
                        result_json = json.dumps(result)
                        
                        # Guardar BIN validado en sesión para validación posterior
                        request.session['validated_bin'] = bin_number
                        request.session['validated_card_type'] = card_type
                        _logger.info(f"VALIDATE_BIN: BIN guardado en sesión - {bin_number} ({card_type})")
                        
                        # Cachear resultado indefinidamente (no son datos sensibles, solo BIN + tipo)
                        try:
                            request.env['ir.config_parameter'].sudo().set_param(
                                f'bin_validation_cache_{bin_number}', 
                                result_json
                            )
                            _logger.info(f"✅ VALIDATE_BIN: **RESULTADO GUARDADO EN CACHE PERMANENTE** para BIN {bin_number} = {result_json}")
                        except Exception as e:
                            _logger.debug(f"VALIDATE_BIN: Cache write error (no crítico): {e}")
                        
                        _logger.info(f"VALIDATE_BIN: Retornando resultado exitoso")
                        return request.make_response(result_json, 
                                                  [('Content-Type', 'application/json')])
                    else:
                        _logger.warning(f"VALIDATE_BIN: Tipo de tarjeta no válido: '{card_type}'")
                        return request.make_response(json.dumps({'error': 'Tipo de tarjeta no válido', 'card_type': None}), 
                                                  [('Content-Type', 'application/json')])
                elif response.status_code == 429:
                    _logger.warning(f"VALIDATE_BIN: Rate limit (429) de binlist.net")
                    return request.make_response(json.dumps({
                        'error': 'Límite de solicitudes alcanzado. Intenta de nuevo en unos minutos.',
                        'card_type': None,
                    }), [('Content-Type', 'application/json')])
                else:
                    _logger.warning(f"VALIDATE_BIN: Status {response.status_code} de binlist.net")
                    return request.make_response(json.dumps({'error': f'BIN no encontrado (status {response.status_code})', 'card_type': None}), 
                                              [('Content-Type', 'application/json')])
            
            except requests.exceptions.Timeout as e:
                _logger.warning(f"VALIDATE_BIN: Timeout de binlist.net: {e}")
                return request.make_response(json.dumps({'error': 'Timeout al validar BIN', 'card_type': None}), 
                                          [('Content-Type', 'application/json')])
            except requests.exceptions.RequestException as e:
                _logger.warning(f"VALIDATE_BIN: Error de requests: {e}")
                return request.make_response(json.dumps({'error': 'Error al conectar con el servicio de validación', 'card_type': None}), 
                                          [('Content-Type', 'application/json')])
        
        except Exception as e:
            _logger.error(f"ERROR en validate_bin: {str(e)}", exc_info=True)
            return request.make_response(json.dumps({'error': str(e), 'card_type': None}), 
                                      [('Content-Type', 'application/json')])
    
    @http.route('/rental/calculate-deposit', auth='public', type='http', methods=['POST'], csrf=False)
    def calculate_deposit(self):
        """Calcula el depósito dinámico basado en tipo de tarjeta y categoría de vehículo"""
        try:
            # Obtener parámetros del body JSON
            try:
                body_data = json.loads(request.httprequest.data.decode('utf-8'))
                category_id = int(body_data.get('category_id', 0))
                card_type = body_data.get('card_type', 'debit')
                total_price = float(body_data.get('total_price', 0))
            except Exception as e:
                _logger.warning(f"CALCULATE_DEPOSIT: Error parseando JSON: {e}")
                category_id = int(request.params.get('category_id', 0))
                card_type = request.params.get('card_type', 'debit')
                total_price = float(request.params.get('total_price', 0))
            
            _logger.info(f"CALCULATE_DEPOSIT: Solicitado - category_id={category_id}, card_type={card_type}, total_price={total_price}")
            
            if not category_id or not card_type or total_price <= 0:
                _logger.warning(f"CALCULATE_DEPOSIT: Parámetros inválidos")
                return request.make_response(json.dumps({
                    'success': False,
                    'error': 'Parámetros inválidos',
                    'deposit_amount': 0
                }), [('Content-Type', 'application/json')])
            
            # Calcular depósito usando el modelo
            try:
                deposit_amount = request.env['vehicle.deposit.rule'].sudo().get_deposit_amount(
                    category_id, card_type, total_price
                )
                deposit_amount = float(deposit_amount) if deposit_amount else 0
                total_with_deposit = total_price + deposit_amount
                
                _logger.info(f"CALCULATE_DEPOSIT: Depósito calculado = {deposit_amount}EUR para {card_type} en categoría {category_id}")
                
                result = {
                    'success': True,
                    'deposit_amount': round(deposit_amount, 2),
                    'total_with_deposit': round(total_with_deposit, 2),
                    'card_type': card_type
                }
                
                return request.make_response(json.dumps(result), 
                                          [('Content-Type', 'application/json')])
            
            except Exception as e:
                _logger.error(f"CALCULATE_DEPOSIT: Error calculando depósito: {str(e)}", exc_info=True)
                return request.make_response(json.dumps({
                    'success': False,
                    'error': f'Error al calcular depósito: {str(e)}',
                    'deposit_amount': 0
                }), [('Content-Type', 'application/json')])
        
        except Exception as e:
            _logger.error(f"ERROR en calculate_deposit: {str(e)}", exc_info=True)
            return request.make_response(json.dumps({
                'success': False,
                'error': str(e),
                'deposit_amount': 0
            }), [('Content-Type', 'application/json')])
