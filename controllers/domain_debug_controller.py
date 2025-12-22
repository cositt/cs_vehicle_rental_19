# -*- coding: utf-8 -*-
# Debug controller para verificar el dominio

from odoo import http
from odoo.http import request


class DomainDebugController(http.Controller):
    """Controlador para debug de dominios"""

    @http.route('/debug/domain', type='http', auth='public', website=True)
    def debug_domain(self, **kw):
        """Muestra información del dominio actual"""
        info = {
            'host': request.httprequest.host,
            'host_url': request.httprequest.host_url,
            'base_url': request.httprequest.base_url,
            'url': request.httprequest.url,
            'headers': dict(request.httprequest.headers),
        }
        
        html = "<h1>Debug de Dominio</h1>"
        html += "<pre>"
        for key, value in info.items():
            html += f"{key}: {value}\n"
        html += "</pre>"
        
        return html


