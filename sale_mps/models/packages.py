# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_log = logging.getLogger("\n ===============[%s]===============" % __name__)


class SaleMps(models.Model):
    _name = "sale.mps"
    _description = "Movimiento manual de paquetes"

    selected = fields.Boolean(string="Selecto")
    sale_id = fields.Many2one('sale.order', string="Pedido de venta")
    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    product_id = fields.Many2one('product.product', string="producto")

    def write(self, vals):
        res = super(SaleMps, self).write(vals)
        if 'selected' in vals:
            self.recalc_product_line_qty()
        return res

    def recalc_product_line_qty(self):
        # Recalc product qty
        if self.sale_id.state not in ['draft']:
            return
        selected_quants = self.sale_id.manual_package_ids.\
            filtered(lambda x: x.product_id.id == self.product_id.id and x.selected is True).\
            mapped('package_id').mapped('quant_ids').filtered(lambda x: x.product_id.id == self.product_id.id)
        total_qty = sum(selected_quants.mapped('reserved_quantity'))
        _log.info(" 1RECALCULANDO con las lineas de paks ::: %s" % total_qty)
        sale_line = self.sale_id.order_line.filtered(lambda x: x.product_id.id == self.product_id.id)
        sale_line.product_uom_qty = total_qty
