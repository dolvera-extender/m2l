# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError
import logging

_log = logging.getLogger(__name__)


class PackagesAuditWizard(models.TransientModel):
    _name = "ia.packages.audit.wizard"
    _description = "Leer paquetes a auditar"

    def _get_default_lines(self):
        package_arr_ids = [pack_id['id'] for pack_id in self._context.get('ai_package_ids', [])]
        package_ids = self.env['stock.quant.package'].browse(package_arr_ids)
        result = []
        for package in package_ids:
            line = (0,0,{
                'package_id': package.id,
                'location_des_id': package.location_id.id
            })
            result.append(line)
        if len(result)<=0:
            return False
        return result

    location_id = fields.Many2one('stock.location', string="Ubicaciòn")
    package_name_read = fields.Char(string="Paquete leído")
    package_line_ids = fields.Many2many('ia.packages.audit.wizard.line', string="Paquetes de la ubicación", default=_get_default_lines)
  

    def process_audit(self):
        _log.info("PROCESANDO TRASPASO")
        pass

    @api.onchange('package_name_read')
    def read_barcode(self):
        _log.info(" lectura detectada en wizard ")
        if self.package_name_read == "" or not self.package_name_read:
            return
        code_read = self.package_name_read
        self.package_name_read = ""
        _log.info(" CODIGO LEIDO %s " % code_read)
        line = self.package_line_ids.filtered(lambda p: p.package_id.name == code_read)
        if line:
            line.read_line = True
        else:
            other_location_pack = self.env['stock.quant.package'].search([('name', '=', code_read)], limit=1)
            if not other_location_pack:
                raise UserError("No se encuentra en el sistema el paquete %s " % code_read)
            
            self.package_line_ids = [(0,0,{
                'package_id': other_location_pack.id,
                'current_location_id': self.location_id.id,
                'to_move': True
            })]

class PackageAuditWizardLine(models.TransientModel):
    _name = "ia.packages.audit.wizard.line"
    _description = "Paquetes a verificar"

    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    current_location_id = fields.Many2one('stock.location', string="Ubicación fisica actual")
    location_des_id = fields.Many2one('stock.location', string="Ubicación fisica esperada")
    to_move = fields.Boolean(string="A mover", default=False)
    read_line = fields.Boolean(string="Escaneado", default=False)

    