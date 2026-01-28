# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models
from dateutil.relativedelta import relativedelta
from datetime import datetime, time
import json
import logging

_logger = logging.getLogger(__name__)


def parse_time_str(time_str, default=None):
    """Parse time string HH:MM to time object"""
    if not time_str:
        return default or time.min
    try:
        h, m = map(int, time_str.split(':'))
        return time(h, m)
    except:
        return default or time.min


class LeadRentalContract(models.TransientModel):
    """Lead Rental Contract"""
    _name = 'lead.rental.contract'
    _description = __doc__

    crm_lead_id = fields.Many2one('crm.lead', string="Lead")
    company_id = fields.Many2one('res.company', string="Compañía", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer")
    selected_category_id = fields.Many2one('fleet.vehicle.model.category', string="Categoría de Vehículo",
                                          readonly=True, help="Categoría del vehículo a alquilar")
    search_vehicle = fields.Char(string="Buscar Vehículo", help="Busca por marca o modelo")
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle",
                                 domain="[('status', '=', 'available'), ('company_id', '=', company_id), '|', ('model_id.category_id', '=', selected_category_id), ('category_id', '=', selected_category_id)]")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")

    def _get_occupied_vehicle_ids(self, start_date, end_date):
        """Retorna IDs de vehículos ocupados en el rango de fechas (contratos activos)"""
        occupied_ids = []
        if start_date and end_date:
            try:
                # Buscar contratos activos que se solapan con las fechas
                overlapping_contracts = self.env['vehicle.contract'].search([
                    ('status', 'in', ['b_in_progress', 'c_return']),
                    ('start_date', '<=', end_date),
                    ('end_date', '>=', start_date),
                ])
                occupied_ids = [c.vehicle_id.id for c in overlapping_contracts if c.vehicle_id]
            except Exception as e:
                _logger.warning(f"Error calculating occupied vehicles: {e}")
        return occupied_ids

    def _get_reserved_vehicle_ids(self, category_id, start_date, end_date):
        """Retorna IDs de vehículos reservados (leads sin vehículo asignado pero pagados)"""
        reserved_ids = []
        if category_id and start_date and end_date:
            try:
                # Buscar leads con vehicle_id=False, type='opportunity' que se solapan
                reserved_leads = self.env['crm.lead'].search([
                    ('selected_category_id', '=', category_id),
                    ('vehicle_id', '=', False),
                    ('type', '=', 'opportunity'),
                    ('start_date', '<=', end_date),
                    ('end_date', '>=', start_date),
                ])
                # No retornamos IDs directos porque los leads no tienen vehículos asignados
                # Pero marcamos que esa categoría está reservada
                return len(reserved_leads) > 0
            except Exception as e:
                _logger.warning(f"Error calculating reserved vehicles: {e}")
        return False

    @api.model
    def default_get(self, field_names):
        """Set default values from crm lead"""
        res = super().default_get(field_names)
        active_id = self.env.context.get('active_id')
        
        if active_id:
            lead = self.env['crm.lead'].browse(active_id)
            if lead.exists():
                # Establecer el lead
                res['crm_lead_id'] = lead.id
                
                # Compañía (para filtrar vehículos por compañía)
                if lead.company_id:
                    res['company_id'] = lead.company_id.id
                
                # Cliente
                if lead.partner_id:
                    res['partner_id'] = lead.partner_id.id
                
                # Categoría seleccionada (para mostrar y filtrar)
                if hasattr(lead, 'selected_category_id') and lead.selected_category_id:
                    res['selected_category_id'] = lead.selected_category_id.id
                
                # Vehículo - buscar por categoría si no hay vehículo específico
                if hasattr(lead, 'vehicle_id') and lead.vehicle_id:
                    res['vehicle_id'] = lead.vehicle_id.id
                elif hasattr(lead, 'selected_category_id') and lead.selected_category_id:
                    vehicle = self.env['fleet.vehicle'].search([
                        ('model_id.category_id', '=', lead.selected_category_id.id),
                        ('status', '=', 'available')
                    ], limit=1)
                    if vehicle:
                        res['vehicle_id'] = vehicle.id
                
                # Obtener horas del lead
                start_time_obj = parse_time_str(getattr(lead, 'start_time', None), time(9, 0))
                end_time_obj = parse_time_str(getattr(lead, 'end_time', None), time(9, 0))
                
                # Fechas - convertir de Date a Datetime usando las horas del lead
                if hasattr(lead, 'start_date') and lead.start_date:
                    if isinstance(lead.start_date, str):
                        date_obj = datetime.strptime(lead.start_date, '%Y-%m-%d').date()
                        res['start_date'] = datetime.combine(date_obj, start_time_obj)
                    else:
                        res['start_date'] = datetime.combine(lead.start_date, start_time_obj)
                
                if hasattr(lead, 'end_date') and lead.end_date:
                    if isinstance(lead.end_date, str):
                        date_obj = datetime.strptime(lead.end_date, '%Y-%m-%d').date()
                        res['end_date'] = datetime.combine(date_obj, end_time_obj)
                    else:
                        res['end_date'] = datetime.combine(lead.end_date, end_time_obj)
        
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to fill data from lead if not provided"""
        records = super().create(vals_list)
        for record in records:
            if record.crm_lead_id and (not record.partner_id or not record.vehicle_id or not record.start_date or not record.end_date):
                lead = record.crm_lead_id
                start_time_obj = parse_time_str(getattr(lead, 'start_time', None), time(9, 0))
                end_time_obj = parse_time_str(getattr(lead, 'end_time', None), time(9, 0))
                
                if not record.partner_id and lead.partner_id:
                    record.partner_id = lead.partner_id
                
                if not record.vehicle_id and lead.vehicle_id:
                    record.vehicle_id = lead.vehicle_id
                
                if not record.start_date and lead.start_date:
                    record.start_date = datetime.combine(lead.start_date, start_time_obj)
                
                if not record.end_date and lead.end_date:
                    record.end_date = datetime.combine(lead.end_date, end_time_obj)
        
        return records
    
    @api.onchange('crm_lead_id')
    def _onchange_crm_lead_id(self):
        """Update fields when lead changes"""
        if self.crm_lead_id:
            lead = self.crm_lead_id
            start_time_obj = parse_time_str(getattr(lead, 'start_time', None), time(9, 0))
            end_time_obj = parse_time_str(getattr(lead, 'end_time', None), time(9, 0))
            
            start_datetime = False
            end_datetime = False
            if lead.start_date:
                start_datetime = datetime.combine(lead.start_date, start_time_obj)
            if lead.end_date:
                end_datetime = datetime.combine(lead.end_date, end_time_obj)
            
            self.partner_id = lead.partner_id if lead.partner_id else False
            
            # Establecer compañía (para filtrar vehículos)
            if lead.company_id:
                self.company_id = lead.company_id
            
            # Establecer categoría
            if hasattr(lead, 'selected_category_id') and lead.selected_category_id:
                self.selected_category_id = lead.selected_category_id
            
            if lead.vehicle_id:
                self.vehicle_id = lead.vehicle_id
            elif hasattr(lead, 'selected_category_id') and lead.selected_category_id:
                vehicle = self.env['fleet.vehicle'].search([
                    ('model_id.category_id', '=', lead.selected_category_id.id),
                    ('status', '=', 'available')
                ], limit=1)
                self.vehicle_id = vehicle if vehicle else False
            else:
                self.vehicle_id = False
            self.start_date = start_datetime
            self.end_date = end_datetime
    
    @api.onchange('start_date', 'end_date', 'search_vehicle')
    def _onchange_vehicle_filters(self):
        """Actualizar domain del vehículo basado en filtros"""
        # Este onchange actualiza dinámicamente el domain, pero Odoo usará
        # el domain del campo vehicle_id para filtrar. 
        # Para una implementación completa, usaremos métodos posteriores para validar.

    def _find_redsys_transaction(self):
        """
        Buscar la transacción Redsys asociada al booking.
        Estrategia: buscar por email del cliente en booking_data_json (más fiable que partner_id)
        """
        # Obtener email del lead/partner
        email = self.partner_id.email or self.crm_lead_id.email_from
        if not email:
            _logger.warning("WIZARD: No se encontró email para buscar transacción")
            return None, {}
        
        email_lower = email.strip().lower()
        
        # Buscar transacciones Redsys recientes (últimas 48h) que contengan este email
        recent_txs = self.env['payment.transaction'].sudo().search([
            ('state', 'in', ['done', 'authorized']),
            ('provider_code', '=', 'redsys'),
            ('booking_data_json', '!=', False),
            ('create_date', '>=', fields.Datetime.now() - relativedelta(hours=48)),
        ], order='id desc', limit=20)
        
        for tx in recent_txs:
            try:
                booking_data = json.loads(tx.booking_data_json) if tx.booking_data_json else {}
                tx_email = (booking_data.get('customer_email') or '').strip().lower()
                if tx_email == email_lower:
                    _logger.info(f"WIZARD: Transacción encontrada por email - TX ID={tx.id}, amount={tx.amount}")
                    return tx, booking_data
            except Exception as e:
                _logger.warning(f"WIZARD: Error parseando booking_data de TX {tx.id}: {e}")
                continue
        
        _logger.warning(f"WIZARD: No se encontró transacción para email {email}")
        return None, {}

    def action_create_rental_contract(self):
        """Create rental contract from lead"""
        # Buscar transacción Redsys por email (más fiable)
        tx, booking_data = self._find_redsys_transaction()
        
        # Obtener precio por día desde booking_data
        daily_rate = 0.0
        total_paid = 0.0
        num_days = 1
        
        if booking_data:
            try:
                daily_rate = float(booking_data.get('selected_price', 0.0))
                total_paid = float(booking_data.get('total_price', 0.0))
                num_days = int(booking_data.get('num_days', 1)) or 1
                _logger.info(f"WIZARD: booking_data encontrado - daily_rate={daily_rate}, total_paid={total_paid}, num_days={num_days}")
            except (ValueError, TypeError) as e:
                _logger.warning(f"WIZARD: Error parseando precios de booking_data: {e}")
        
        # Fallback: calcular desde tx.amount si no hay daily_rate
        if not daily_rate and tx and self.start_date and self.end_date:
            days = (self.end_date.date() - self.start_date.date()).days or 1
            daily_rate = (tx.amount or 0.0) / max(1, days)
            total_paid = tx.amount or 0.0
            num_days = days
            _logger.info(f"WIZARD: Fallback - daily_rate calculado={daily_rate}, total_paid={total_paid}")
        
        # Si aún no tenemos total_paid pero tenemos tx
        if not total_paid and tx:
            total_paid = tx.amount or 0.0
        
        # Obtener ubicación
        location = (booking_data.get('location') or getattr(self.crm_lead_id, 'location', '') or '')
        
        # Buscar provincia/estado por nombre de ubicación
        state_id = False
        if location:
            state = self.env['res.country.state'].search([
                ('country_id.code', '=', 'ES'),
                ('name', 'ilike', location)
            ], limit=1)
            if state:
                state_id = state.id
        
        # España por defecto
        spain = self.env['res.country'].search([('code', '=', 'ES')], limit=1)
        
        contract_vals = {
            'crm_lead_id': self.crm_lead_id.id,
            'customer_id': self.partner_id.id,
            'customer_phone': self.partner_id.phone,
            'customer_email': self.partner_id.email,
            'vehicle_id': self.vehicle_id.id,
            'model_year': self.vehicle_id.model_year,
            'transmission': self.vehicle_id.transmission,
            'fuel_type': self.vehicle_id.fuel_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'pick_up_city': location,
            'drop_off_city': location,
            'pick_up_state_id': state_id,
            'pick_up_country_id': spain.id if spain else False,
            'drop_off_state_id': state_id,
            'drop_off_country_id': spain.id if spain else False,
            'rent': daily_rate,  # Precio por día
            'rent_type': 'days',  # Tipo de alquiler: días
            'discount_reason': 'Precio de reserva web',  # Auto-rellenado para evitar validación
        }
        
        _logger.info(f"WIZARD: Creando contrato con rent={daily_rate} €/día")
        
        # ============================================
        # CREAR SALE.ORDER PARA INTEGRACIÓN CON VENTAS
        # ============================================
        sale_order = self._create_sale_order(
            partner=self.partner_id,
            lead=self.crm_lead_id,
            vehicle=self.vehicle_id,
            start_date=self.start_date,
            end_date=self.end_date,
            daily_rate=daily_rate,
            total_paid=total_paid,
            num_days=num_days,
            tx=tx,
        )
        _logger.info(f"WIZARD: Sale.order creado: {sale_order.name if sale_order else 'None'}")
        
        # Añadir sale_order_id a contract_vals
        if sale_order:
            contract_vals['sale_order_id'] = sale_order.id
        
        contract = self.env['vehicle.contract'].create(contract_vals)
        self.crm_lead_id.contract_id = contract.id
        
        # Vincular sale.order con el contrato
        if sale_order:
            sale_order.vehicle_contract_id = contract.id
        
        # Crear línea en Detalles de pago del vehículo con el cobro Redsys (total pagado)
        if tx and total_paid > 0:
            self.env['vehicle.payment.option'].sudo().create({
                'name': f'Pago online Redsys ({tx.reference})',
                'payment_date': fields.Date.context_today(self),
                'payment_amount': total_paid,  # TOTAL pagado, no precio/día
                'vehicle_contract_id': contract.id,
                'company_id': contract.company_id.id,
                'currency_id': contract.currency_id.id,
            })
            _logger.info(f"WIZARD: Creada línea de pago Redsys por {total_paid}€")
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vehicle.contract',
            'res_id': contract.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_sale_order(self, partner, lead, vehicle, start_date, end_date, daily_rate, total_paid, num_days, tx=None):
        """
        Crear sale.order vinculado al lead para que aparezca en Ventas.
        El pedido se crea como confirmado ya que el pago está realizado.
        """
        try:
            # Obtener producto de alquiler
            rental_product = self.env.ref('vehicle_rental.vehicle_rent_charge', raise_if_not_found=False)
            if not rental_product:
                _logger.warning("WIZARD: Producto vehicle_rent_charge no encontrado, no se creará sale.order")
                return None
            
            # Obtener compañía del vehículo o del lead
            company = vehicle.company_id or lead.company_id or self.env.company
            
            # Preparar líneas del pedido
            order_lines = []
            
            # Línea principal: Alquiler del vehículo
            vehicle_name = f"{vehicle.model_id.brand_id.name}/{vehicle.model_id.name}" if vehicle.model_id else vehicle.name
            rental_description = (
                f"Alquiler de vehículo - {vehicle_name} | "
                f"Matrícula: {vehicle.license_plate} | "
                f"Período: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')} | "
                f"Días: {num_days}"
            )
            rental_line = {
                'product_id': rental_product.id,
                'name': rental_description,
                'product_uom_qty': num_days,
                'price_unit': daily_rate,
            }
            order_lines.append((0, 0, rental_line))
            
            # Crear el sale.order
            sale_note = f"Reserva web - Pago Redsys: {tx.reference if tx else 'N/A'} | Total pagado: {total_paid:.2f}€"
            sale_vals = {
                'partner_id': partner.id,
                'opportunity_id': lead.id,
                'company_id': company.id,
                'vehicle_id': vehicle.id,
                'rental_start_date': start_date,
                'rental_end_date': end_date,
                'order_line': order_lines,
                'note': sale_note,
            }
            
            sale_order = self.env['sale.order'].sudo().create(sale_vals)
            
            # Confirmar el pedido automáticamente (ya está pagado)
            sale_order.action_confirm()
            
            _logger.info(f"WIZARD: Sale.order {sale_order.name} creado y confirmado para lead {lead.id}")
            
            return sale_order
            
        except Exception as e:
            _logger.error(f"WIZARD: Error creando sale.order: {e}", exc_info=True)
            return None
