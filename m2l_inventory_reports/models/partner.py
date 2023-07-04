# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartnerM2l(models.Model):
    _inherit = "res.partner"

    product_category_ids = fields.Many2many('product.category', string="Categorías permitidas")