/* -*- coding: utf-8 -*-
 * Validación de tarjeta de crédito/débito con Freebinchecker
 * Calcula dinámicamente el depósito basado en el tipo de tarjeta
 */

document.addEventListener('DOMContentLoaded', function() {
    const cardTypeSelect = document.getElementById('card_type');
    const cardNumberInput = document.getElementById('card_number');
    const depositDisplay = document.getElementById('deposit_display');
    const totalDisplay = document.getElementById('total_display');
    const cardBinInput = document.getElementById('card_bin');
    
    // Escuchar cambios en el tipo de tarjeta seleccionado
    if (cardTypeSelect) {
        cardTypeSelect.addEventListener('change', function() {
            updateDepositDisplay();
            logPaymentInfo();
        });
    }
    
    // Validar BIN cuando el usuario ingrese 6 dígitos
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', function() {
            let cardNumber = this.value.replace(/\D/g, '');
            
            // Si hay al menos 6 dígitos, validar con Freebinchecker
            if (cardNumber.length >= 6) {
                const bin = cardNumber.substring(0, 6);
                cardBinInput.value = bin;
                validateBinWithFreebinchecker(bin);
            }
        });
    }
});

function validateBinWithFreebinchecker(bin) {
    _logger.info(`Validando BIN con Freebinchecker: ${bin}`);
    
    fetch(`https://lookup.binlist.net/${bin}`)
        .then(response => response.json())
        .then(data => {
            if (data && data.type) {
                const cardType = data.type.toLowerCase();
                const cardTypeSelect = document.getElementById('card_type');
                
                // Establecer el tipo de tarjeta automaticamente
                if (cardType === 'credit' || cardType === 'debit') {
                    cardTypeSelect.value = cardType;
                    _logger.info(`Freebinchecker detectó: ${cardType}`);
                    updateDepositDisplay();
                    logPaymentInfo();
                } else {
                    _logger.warning(`Tipo de tarjeta no reconocido: ${cardType}`);
                }
            }
        })
        .catch(error => {
            _logger.warning(`Error validando BIN: ${error}`);
            // Continuar sin validacion si Freebinchecker falla
        });
}

function updateDepositDisplay() {
    const cardTypeSelect = document.getElementById('card_type');
    const rentalPrice = parseFloat(document.getElementById('selected_price')?.value || 0);
    
    if (!cardTypeSelect) return;
    
    const cardType = cardTypeSelect.value;
    const depositDisplay = document.getElementById('deposit_display');
    const totalDisplay = document.getElementById('total_display');
    
    if (depositDisplay && totalDisplay) {
        // Placeholder: Mostrar tipo de tarjeta seleccionado
        // En producción, esto vendría del servidor basado en la regla configurada
        depositDisplay.textContent = `Tipo: ${cardType === 'credit' ? 'Crédito' : 'Débito'}`;
        totalDisplay.textContent = `Total con depósito: ${rentalPrice}EUR (a confirmar)`;
    }
}

function logPaymentInfo() {
    const cardTypeSelect = document.getElementById('card_type');
    const cardBinInput = document.getElementById('card_bin');
    
    if (cardTypeSelect) {
        console.log(`Información de pago actualizada:
            - Tipo de tarjeta: ${cardTypeSelect.value}
            - BIN: ${cardBinInput?.value || 'No disponible'}
        `);
    }
}

// Logger helper
const _logger = {
    info: function(msg) { console.log('[INFO] ' + msg); },
    warning: function(msg) { console.warn('[WARNING] ' + msg); },
    error: function(msg) { console.error('[ERROR] ' + msg); }
};
