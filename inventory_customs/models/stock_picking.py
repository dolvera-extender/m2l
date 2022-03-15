# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)


class StockPickingCustom(models.Model):
    _inherit = "stock.picking"

    use_multiplier = fields.Boolean(string="Usar multiplicador", compute="_check_use_multiplier", store=False)
    product_to_multiply = fields.Many2one('product.product', string="Producto a multiplicar")
    product_tm_domain = fields.One2many('product.product', 'product_multiplier_domain',
                                        string="Product tm domain", compute="_get_product_mult_domain", store=False)
    product_pack_qty = fields.Integer(string="Cantidad por paquete")
    product_av_qty = fields.Integer(string="Cantidad a empaquetar")

    def _check_use_multiplier(self):
        use_multiplier = True if self.picking_type_id and self.picking_type_id.use_multiplier else False
        self.use_multiplier = use_multiplier
        return use_multiplier

    def multiply_product(self):
        """
        Method that create packages with computed number of lots for stock picking.
        Use the field move_ids_without_package
        :return:
        """
        _log.info("Usando multiplicador.")
        pass

    @api.onchange('product_to_multiply')
    def default_product_av_qty(self):
        pass

    def _get_product_mult_domain(self):
        domain = []
        _log.info("______________ CONTEXT :::: %s " % self.env.context)
        _log.info("___________picking:: %s " % self)
        _log.info("Lineas del picking:: %s " % self.move_ids_without_package)
        move_product_ids = self.move_ids_without_package.ids if self.move_ids_without_package else []
        if len(move_product_ids) > 0:
            domain.append(('id', 'in', move_product_ids))
            self.product_tm_domain = [(6, 0, move_product_ids)]


class StockPickingTypeCustom(models.Model):
    _inherit = "stock.picking.type"

    use_multiplier = fields.Boolean(string="Usa multiplicador", default=False)


class ProductProductMultiply(models.Model):
    _inherit = "product.product"

    product_multiplier_domain = fields.Many2one('stock.picking', 'Movimiento multiplicado')
