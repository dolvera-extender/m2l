# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class StockPickingM2lr(models.Model):
    _inherit = "stock.picking"


    pcover_id = fields.Many2one('pcover.report.history', string="Reporte de portada")


class StockMoveLineM2l(models.Model):
    _inherit = "stock.move.line"

    product_category_id = fields.Many2one('product.category', string="Categoria del producto", related="product_id.categ_id")
    pol_invoice_ref = fields.Char(string="Factura", compute="_compute_invoice_ref", store=False)
    pol_asn_ref = fields.Char(string="ASN", compute="_compute_invoice_ref", store=False)

    def _compute_invoice_ref(self):
        for rec in self:
            _log.info(" linea de compra :: %s -->> FACTURA :: %s" % (rec.move_id.purchase_line_id, rec.move_id.purchase_line_id.x_studio_no_factura))
            if rec.move_id and rec.move_id.purchase_line_id:
                rec.pol_invoice_ref = rec.move_id.purchase_line_id.x_studio_no_factura
                rec.pol_asn_ref = rec.move_id.purchase_line_id.x_studio_asn
            else:
                rec.pol_invoice_ref = ""
                rec.pol_asn_ref = ""

class StockPickingTypeRm2l(models.Model):
    _inherit = "stock.picking.type"

    to_pcover = fields.Boolean(string="Portada embarques", default=False)

