# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError
import logging

_log = logging.getLogger(__name__)


class StockPackageAudit(models.Model):
    _name = "stock.package.audit"
    _description = "Rectificación  de existencias."

    name = fields.Char(string="Nombre")
    location_id = fields.Many2one('stock.location', string="Ubicación")
    audit_date = fields.Datetime(string="Fecha revisión")
    picking_id = fields.Many2one('stock.picking')
    audit_line_ids = fields.One2many('stock.package.audit.line', 'package_audit_id', string="Paquetes")

    def generate_move(self):
        pass

    def generate_pdf_report(self):
        pass


class StockPackageAuditLine(models.Model):
    _name = "stock.package.audit.line"
    _description = "Rectificación  de existencias."

    package_audit_id = fields.Many2one('stock.package.audit', string="Auditoria")
    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    location_id = fields.Many2one('stock.location', string="Ubicación en odoo")
    moved = fields.Boolean(string="Transferido", default=False)
