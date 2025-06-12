# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class StockQuantInherit(models.Model):
    _inherit = "stock.quant"

    total_rack = fields.Float(related="location_id.total_rack")
    percentage_ocupado = fields.Float(related="location_id.percentage_ocupado")
    qty_rack_free = fields.Float(related="location_id.qty_rack_free")

    @api.constrains('quantity','location_id')
    def _constrains_quantity_loc(self):
        for rec in self:
            if rec.location_id and rec.location_id.usage == 'internal':
                rec.location_id._compute_quantity_rack()

class StockQuantPackageInherit(models.Model):
    _inherit = "stock.quant.package"

    total_rack = fields.Float(related="location_id.total_rack")
    percentage_ocupado = fields.Float(related="location_id.percentage_ocupado")
    qty_rack_free = fields.Float(related="location_id.qty_rack_free")

    @api.constrains('name', 'location_id')
    def _constrains_quantity_loc(self):
        for rec in self:
            if rec.location_id and rec.location_id.usage == 'internal':
                rec.location_id._compute_quantity_rack()





