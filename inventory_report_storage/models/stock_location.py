# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class StockLocationInherit(models.Model):
    _inherit = "stock.location"

    total_rack = fields.Float(string="Posiciones Rack")

    percentage_ocupado = fields.Float(string="Porcentage Ocupado", compute="_compute_quantity_rack", store=True)
    qty_rack_free = fields.Float(string="Cantidad libre Rack", compute="_compute_quantity_rack", store=True)

    @api.depends('location_id', 'total_rack')
    def _compute_quantity_rack(self):
        quants_package = self.env['stock.quant.package'].search([('location_id','in',self.ids),('location_id.usage','=','internal')])
        for rec in self:
            if rec.usage !='internal':
                rec.percentage_ocupado = 0
                rec.qty_rack_free = 0
                continue
            quants_loc = quants_package.filtered_domain([('location_id', '=', rec.id)])
            total_rack = rec.total_rack
            percentage_ocupado = 0
            qty_rack_free = 0
            quantity = len(quants_loc)
            qty_rack_free = total_rack - quantity
            if quantity and total_rack:
                percentage_ocupado = quantity / total_rack * 100


            rec.percentage_ocupado = percentage_ocupado
            rec.qty_rack_free = qty_rack_free