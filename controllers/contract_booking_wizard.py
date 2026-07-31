# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request

from ..models.vehicle_contract import BUSY_CONTRACT_STATES

_logger = logging.getLogger(__name__)


class ContractBookingWizardController(http.Controller):
    """Controller for manual contract booking wizard - handles availability calculations"""

    @http.route('/wizard/get-available-vehicles', type='json', auth='user')
    def get_available_vehicles(self, **kw):
        """Get availability counts for a category and date range (for internal wizard)"""
        try:
            category_id = int(kw.get('category_id', 0))
            start_date = kw.get('start_date')
            end_date = kw.get('end_date')
            company_id = int(kw.get('company_id', 1))
            search_text = kw.get('search_text', '').strip()

            _logger.warning(f"WIZARD: category_id={category_id}, start_date={start_date}, end_date={end_date}, company_id={company_id}")

            # 1. TOTAL: All vehicles in category with status='available'
            total_domain = [
                '|',
                ('category_id', '=', category_id),
                ('model_id.category_id', '=', category_id),
                ('company_id', '=', company_id),
                ('status', '=', 'available')
            ]
            total_vehicles = request.env['fleet.vehicle'].sudo().search(total_domain)
            total_count = len(total_vehicles)

            # 2. OCCUPIED: Vehicles with active contracts that overlap dates
            occupied_vehicles = set()
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    overlapping_contracts = request.env['vehicle.contract'].sudo().search([
                        ('status', 'in', list(BUSY_CONTRACT_STATES)),
                        ('start_date', '<=', end_dt),
                        ('end_date', '>=', start_dt),
                        ('vehicle_id.company_id', '=', company_id),
                    ])
                    
                    for contract in overlapping_contracts:
                        if contract.vehicle_id:
                            occupied_vehicles.add(contract.vehicle_id.id)
                except Exception as e:
                    _logger.error(f"Error calculating occupied: {e}")

            # 3. RESERVED: Draft contracts with assigned vehicles in those dates
            reserved_vehicles = set()
            if start_date and end_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    draft_contracts = request.env['vehicle.contract'].sudo().search([
                        ('status', '=', 'a_draft'),
                        ('start_date', '<=', end_dt),
                        ('end_date', '>=', start_dt),
                        ('vehicle_id', '!=', False),
                        ('vehicle_id.company_id', '=', company_id),
                    ])
                    
                    for contract in draft_contracts:
                        if contract.vehicle_id:
                            reserved_vehicles.add(contract.vehicle_id.id)
                except Exception as e:
                    _logger.error(f"Error calculating reserved: {e}")

            # 4. AVAILABLE = TOTAL - OCCUPIED - RESERVED
            occupied_count = len(occupied_vehicles)
            reserved_count = len(reserved_vehicles)
            available_count = max(0, total_count - occupied_count - reserved_count)

            # 5. Get available vehicles for list display (apply search if present)
            available_vehicle_list = []
            for vehicle in total_vehicles:
                if vehicle.id not in occupied_vehicles and vehicle.id not in reserved_vehicles:
                    # Apply search filter
                    if search_text:
                        search_lower = search_text.lower()
                        vehicle_name = vehicle.name.lower() if vehicle.name else ""
                        model_name = vehicle.model_id.name.lower() if vehicle.model_id else ""
                        if search_lower not in vehicle_name and search_lower not in model_name:
                            continue
                    
                    available_vehicle_list.append({
                        'id': vehicle.id,
                        'name': vehicle.name,
                        'model': vehicle.model_id.name if vehicle.model_id else '',
                        'license_plate': vehicle.license_plate,
                        'category': vehicle.category_id.name if vehicle.category_id else (
                            vehicle.model_id.category_id.name if vehicle.model_id and vehicle.model_id.category_id else ''
                        ),
                    })

            result = {
                'success': True,
                'total': total_count,
                'occupied': occupied_count,
                'reserved': reserved_count,
                'available': available_count,
                'vehicles': available_vehicle_list,
                'message': f'Disponibles: {available_count} vehículos' if available_count > 0 else 'No hay vehículos disponibles'
            }

            return result

        except Exception as e:
            _logger.error(f"Error in get_available_vehicles: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Error al calcular disponibilidad'
            }
