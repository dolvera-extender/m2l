# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_log = logging.getLogger("\n ===============[%s]===============" % __name__)


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    manual_package_available_ids = fields.One2many('sale.mps', 'sale_id_av', string="Paquetes disponibles")
    manual_package_selected_ids = fields.One2many('sale.mps', 'sale_id_se', string="Paquetes seleccionados")
    mps_product_domain = fields.Many2many('product.product', string="Dominio del producto",
                                          compute="_compute_mpsp_domain", store=False)
    mps_product_id = fields.Many2one("product.product", string="Producto a filtrar")

    def _compute_mpsp_domain(self):
        sale_product_ids = self.order_line.mapped('product_id').ids
        if len(sale_product_ids) > 0:
            self.mps_product_domain = [(6, 0, sale_product_ids)]
        else:
            self.mps_product_domain = False

    @api.onchange('mps_product_id')
    def calc_packages(self):
        """
        La idea es tener dos listas de paquetes,una oculta y otra que se muestra.
        la que se muestra estará siempre filtrada por el producto seleccionado arriba,
        y se reecalculará en base a ese producto.
        La oculta solo guardará los paquetes (misma estructura) que hayan sido seleccionados
        en la que se muestra, de la misma forma los quitará cuando en la lista mostrada se marquen
        como no seleccionados.
        Para esto cada que se calcule la vista de arriba consultará la lista de paquetes ya marcados
        para marcarlos como seleccionados.
        :return:
        """
        """
        Método que calcula las opciones de paquetes para que el usuario pueda escoger.
        :return:
        """
        wh_stock_id = self.warehouse_id.lot_stock_id
        wh_stock_leaf_ids = wh_stock_id.child_ids
        wh_dom = wh_stock_leaf_ids.ids
        wh_dom.append(wh_stock_id.id)
        # line_product_ids = self.order_line.mapped('product_id')
        self.manual_package_available_ids = False
        stock_quant_ids = self.env['stock.quant'].search([
            ('package_id', '!=', False),
            ('product_id', '=', self.mps_product_id.id),
            ('quantity', '>', 0),
            ('location_id', 'in', wh_dom)
        ])
        if not stock_quant_ids:
            return
        package_ids = stock_quant_ids.mapped('package_id')

        # Clean manual_package_ids
        # self.manual_package_available_ids = [(5, 0, 0)]
        packages = []
        selected_packages = self.manual_package_selected_ids.mapped('package_id')
        for pa in package_ids:
            if pa.id in selected_packages.ids:
                continue
            fproduct_id = None
            for sq in pa.quant_ids:
                if sq.product_id.id == self.mps_product_id.id:
                    fproduct_id = sq.product_id.id
                    break
            pa_data = {
                # 'selected': False,
                'package_id': pa.id,
            }
            if fproduct_id is not None:
                pa_data['product_id'] = fproduct_id
            packages.append((0, 0, pa_data))
        self.manual_package_available_ids = packages
        self.mps_product_id = False

    def action_confirm(self):
        self = self.with_context(mps_sale_id=self.id)
        res = super(SaleOrderInherit, self).action_confirm()
        return res
