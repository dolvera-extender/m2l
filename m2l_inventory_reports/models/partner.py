# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class ResPartnerM2l(models.Model):
    _inherit = "res.partner"

    product_category_ids = fields.Many2many('product.category', string="Categorías permitidas")


class M2lFilterRecords(models.TransientModel):
    _name = "m2l.filter.records"
    _description = "Record filter model"

    def get_child_product_categories(self, categories):
        child_categories = categories.mapped('child_id')
        if not child_categories:
            return False
        gc_categories = self.get_child_product_categories(child_categories)
        if gc_categories:
            child_categories += gc_categories
        return child_categories

    def m2l_filter_products(self):
        tree_view = self.env.ref('m2l_inventory_reports.product_product_m2l_report_tree_view', False)
        _log.info("vISTA ENCONTRADA ::: %s " % tree_view)
        us_cat = self.env.user.partner_id.product_category_ids
        _log.info("Categorias del usuario :: %s " % us_cat)
        child_categs = self.get_child_product_categories(us_cat) if us_cat else False

        if us_cat:
            if child_categs:
                ac_ids = (us_cat+child_categs).ids
            else:
                ac_ids = us_cat.ids
        else:
            ac_ids = []
        return {
            'name': "Productos",
            'view_mode': 'tree',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'target': "current",
            'domain': [('categ_id', 'in', ac_ids)],
            'views': [[tree_view.id, "tree"]],
            # 'context': {}
        }