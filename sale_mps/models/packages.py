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
        _log.info(" VALS in WRITE::: %s " % vals)
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
        total_qty = sum(selected_quants.mapped('quantity'))
        _log.info(" cantidad de producto ::: %s" % total_qty)
        sale_line = self.sale_id.order_line.filtered(lambda x: x.product_id.id == self.product_id.id)
        sale_line.product_uom_qty = total_qty


class StockPickingMps(models.Model):
    _inherit = "stock.picking"

    @api.model
    def create(self, vals):
        _log.info("\n CREATE CONTEXT::: %s " % self._context)
        _log.info("\nCREATE VALS::: %s " % vals)
        picking = super(StockPickingMps, self).create(vals)
        # Create move lines
        mlids = []
        if 'mps_sale_id' in self._context:
            sale_id = self.env['sale.order'].browse(self._context.get('mps_sale_id'))
            _log.info("SALE ORDER ::: %s" % sale_id)
            wh_stock_id = sale_id.warehouse_id.lot_stock_id
            # Segúnda parte: agregar una condición para la selección manual o no.
            if wh_stock_id.id != picking.location_id.id:
                return picking
            # Then create move_line_ids_without_package
            for pack in sale_id.manual_package_ids.filtered(lambda x: x.selected == True):
                lot_id = pack.package_id.quant_ids.mapped('lot_id')[0]
                qty = sum(pack.package_id.quant_ids.filtered(lambda x: x.product_id.id == pack.product_id.id).mapped('quantity'))
                ml_data = {
                    'product_id': pack.product_id.id,
                    'package_id': pack.package_id.id,
                    'result_package_id': pack.package_id.id,
                    'lot_id': lot_id.id,
                    'product_uom_qty': qty,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'product_uom_id': lot_id.product_uom_id.id
                }
                mlids.append((0, 0, ml_data))

            picking.move_line_ids_without_package = mlids
            # clean context
            # context = dict(self._context)
            # context.pop('mps_sale_id')
            # self = self.with_context(context)

        return picking
