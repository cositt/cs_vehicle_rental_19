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

        selected_company_ids = request.httprequest.cookies.get('cids')
        company_ids = [int(cid) for cid in selected_company_ids.split('-') if cid.isdigit()] \
            if selected_company_ids else [request.env.company.id]
        contracts = request.env['vehicle.contract'].with_context(allowed_company_ids=company_ids)
        return {'data': contracts._availability_chart_data()}
