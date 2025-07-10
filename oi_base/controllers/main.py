# -*- coding: utf-8 -*-

from odoo import http

class ConnectionTest(http.Controller):
    
    @http.route('/ping', type='http', auth='none', methods=['GET'], csrf=False, save_session=False)
    def test(self, *arg, **kw):
        return 'OK'
    