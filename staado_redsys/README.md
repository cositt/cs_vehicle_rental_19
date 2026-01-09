# Pruebas manuales Redsys (sis-t)

Scripts:
- tests_redsys.py: genera Ds_MerchantParameters y Ds_Signature (3DES→HMAC-SHA256) y puede POSTear a Redsys.
- tests_redsys.sh: wrapper rápido.

Uso:

export REDSYS_SECRET_B64='sq7HjrUOBfKmC576ILgskD5srU870gJ7'
export REDSYS_MERCHANT_CODE='999008881'   # o el del TPV
export REDSYS_TERMINAL='1'

./tests_redsys.sh   # muestra cabeceras + inicio del HTML de "Pantalla de pago Redsys"

