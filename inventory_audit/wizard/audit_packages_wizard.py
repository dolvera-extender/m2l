# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
import logging

_log = logging.getLogger(__name__)


class PackagesAuditWizard(models.TransientModel):
    _name = "ia.packages.audit.wizard"
    _description = "Leer paquetes a auditar"

    def _get_default_lines(self):
        _log.info(" CONTEXTO :: %s " % self._context)
        return False

    location_id = fields.Many2one('stock.location', string="Ubicaciòn")
    package_name_read = fields.Char(string="Paquete leído")
    package_line_ids = fields.Many2many('ia.packages.audit.wizard.line', default=_get_default_lines)

class PackageAuditWizardLine(models.TransientModel):
    _name = "ia.packages.audit.wizard.line"
    _description = "Paquetes a verificar"

    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    current_location_id = fields.Many2one('stock.location', string="Ubicación fisica actual")
    location_des_id = fields.Many2one('stock.location', string="Ubicación fisica esperada")
    to_move = fields.Boolean(string="A mover", default=False)
    read_line = fields.Boolean(string="Escaneado")

    