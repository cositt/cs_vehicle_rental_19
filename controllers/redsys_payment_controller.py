# -*- coding: utf-8 -*-
"""
Controlador para el pago con Redsys - Versión CORREGIDA
Generador de parámetros Redsys HMAC_SHA256_V1 con derivación 3DES-CBC
"""

from odoo import http
from odoo.http import request, Response
import base64, hashlib, hmac, json, time, logging, tempfile, subprocess, os

_logger = logging.getLogger(__name__)

def derive_key_3des(secret_b64: str, order: str) -> bytes:
    """
    Derivar clave HMAC a partir de secret base64 y número de orden usando 3DES-CBC
    Redsys requiere esta derivación para validar la firma correctamente
    """
    try:
        # Decodificar secret base64
        secret = base64.b64decode(secret_b64)
        
        # Preparar orden con padding nulo a múltiplo de 8 bytes (requerido para 3DES)
        order_bytes = order.encode('utf-8')
        pad = (-len(order_bytes)) % 8
        order_padded = order_bytes + b'\x00' * pad
        
        # Crear archivo temporal con orden padded
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f_order:
            f_order.write(order_padded)
            order_path = f_order.name
        
        try:
            # Derivar clave usando openssl: enc -des-ede3-cbc con key en hex y IV=0
            derived_path = tempfile.mktemp()
            key_hex = secret.hex()
            subprocess.check_call([
                'openssl', 'enc', '-des-ede3-cbc',
                '-K', key_hex,
                '-iv', '0000000000000000',
                '-nopad',
                '-in', order_path,
                '-out', derived_path
            ])
            
            # Leer clave derivada
            with open(derived_path, 'rb') as f:
                derived_key = f.read()
            
            os.unlink(derived_path)
        finally:
            os.unlink(order_path)
        
        return derived_key
    except Exception as e:
        _logger.error(f"Error derivando clave 3DES: {str(e)}")
        raise

