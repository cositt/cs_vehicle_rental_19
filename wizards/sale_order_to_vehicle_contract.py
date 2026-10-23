# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models, _
from odoo.exceptions import UserError


class SaleOrderToVehicleContract(models.TransientModel):
    """Convert Sale Order to Vehicle Contract"""
    _name = 'sale.order.to.vehicle.contract'
    _description = __doc__

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", required=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True,
                                 domain="[('status', '=', 'available')]")
    start_date = fields.Datetime(string="Pick-up Date", required=True)
    end_date = fields.Datetime(string="Return Date", required=True)

    @api.model
    def default_get(self, field_names):
        """Set default values from sale order"""
        res = super().default_get(field_names)
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['sale.order'].browse(active_id)
            if order:
                res.update({
                    'sale_order_id': order.id,
                    'partner_id': order.partner_id.id,
                    'vehicle_id': order.vehicle_id.id if order.vehicle_id else False,
                    'start_date': order.rental_start_date,
                    'end_date': order.rental_end_date,
                })
                
                # Si el pedido viene de un lead con vehículo, usar esos datos
                if not res.get('vehicle_id') and order.opportunity_id and order.opportunity_id.vehicle_id:
                    res['vehicle_id'] = order.opportunity_id.vehicle_id.id
                    
                    # También copiar las fechas del lead si existen
                    if not res.get('start_date') and hasattr(order.opportunity_id, 'start_date'):
                        from datetime import datetime, time
                        if order.opportunity_id.start_date:
                            date_obj = order.opportunity_id.start_date
                            if isinstance(date_obj, str):
                                date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
                            res['start_date'] = datetime.combine(date_obj, time.min)
                    
                    if not res.get('end_date') and hasattr(order.opportunity_id, 'end_date'):
                        from datetime import datetime, time
                        if order.opportunity_id.end_date:
                            date_obj = order.opportunity_id.end_date
                            if isinstance(date_obj, str):
                                date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
                            res['end_date'] = datetime.combine(date_obj, time.max)
        return res

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Update fields when sale order changes"""
        if self.sale_order_id:
            order = self.sale_order_id
            self.partner_id = order.partner_id.id
            self.vehicle_id = order.vehicle_id.id if order.vehicle_id else False
            self.start_date = order.rental_start_date
            self.end_date = order.rental_end_date
            
            # Si viene de un lead con vehículo
            if not self.vehicle_id and order.opportunity_id and order.opportunity_id.vehicle_id:
                self.vehicle_id = order.opportunity_id.vehicle_id.id
                
                if not self.start_date and hasattr(order.opportunity_id, 'start_date'):
                    from datetime import datetime, time
                    if order.opportunity_id.start_date:
                        date_obj = order.opportunity_id.start_date
                        if isinstance(date_obj, str):
                            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
                        self.start_date = datetime.combine(date_obj, time.min)
                
                if not self.end_date and hasattr(order.opportunity_id, 'end_date'):
                    from datetime import datetime, time
                    if order.opportunity_id.end_date:
                        date_obj = order.opportunity_id.end_date
                        if isinstance(date_obj, str):
                            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
                        self.end_date = datetime.combine(date_obj, time.max)

    def _agreed_daily_rent(self):
        """Price per day of the rent line of the order (0 if there is none)."""
        rent_product = self.env.ref('vehicle_rental.vehicle_rent_charge', raise_if_not_found=False)
        lines = self.sale_order_id.order_line.filtered(lambda line: not line.display_type and line.price_unit > 0)
        rent_lines = lines.filtered(lambda line: rent_product and line.product_id.product_tmpl_id
                                    == (rent_product.product_tmpl_id if rent_product._name == 'product.product'
                                        else rent_product))
        return (rent_lines or lines)[:1].price_unit

    def action_create_vehicle_contract(self):
        """Create vehicle contract from sale order"""
        self.ensure_one()
        
        # Validaciones
        if not self.vehicle_id:
            raise UserError(_("Seleccione un vehículo."))
        if not self.partner_id:
            raise UserError(_("Seleccione un cliente."))
        if not self.start_date or not self.end_date:
            raise UserError(_("Indique las fechas de recogida y devolución."))
        if self.end_date < self.start_date:
            raise UserError(_("La fecha de devolución no puede ser anterior a la de recogida."))
        
        # Verificar que el pedido esté confirmado
        if self.sale_order_id.state not in ['sale', 'done']:
            raise UserError(_("Confirme el pedido de venta antes de crear el contrato."))
        
        # Verificar si ya existe un contrato para este pedido
        if self.sale_order_id.vehicle_contract_id:
            raise UserError(_("Este pedido ya tiene contrato: %s",
                            self.sale_order_id.vehicle_contract_id.reference_no))
        
        # Obtener información del vehículo
        vehicle = self.vehicle_id
        
        # Crear el contrato
        contract = self.env['vehicle.contract'].create({
            'sale_order_id': self.sale_order_id.id,
            'crm_lead_id': self.sale_order_id.opportunity_id.id if self.sale_order_id.opportunity_id else False,
            'customer_id': self.partner_id.id,
            'customer_phone': self.partner_id.phone,
            'customer_email': self.partner_id.email,
            'vehicle_id': vehicle.id,
            'license_plate': vehicle.license_plate,
            'model_year': vehicle.model_year,
            'transmission': vehicle.transmission,
            'fuel_type': vehicle.fuel_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            # The price agreed in the order; it was left at 0
            'rent': self._agreed_daily_rent(),
            'rent_type': 'days',
        })
        
        # Vincular el contrato al pedido de venta
        self.sale_order_id.vehicle_contract_id = contract.id
        
        # Si hay un lead vinculado, también vincularlo al contrato
        if self.sale_order_id.opportunity_id:
            self.sale_order_id.opportunity_id.contract_id = contract.id
        
        # Mostrar mensaje de éxito
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Contrato creado'),
                'message': _('Contrato %s creado.', contract.reference_no),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'vehicle.contract',
                    'res_id': contract.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            }
        }

















