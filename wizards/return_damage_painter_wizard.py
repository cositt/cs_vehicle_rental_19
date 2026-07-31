# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class VehicleReturnDamagePainter(models.TransientModel):
    """Wizard para pintar daños en la devolución de un vehículo"""
    _name = 'vehicle.contract.return.damage.painter'
    _description = 'Editor de Daños para Devolución'

    return_wizard_id = fields.Many2one(
        'vehicle.contract.return.wizard',
        string='Wizard de Devolución',
        required=True,
        ondelete='cascade'
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True
    )

    base_image = fields.Binary(
        string='Imagen Base del Vehículo',
        compute='_compute_base_image'
    )

    painter_ref = fields.Char(
        string='Referencia del Painter',
        compute='_compute_painter_ref',
        help='"modelo,id" que el editor de daños lee del DOM para saber dónde '
             'guardar la imagen. No se puede deducir de la URL porque abrir un '
             'diálogo no la modifica.'
    )

    @api.depends_context('uid')
    def _compute_painter_ref(self):
        for rec in self:
            rec.painter_ref = '%s,%s' % (rec._name, rec.id or '')

    @api.depends('vehicle_id')
    def _compute_base_image(self):
        """Obtener la imagen base del vehículo o una por defecto"""
        for rec in self:
            if rec.vehicle_id and rec.vehicle_id.image_128:
                rec.base_image = rec.vehicle_id.image_128
            else:
                rec.base_image = False

    def get_base_image(self):
        """Imagen sobre la que empieza a dibujar el editor.

        Si ya hay marcas guardadas se devuelven, para poder editarlas (añadir o
        borrar) en vez de empezar de cero cada vez. Si no, el JS usa el diagrama
        del vehículo por defecto.
        """
        self.ensure_one()
        existing = self.return_wizard_id.painted_damage_image
        return existing.decode('utf-8') if existing else False

    def get_wizard_id_for_js(self):
        """Devolver el ID del wizard de devolución para JavaScript"""
        self.ensure_one()
        return {
            'wizard_id': self.return_wizard_id.id,
        }

    def save_image_to_wizard(self, image_data):
        """Guardar la imagen pintada en el wizard de devolución"""
        self.ensure_one()

        if not image_data:
            return {'success': False, 'message': _('No se recibió ninguna imagen')}

        try:
            self.return_wizard_id.write({
                'painted_damage_image': image_data,
                'has_damage': True,
            })
            # Sin cr.commit(): Odoo confirma la transacción al terminar la petición.
            # Un commit explícito aquí rompe la transacción y provoca
            # "could not serialize access due to concurrent update".

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
        return self.action_back_to_wizard()

    def action_back_to_wizard(self):
        """Volver al asistente de devolución conservando lo ya introducido.

        Abrir el painter con target 'new' desde el diálogo del wizard lo reemplaza
        en vez de apilarse, así que cerrar sin más dejaría al usuario sin pantalla
        y con la sensación de haber perdido la devolución. El registro transitorio
        conserva los datos: basta con reabrirlo.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devolución de Vehículo'),
            'res_model': 'vehicle.contract.return.wizard',
            'res_id': self.return_wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
