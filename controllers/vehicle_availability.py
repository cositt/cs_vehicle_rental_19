# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request


class VehicleContractController(http.Controller):
    """Vehicle contract controller"""

    @http.route('/get/contract/data', type='json', auth="user")
    def get_contract_data(self):
        """
        Retrieve vehicle contract data for Gantt chart visualization.

        Fetches all active vehicle contracts (excluding 'd_cancel' status).
        Extracts details like contract ID, vehicle name, reference number,
        start and end dates, and returns structured JSON data.

        Returns:
            dict: A dictionary containing contract data formatted for Gantt charts.
        """

        # Retrieve selected company IDs from cookies
        selected_company_ids = request.httprequest.cookies.get('cids')
        if selected_company_ids:
            company_ids = list(map(int, selected_company_ids.split('-')))
        else:
            company_ids = [request.env.company.id]
        # Search for vehicle contracts excluding canceled ones
        contracts = request.env['vehicle.contract'].sudo().search([
            ('status', '!=', 'd_cancel'),
            ('company_id', 'in', company_ids)
        ])
        # Prepare Gantt chart data
        gantt_chart_data = [
            {
                'id': contract.id,
                'text': contract.vehicle_id.name,
                'name': contract.reference_no,
                'start_date': contract.start_date.strftime("%d-%m-%Y %H:%M:%S"),
                'end_date': contract.end_date.strftime("%d-%m-%Y %H:%M:%S"),
                'order': 10,
                'progress': 0.6,
            }
            for contract in contracts if contract.start_date and contract.end_date
        ]

        return {'data': gantt_chart_data}
