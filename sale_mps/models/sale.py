# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_log = logging.getLogger("\n ===============[%s]===============" % __name__)


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    manual_package_ids = fields.One2many('sale.mps', 'sale_id', string="Selección manual de paquetes")

    @api.depends('order_line')
    def calc_packages(self):
        _log.info("Calculando paquetes para las lineas: %s" % self.order_line)
        line_product_ids = self.order_line.mapped('product_id')

