# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)


class StockPickingCustom(models.Model):
    _inherit = "stock.picking"

    use_multiplier = fields.Boolean(string="Usar multiplicador", compute="_check_use_multiplier", store=False)

    def _check_use_multiplier(self):
        use_multiplier = True if self.picking_type_id and self.picking_type_id.use_multiplier else False
        self.use_multiplier = use_multiplier
        return use_multiplier


class StockPickingTypeCustom(models.Model):
    _inherit = "stock.picking.type"

    use_multiplier = fields.Boolean(string="Usa multiplicador", default=False)