class RedsysPaymentController(http.Controller):
    
    @http.route('/web/redsys/generate', type='http', auth='public')
    def generate_redsys_params(self, **kwargs):
        """
        Endpoint para generar parámetros Redsys
        ENDPOINT NUEVO - NO EN CACHÉ
        """
        try:
            price = float(kwargs.get('price', 0))
            
            merchant_code = "369056973"
            terminal = "1"
            secret_key = "sq7HjrUOBfKmC576ILgskD5srU870gJ7"
            
            # Crear número de pedido único (12 dígitos sin caracteres especiales)
            order_number = str(int(time.time()) % 1000000000000).zfill(12)
            
            # Convertir cantidad a céntimos
            amount_cents = int(float(price) * 100)
            if amount_cents < 1:
                amount_cents = 1
            
            # Datos del comerciante (SOLO campos requeridos por Redsys)
            merchant_data = {
                "DS_MERCHANT_AMOUNT": str(amount_cents),
                "DS_MERCHANT_ORDER": order_number,
                "DS_MERCHANT_MERCHANTCODE": merchant_code,
                "DS_MERCHANT_CURRENCY": "978",
                "DS_MERCHANT_TRANSACTIONTYPE": "0",
                "DS_MERCHANT_TERMINAL": terminal,
                "DS_MERCHANT_MERCHANTURL": "https://sunsetrent.es/web/redsys-webhook",
            }
            
            # Codificar JSON sin espacios
            merchant_json = json.dumps(merchant_data, separators=(',', ':'))
            merchant_params = base64.b64encode(merchant_json.encode('utf-8')).decode('utf-8')
            
            # Generar firma HMAC_SHA256 con clave derivada 3DES-CBC
            derived_key = derive_key_3des(secret_key, order_number)
            signature_bytes = hmac.new(derived_key, merchant_params.encode('utf-8'), hashlib.sha256).digest()
            signature = base64.b64encode(signature_bytes).decode('utf-8')
            
            _logger.info(f"=== REDSYS DEBUG (NEW CONTROLLER) ===")
            _logger.info(f"Merchant Code: {merchant_code}")
            _logger.info(f"Terminal: {terminal}")
            _logger.info(f"Order Number: {order_number}")
            _logger.info(f"Amount (cents): {amount_cents}")
            _logger.info(f"Merchant JSON: {merchant_json}")
            _logger.info(f"Merchant Params (B64): {merchant_params}")
            _logger.info(f"Signature: {signature}")
            
            return Response(
                json.dumps({
                    'status': 'ok',
                    'merchant_params': merchant_params,
                    'signature': signature,
                    'merchant_code': merchant_code,
                    'terminal': terminal,
                    'order_number': order_number,
                }),
                content_type='application/json'
            )
        except Exception as e:
            _logger.error(f"Error generando parámetros Redsys: {str(e)}")
            return Response(
                json.dumps({'status': 'error', 'message': str(e)}),
                content_type='application/json',
                status=400
            )


    @http.route('/web/booking-confirmation-redsys', auth='public', website=True, type='http', methods=['POST'], csrf=False)
    def booking_confirmation_redsys(self, **kwargs):
        """
        Endpoint que procesa la confirmación de reserva y redirige a Redsys
        NUEVO - Usa el controlador corregido con derivación 3DES
        """
        try:
            price = float(kwargs.get('price', 0))
            customer_name = kwargs.get('customer_name', '')
            customer_email = kwargs.get('customer_email', '')
            category_id = kwargs.get('category_id', '')
            start_date = kwargs.get('start_date', '')
            end_date = kwargs.get('end_date', '')
            
            merchant_code = "369056973"
            terminal = "1"
            secret_key = "sq7HjrUOBfKmC576ILgskD5srU870gJ7"
            
            # Crear número de pedido único (12 dígitos sin caracteres especiales)
            order_number = str(int(time.time()) % 1000000000000).zfill(12)
            
            # Convertir cantidad a céntimos
            amount_cents = int(float(price) * 100)
            if amount_cents < 1:
                amount_cents = 1
            
            # Datos del comerciante
            merchant_data = {
                "DS_MERCHANT_AMOUNT": str(amount_cents),
                "DS_MERCHANT_ORDER": order_number,
                "DS_MERCHANT_MERCHANTCODE": merchant_code,
                "DS_MERCHANT_CURRENCY": "978",
                "DS_MERCHANT_TRANSACTIONTYPE": "0",
                "DS_MERCHANT_TERMINAL": terminal,
                "DS_MERCHANT_MERCHANTURL": "https://sunsetrent.es/web/redsys-webhook",
            }
            
            # Codificar JSON sin espacios
            merchant_json = json.dumps(merchant_data, separators=(',', ':'))
            merchant_params = base64.b64encode(merchant_json.encode('utf-8')).decode('utf-8')
            
            # Generar firma HMAC_SHA256 con clave derivada 3DES-CBC
            derived_key = derive_key_3des(secret_key, order_number)
            signature_bytes = hmac.new(derived_key, merchant_params.encode('utf-8'), hashlib.sha256).digest()
            signature = base64.b64encode(signature_bytes).decode('utf-8')
            
            _logger.info(f"=== BOOKING CONFIRMATION REDSYS ===")
            _logger.info(f"Customer: {customer_name} ({customer_email})")
            _logger.info(f"Dates: {start_date} to {end_date}")
            _logger.info(f"Amount: {price} EUR ({amount_cents} cents)")
            _logger.info(f"Order: {order_number}")
            
            # Guardar booking data en sesión
            request.session['booking_data'] = {
                'customer_name': customer_name,
                'customer_email': customer_email,
                'category_id': int(category_id),
                'start_date': start_date,
                'end_date': end_date,
                'selected_price': price,
                'order_number': order_number,
            }
            
            # Renderizar template con formulario que auto-submit
            return request.render('vehicle_rental.redsys_checkout', {
                'merchant_params': merchant_params,
                'signature': signature,
                'merchant_code': merchant_code,
                'terminal': terminal,
                'order_number': order_number,
            })
            
        except Exception as e:
            _logger.error(f"Error en booking-confirmation-redsys: {str(e)}")
            return f"Error: {str(e)}"
