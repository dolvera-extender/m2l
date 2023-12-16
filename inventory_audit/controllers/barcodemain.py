# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.osv import expression
from odoo.tools import pdf, split_every
from odoo.tools.misc import file_open
import logging

_log = logging.getLogger(__name__)


class StockBarcodeController(http.Controller):

    @http.route('/ia_package_barcode/scan_package_barcode', type='json', auth='user')
    def read_package(self, barcode, **kw):
        """ Receive a barcode scanned from the main menu and return the appropriate
            action (open an existing / new picking) or warning.
        """
        barcode = barcode.replace("'","-")
        _log.info(" LECTURA HECHA ... %s  " % barcode) 
        location = request.env['stock.location'].search_read([('name','=like', barcode)], ['id'], limit=1)
        if len(location) <= 0:
            return {'warning': _('No existe una ubicación para el código leído %(bcode)s') % {'bcode': barcode}}
        packages = request.env['stock.quant.package'].search_read([('location_id','=', location[0]['id'])], ['id'])
        if len(packages) <= 0:
            return {'warning': _('La ubicaciòn %(bcode)s no contiene paquetes ') % {'bcode': barcode}}
        _log.info(" PAQUETES EN ESA UBICACIÓN. %s " % packages)
        wizard_view_id = request.env.ref('inventory_audit.ai_packages_wizard_form_view').id        
        return {
                'action': {
                    'name': "Verificacion de paquetes",
                    'res_model': 'ia.packages.audit.wizard',
                    'views': [(wizard_view_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'domain': [],
                    'context': {
                        'default_location_id': location[0]['id'],
                        'ai_package_ids': packages
                    }
                }
            }
  

    
