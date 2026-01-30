# -*- coding: utf-8 -*-
"""
Fix para el webhook de Redsys: actualizar transacción a 'done' cuando recibe respuesta exitosa
"""

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class PaymentTransactionRedsysWebhookFix(models.Model):
    """Override para arreglar el procesamiento del webhook de Redsys"""
    _inherit = 'payment.transaction'

    @api.model
    def _redsys_form_validate(self, data):
        """
        Hook que se ejecuta después de recibir y validar un webhook de Redsys.
        Aquí actualizamos manualmente la transacción a 'done' si la respuesta es éxito.
        """
        _logger.info("PAYMENT_REDSYS_WEBHOOK_FIX: Interceptando validación de Redsys")
        
        # Llamar al método padre primero
        result = super()._redsys_form_validate(data)
        
        # Obtener datos del webhook
        ds_response = data.get('Ds_Response', '')
        ds_order = data.get('Ds_Order', '')
        
        _logger.info(f"PAYMENT_REDSYS_WEBHOOK_FIX: Ds_Response={ds_response}, Ds_Order={ds_order}")
        
        # Si la respuesta es 0000 (éxito), actualizar la transacción
        if ds_response == '0000' and ds_order:
            try:
                # Buscar la transacción por referencia
                payment_tx = self.search(
                    [('reference', '=', ds_order)],
                    limit=1
                )
                
                if payment_tx:
                    _logger.info(f"PAYMENT_REDSYS_WEBHOOK_FIX: Encontrada TX {payment_tx.id}, estado actual: {payment_tx.state}")
                    
                    # Si está en estado 'error' o 'pending', cambiar a 'done'
                    if payment_tx.state in ('error', 'pending', 'draft'):
                        # Usar _set_done() que es el método correcto para transicionar
                        _logger.info(f"PAYMENT_REDSYS_WEBHOOK_FIX: Transitioning TX {payment_tx.id} to done")
                        try:
                            payment_tx._set_done()
                            _logger.info(f"PAYMENT_REDSYS_WEBHOOK_FIX: TX {payment_tx.id} transitioned to done")
                        except Exception as e:
                            _logger.warning(f"PAYMENT_REDSYS_WEBHOOK_FIX: _set_done() failed, trying direct update: {str(e)}")
                            # Si _set_done falla, intentar actualizar directamente la BD
                            self.env.cr.execute(
                                "UPDATE payment_transaction SET state = %s WHERE id = %s",
                                ('done', payment_tx.id)
                            )
                            _logger.info(f"PAYMENT_REDSYS_WEBHOOK_FIX: TX {payment_tx.id} updated to done via direct DB update")
                    
                else:
                    _logger.warning(f"PAYMENT_REDSYS_WEBHOOK_FIX: TX no encontrada con referencia {ds_order}")
                    
            except Exception as e:
                _logger.error(f"PAYMENT_REDSYS_WEBHOOK_FIX: Error: {str(e)}", exc_info=True)
        
        return result
