# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_log = logging.getLogger("\n ===============[%s]===============" % __name__)


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    manual_package_ids = fields.One2many('sale.mps', 'sale_id', string="Selección manual de paquetes")

    @api.onchange('order_line')
    def calc_packages(self):
        """
        Método que calcula las opciones de paquetes para que el usuario pueda escoger.
        :return:
        """
        wh_stock_id = self.warehouse_id.lot_stock_id
        line_product_ids = self.order_line.mapped('product_id')
        self.manual_package_ids = False
        stock_quant_ids = self.env['stock.quant'].search([
            ('package_id', '!=', False),
            ('product_id', 'in', line_product_ids.ids),
            ('quantity', '>', 0),
            ('location_id', '=', wh_stock_id.id)
        ])
        if not stock_quant_ids:
            return
        package_ids = stock_quant_ids.mapped('package_id')

        # Clean manual_package_ids
        self.manual_package_ids = [(5, 0, 0)]
        packages = []
        for pa in package_ids:
            fproduct_id = None
            for sq in pa.quant_ids:
                if sq.product_id.id in line_product_ids.ids:
                    fproduct_id = sq.product_id.id
                    break
            pa_data = {
                'selected': False,
                'package_id': pa.id,
            }
            if fproduct_id is not None:
                pa_data['product_id'] = fproduct_id
            packages.append((0, 0, pa_data))
        self.manual_package_ids = packages

    def action_confirm(self):
        self = self.with_context(mps_sale_id=self.id)
        res = super(SaleOrderInherit, self).action_confirm()
        return res
