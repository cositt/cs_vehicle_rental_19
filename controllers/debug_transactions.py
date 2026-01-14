# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class DebugTransactionsController(http.Controller):
    @http.route('/debug/transactions', auth='public', type='http')
    def debug_transactions(self, **kw):
        """Debug endpoint para ver transacciones recientes"""
        try:
            tx_list = request.env['payment.transaction'].sudo().search([], order='id desc', limit=20)
            
            html = "<h1>Transacciones Recientes</h1><table border='1'><tr><th>ID</th><th>Reference</th><th>State</th><th>Amount</th><th>Booking Created</th><th>Has Booking Data</th><th>Created</th></tr>"
            
            for tx in tx_list:
                html += f"<tr><td>{tx.id}</td><td>{tx.reference}</td><td>{tx.state}</td><td>{tx.amount}</td><td>{tx.booking_created}</td><td>{bool(tx.booking_data_json)}</td><td>{tx.create_date}</td></tr>"
            
            html += "</table>"
            
            # Buscar leads recientes
            html += "<h2>Leads Recientes</h2><table border='1'><tr><th>ID</th><th>Name</th><th>Company</th><th>Email</th><th>Vehicle</th><th>Created</th></tr>"
            
            leads = request.env['crm.lead'].sudo().search([], order='id desc', limit=20)
            for lead in leads:
                html += f"<tr><td>{lead.id}</td><td>{lead.name}</td><td>{lead.company_id.name if lead.company_id else 'None'}</td><td>{lead.email_from}</td><td>{lead.vehicle_id.name if lead.vehicle_id else 'None'}</td><td>{lead.create_date}</td></tr>"
            
            html += "</table>"
            
            return html
        except Exception as e:
            return f"Error: {str(e)}"

    @http.route('/debug/providers', auth='public', type='http')
    def debug_providers(self, **kw):
        """Debug endpoint para ver proveedores de pago"""
        try:
            providers = request.env['payment.provider'].sudo().search([])
            
            html = "<h1>Proveedores de Pago</h1><table border='1'><tr><th>ID</th><th>Name</th><th>Code</th><th>State</th></tr>"
            
            for prov in providers:
                html += f"<tr><td>{prov.id}</td><td>{prov.name}</td><td>{prov.code}</td><td>{prov.state}</td></tr>"
            
            html += "</table>"
            
            # Mostrar Redsys específicamente
            html += "<h2>Provider Redsys</h2>"
            redsys = request.env['payment.provider'].sudo().search([('code', '=', 'redsys')], limit=1)
            if redsys:
                html += f"<p><strong>Redsys Provider ID:</strong> {redsys.id}</p>"
                html += f"<p><strong>Name:</strong> {redsys.name}</p>"
                html += f"<p><strong>State:</strong> {redsys.state}</p>"
            else:
                html += "<p>⚠ No hay provider Redsys configurado</p>"
            
            return html
        except Exception as e:
            return f"Error: {str(e)}"


    @http.route('/debug/tx/<int:tx_id>', auth='public', type='http')
    def debug_tx_detail(self, tx_id, **kw):
        """Mostrar detalles completos de una transacción"""
        try:
            tx = request.env['payment.transaction'].sudo().browse(tx_id)
            if not tx.exists():
                return f"Transacción {tx_id} no encontrada"
            
            html = f"<h1>Detalles de Transacción {tx_id}</h1>"
            html += f"<table><tr><th>Campo</th><th>Valor</th></tr>"
            html += f"<tr><td>Reference</td><td>{tx.reference}</td></tr>"
            html += f"<tr><td>State</td><td>{tx.state}</td></tr>"
            html += f"<tr><td>Amount</td><td>{tx.amount} {tx.currency_id.name}</td></tr>"
            html += f"<tr><td>Provider</td><td>{tx.provider_id.name}</td></tr>"
            html += f"<tr><td>Booking Created</td><td>{tx.booking_created}</td></tr>"
            html += f"<tr><td>Booking Data</td><td><pre>{tx.booking_data_json or 'Vacío'}</pre></td></tr>"
            html += f"<tr><td>Create Date</td><td>{tx.create_date}</td></tr>"
            html += f"<tr><td>State Message</td><td>{tx.state_message or 'N/A'}</td></tr>"
            html += f"</table>"
            
            return html
        except Exception as e:
            return f"Error: {str(e)}"


    @http.route('/debug/company', auth='public', type='http')
    def debug_company(self, **kw):
        """Mostrar información de la compañía actual"""
        try:
            company = request.env.company
            
            html = f"<h1>Información de Compañía</h1>"
            html += f"<p><strong>Company ID:</strong> {company.id}</p>"
            html += f"<p><strong>Company Name:</strong> {company.name}</p>"
            html += f"<p><strong>Currency:</strong> {company.currency_id.name}</p>"
            html += f"<p><strong>Currency ID:</strong> {company.currency_id.id}</p>"
            
            return html
        except Exception as e:
            return f"Error: {str(e)}"

