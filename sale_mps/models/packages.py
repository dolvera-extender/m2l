# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_log = logging.getLogger("\n ===============[%s]===============" % __name__)


class SaleMps(models.Model):
    _name = "sale.mps"
    _description = "Movimiento manual de paquetes"
    # _order = "package_id asc"

    # selected = fields.Boolean(string="Selecto")
    sale_id_av = fields.Many2one('sale.order', string="Pedido de venta")
    sale_id_se = fields.Many2one('sale.order', string="Pedido de venta")
    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    product_id = fields.Many2one('product.product', string="producto")

    def mps_select(self):
        self.sale_id_se = self.sale_id_av.id
        self.sale_id_av = False
        self.update_qty_selected()

    def mps_unselect(self):
        self.sale_id_av = self.sale_id_se.id
        self.sale_id_se = False
        self.update_qty_selected()

    def update_qty_selected(self):
        so = self.sale_id_se if self.sale_id_se else self.sale_id_av
        ol = so.order_line.filtered(lambda x: x.product_id.id == self.product_id.id)
        quants_used = so.manual_package_selected_ids \
            .mapped('package_id') \
            .mapped('quant_ids') \
            .filtered(lambda x: x.product_id.id == self.product_id.id)
        quantity = sum(quants_used.mapped('quantity'))
        ol.product_uom_qty = quantity


class StockPickingMps(models.Model):
    _inherit = "stock.picking"

    sale_order_id = fields.Many2one("sale.order", string="Venta")

    @api.model
    def create(self, vals):
        _log.info("\n CREATE CONTEXT::: %s " % self._context)
        _log.info("\nCREATE VALS::: %s " % vals)
        picking = super(StockPickingMps, self).create(vals)
        # Create move lines
        # mlids = []
        if 'mps_sale_id' in self._context:
            sale_id = self.env['sale.order'].browse(self._context.get('mps_sale_id'))
            picking.sale_order_id = sale_id.id
            _log.info("SALE ORDER ::: %s" % sale_id)
            # wh_stock_id = sale_id.warehouse_id.lot_stock_id
            # # Segúnda parte: agregar una condición para la selección manual o no.
            # if wh_stock_id.id != picking.location_id.id:
            #     return picking
            # # Then create move_line_ids_without_package
            # for pack in sale_id.manual_package_ids.filtered(lambda x: x.selected == True):
            #     lot_id = pack.package_id.quant_ids.mapped('lot_id')[0]
            #     qty = sum(pack.package_id.quant_ids.filtered(lambda x: x.product_id.id == pack.product_id.id).mapped('quantity'))
            #     ml_data = {
            #         'product_id': pack.product_id.id,
            #         'package_id': pack.package_id.id,
            #         'result_package_id': pack.package_id.id,
            #         'lot_id': lot_id.id,
            #         'product_uom_qty': qty,
            #         'location_id': picking.location_id.id,
            #         'location_dest_id': picking.location_dest_id.id,
            #         'product_uom_id': lot_id.product_uom_id.id
            #     }
            #     mlids.append((0, 0, ml_data))
            #
            # picking.move_line_ids_without_package = mlids
            # # clean context
            # context = dict(self._context)
            # context.pop('mps_sale_id')
            # self = self.with_context(context)

        return picking
