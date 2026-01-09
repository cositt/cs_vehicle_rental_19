/**
 * Manejador de pago Redsys
 * Genera parámetros usando el nuevo endpoint corregido
 */

(function() {
    'use strict';
    
    window.RedsysPaymentHandler = {
        
        /**
         * Generar parámetros Redsys y redirigir
         */
        generateAndPay: async function(price) {
            console.log('Generando parámetros Redsys para price:', price);
            
            try {
                // Llamar al nuevo endpoint JSON
                const response = await fetch('/web/redsys/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        price: price
                    })
                });
                
                const data = await response.json();
                
                if (data.status !== 'ok') {
                    console.error('Error generando parámetros:', data.message);
                    alert('Error al procesar el pago: ' + data.message);
                    return;
                }
                
                console.log('Parámetros generados:', data);
                
                // Crear formulario para enviar a Redsys
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = 'https://sis-t.redsys.es:25443/sis/realizarPago';
                form.style.display = 'none';
                
                // Agregar campos
                const fields = {
                    'Ds_SignVersion': 'HMAC_SHA256_V1',
                    'Ds_MerchantParameters': data.merchant_params,
                    'Ds_Signature': data.signature
                };
                
                for (const [key, value] of Object.entries(fields)) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = key;
                    input.value = value;
                    form.appendChild(input);
                }
                
                document.body.appendChild(form);
                
                console.log('Enviando formulario a Redsys...');
                form.submit();
                
            } catch (error) {
                console.error('Error en RedsysPaymentHandler:', error);
                alert('Error al procesar el pago: ' + error.message);
            }
        }
    };
    
    console.log('✓ RedsysPaymentHandler cargado');
})();
