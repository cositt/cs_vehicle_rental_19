# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class VehicleSubstitutionDamagePainter(models.TransientModel):
    """Wizard para pintar daños en sustituciones de vehículos"""
    _name = 'vehicle.substitution.damage.painter'
    _description = 'Editor de Daños para Sustitución'

    substitution_wizard_id = fields.Many2one(
        'vehicle.substitution.wizard',
        string='Wizard de Sustitución',
        required=True,
        ondelete='cascade'
    )
    
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True
    )
    
    damage_type = fields.Selection([
        ('old', 'Vehículo Devuelto'),
        ('new', 'Vehículo Sustituto')
    ], string='Tipo de Daño', required=True, default='old')
    
    base_image = fields.Binary(
        string='Imagen Base del Vehículo',
        compute='_compute_base_image'
    )
    
    @api.depends('vehicle_id')
    def _compute_base_image(self):
        """Obtener la imagen base del vehículo o una por defecto"""
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.image_128:
                rec.base_image = rec.vehicle_id.image_128
            else:
                # Usar imagen por defecto
                rec.base_image = False
    
    def get_wizard_id_for_js(self):
        """Devolver el ID del wizard de sustitución para JavaScript"""
        self.ensure_one()
        return {
            'wizard_id': self.substitution_wizard_id.id,
            'damage_type': self.damage_type,
        }
    
    def save_image_to_wizard(self, image_data):
        """Guardar la imagen pintada en el wizard de sustitución"""
        self.ensure_one()
        
        if not image_data:
            return {'success': False, 'message': _('No se recibió ninguna imagen')}
        
        try:
            # Guardar en el campo correspondiente del wizard de sustitución
            if self.damage_type == 'old':
                self.substitution_wizard_id.write({
                    'old_vehicle_painted_damage_image': image_data,
                    'old_vehicle_has_damage': True,
                })
            else:  # new
                self.substitution_wizard_id.write({
                    'new_vehicle_painted_damage_image': image_data,
                    'new_vehicle_has_damage': True,
                })
            
            self.env.cr.commit()
            
            return {
                'success': True,
                'message': _('Imagen guardada correctamente')
            }
        except Exception as e:
            return {
                'success': False,
                'message': _('Error al guardar la imagen: %s') % str(e)
            }
    
    def save_damage_image(self):
        """Guardar y cerrar el modal (la imagen se guarda desde JavaScript)"""
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}




















