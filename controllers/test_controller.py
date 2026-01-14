# -*- coding: utf-8 -*-
# Controlador de prueba para verificar vehículos

from odoo import http
from odoo.http import request


class TestController(http.Controller):
    """Controlador de prueba"""

    @http.route('/test/vehicles', type='http', auth='public', website=True)
    def test_vehicles(self, **kw):
        """Página de prueba para verificar vehículos"""
        try:
            # Obtener vehículos reales de la base de datos
            vehicles = request.env['fleet.vehicle'].sudo().search([])
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Vehículos</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .vehicle {{ border: 1px solid #ccc; margin: 10px; padding: 10px; }}
                </style>
            </head>
            <body>
                <h1>Test de Vehículos</h1>
                <p>Total de vehículos encontrados: {len(vehicles)}</p>
                <div>
            """
            
            for vehicle in vehicles:
                html += f"""
                    <div class="vehicle">
                        <h3>ID: {vehicle.id}</h3>
                        <p><strong>Nombre:</strong> {vehicle.name or 'Sin nombre'}</p>
                        <p><strong>Matrícula:</strong> {vehicle.license_plate or 'Sin matrícula'}</p>
                        <p><strong>Modelo:</strong> {vehicle.model_id.name if vehicle.model_id else 'Sin modelo'}</p>
                        <p><strong>Marca:</strong> {vehicle.brand_id.name if vehicle.brand_id else 'Sin marca'}</p>
                    </div>
                """
            
            html += """
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            return f"<h1>Error: {str(e)}</h1>"















    @http.route('/test/trigger-lead', auth='public', type='json', csrf=False)
    def trigger_lead_creation(self, **kw):
        """Test endpoint para disparar creación de Lead"""
        try:
            Payment = request.env['payment.transaction'].sudo()
            tx = Payment.search([('reference', '=', 'TEST_FINAL_LEAD')], limit=1)
            
            if not tx:
                return {'status': 'error', 'message': 'TX no encontrada'}
            
            # Ejecutar _apply_updates
            tx._apply_updates({})
            request.env.cr.commit()
            
            # Verificar Lead creado
            leads = request.env['crm.lead'].sudo().search([('description', 'like', f'TX:{tx.id}')])
            
            return {
                'status': 'ok',
                'tx_id': tx.id,
                'leads_created': len(leads),
                'lead_ids': [l.id for l in leads]
            }
        except Exception as e:
            import traceback
            return {
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }
