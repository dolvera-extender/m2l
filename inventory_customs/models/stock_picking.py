# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)


class StockPickingCustom(models.Model):
    _inherit = "stock.picking"

    is_entry = fields.Boolean(string="Es entrada", compute="_check_if_is_entry", store=False)

    def _check_if_is_entry(self):
        is_entry = True if self.picking_type_id and self.picking_type_id.name == "Recepciones" else False
        self.is_entry = is_entry
        return is_entry
