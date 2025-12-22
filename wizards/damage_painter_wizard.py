# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64
import os

class VehicleContractDamagePainter(models.TransientModel):
    _name = 'vehicle.contract.damage.painter'
    _description = 'Editor de Daños del Vehículo'

    contract_id = fields.Many2one('vehicle.contract', string='Contrato', required=True)
    damage_image = fields.Binary(string='Imagen de Daños')
    base_image = fields.Binary(string='Imagen Base', compute='_compute_base_image', store=False)
    
    def get_contract_id_for_js(self):
        """Método para que JavaScript obtenga el contract_id"""
        self.ensure_one()
        return self.contract_id.id if self.contract_id else False

    @api.depends('contract_id')
    def _compute_base_image(self):
        """Cargar imagen base o imagen previamente pintada"""
        for record in self:
            if record.contract_id.painted_damage_image:
                record.base_image = record.contract_id.painted_damage_image
            else:
                record.base_image = False
    
    def get_contract_id(self):
        """Obtener el ID del contrato para JavaScript"""
        self.ensure_one()
        return self.contract_id.id
    
    def save_image_to_contract(self, image_data):
        """Guardar imagen directamente en el contrato desde JavaScript"""
        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info('=== GUARDANDO IMAGEN DIRECTAMENTE EN CONTRATO ===')
        _logger.info(f'Contract ID: {self.contract_id.id}')
        _logger.info(f'Wizard ID: {self.id}')
        _logger.info(f'Tamaño de imagen recibida: {len(image_data)} caracteres')
        
        try:
            # Guardar la imagen en el contrato usando write para asegurar la persistencia
            self.contract_id.write({
                'painted_damage_image': image_data
            })
            
            # Hacer commit explícito para asegurar que se guarde
            self.env.cr.commit()
            
            _logger.info('✅ Commit realizado')
            
            # Verificar que se guardó
            self.contract_id.invalidate_recordset(['painted_damage_image'])
            if self.contract_id.painted_damage_image:
                _logger.info(f'✅ Verificación OK - Imagen guardada: {len(self.contract_id.painted_damage_image)} bytes')
                return {'success': True, 'message': 'Imagen guardada correctamente'}
            else:
                _logger.error('❌ ERROR: La imagen no se guardó correctamente')
                return {'success': False, 'message': 'Error: La imagen no se guardó'}
                
        except Exception as e:
            _logger.error(f'❌ Error al guardar: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def save_damage_image(self):
        """Guardar imagen de daños en el contrato - LLAMADO DESDE EL BOTÓN"""
        self.ensure_one()
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info('=== BOTÓN GUARDAR PRESIONADO ===')
        _logger.info(f'Wizard ID: {self.id}')
        _logger.info(f'Contract ID: {self.contract_id.id if self.contract_id else "NO TIENE"}')
        
        # La imagen viene desde JavaScript vía save_image_to_contract
        # Este método solo cierra el modal
        return {'type': 'ir.actions.act_window_close'}

