#!/usr/bin/env python3
import os, sys, base64, json, time, hmac, hashlib, binascii, subprocess, tempfile
from urllib.parse import urlencode

def derive_key_3des(secret_b64: str, order: str) -> bytes:
    secret = base64.b64decode(secret_b64)
    order_bytes = order.encode('ascii')
    pad = (-len(order_bytes)) % 8
    order_padded = order_bytes + b'\x00'*pad
    with tempfile.NamedTemporaryFile(delete=False) as f_order:
        f_order.write(order_padded); f_order.flush()
        key_hex = binascii.hexlify(secret).decode('ascii')
    derived_path = tempfile.mktemp()
    subprocess.check_call(['openssl','enc','-des-ede3-cbc','-K', key_hex, '-iv','0000000000000000','-nopad','-in', f_order.name, '-out', derived_path])
    K = open(derived_path,'rb').read()
    os.unlink(f_order.name); os.unlink(derived_path)
    return K

def build_params(merchant_code, terminal, secret_b64, amount_cents=123, currency='978', txn_type='0', merchant_url='https://sunsetrent.es/web/redsys-webhook'):
    order = str(int(time.time()) % 10**12).zfill(12)
    merchant = {
        'DS_MERCHANT_AMOUNT': str(amount_cents),
        'DS_MERCHANT_ORDER': order,
        'DS_MERCHANT_MERCHANTCODE': merchant_code,
        'DS_MERCHANT_CURRENCY': currency,
        'DS_MERCHANT_TRANSACTIONTYPE': txn_type,
        'DS_MERCHANT_TERMINAL': terminal,
        'DS_MERCHANT_MERCHANTURL': merchant_url,
    }
    merch_json = json.dumps(merchant, separators=(',', ':'))
    merch_b64 = base64.b64encode(merch_json.encode('utf-8')).decode('ascii')
    K = derive_key_3des(secret_b64, merchant['DS_MERCHANT_ORDER'])
    sig = base64.b64encode(hmac.new(K, merch_b64.encode('ascii'), hashlib.sha256).digest()).decode('ascii')
    return merchant, merch_b64, sig

def post_to_redsys(merchant_params_b64, signature, url='https://sis-t.redsys.es:25443/sis/realizarPago'):
    data = {
        'Ds_SignatureVersion': 'HMAC_SHA256_V1',
        'Ds_MerchantParameters': merchant_params_b64,
        'Ds_Signature': signature,
    }
    body = urlencode(data)
    cmd = ['curl','-sS','-k','-D','-','--data', body, url]
    res = subprocess.run(cmd, stdout=subprocess.PIPE)
    out = res.stdout
    head, body = out.split(b'\r\n\r\n',1) if b'\r\n\r\n' in out else (out, b'')
    sys.stdout.write(head.decode('latin-1','ignore') + '\n\n')
    if body:
        sys.stdout.write('BODY (inicio):\n' + body[:500].decode('latin-1','ignore') + '\n')

def main():
    merchant_code = os.getenv('REDSYS_MERCHANT_CODE') or '999008881'
    terminal = os.getenv('REDSYS_TERMINAL') or '1'
    secret_b64 = os.getenv('REDSYS_SECRET_B64')
    if not secret_b64:
        print('ERROR: define REDSYS_SECRET_B64 en el entorno (Base64 de la clave secreta)'); sys.exit(1)
    amount = int(os.getenv('REDSYS_AMOUNT_CENTS') or '123')
    merchant, merch_b64, sig = build_params(merchant_code, terminal, secret_b64, amount)
    print('Merchant:', merchant)
    print('Ds_MerchantParameters (b64):', merch_b64)
    print('Ds_Signature:', sig)
    if '--post' in sys.argv:
        post_to_redsys(merch_b64, sig)

if __name__ == '__main__':
    main()
