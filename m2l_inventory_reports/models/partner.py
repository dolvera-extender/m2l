# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
_log = logging.getLogger("\n =====[%s]===" % __name__)


class ResPartnerM2l(models.Model):
    _inherit = "res.partner"

    product_category_ids = fields.Many2many('product.category', string="Categorías de producto permitidas", help="Categorias de producto que el usuario puede visualizar en el reporte M2L")
    is_carrier = fields.Boolean(string="Es transportista")


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
        us_cat = self.env.user.partner_id.product_category_ids
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

    def m2l_filter_stock_move_line(self):
        form_view = self.env.ref('m2l_inventory_reports.stock_move_line_m2l_form_view', False)
        kanban_view = self.env.ref('m2l_inventory_reports.stock_move_line_m2l_kanban_view', False)
        tree_view = self.env.ref('m2l_inventory_reports.stock_move_line_m2l_tree_view', False)

        us_cat = self.env.user.partner_id.product_category_ids
        child_categs = self.get_child_product_categories(us_cat) if us_cat else False

        if us_cat:
            if child_categs:
                ac_ids = (us_cat + child_categs).ids
            else:
                ac_ids = us_cat.ids
        else:
            ac_ids = []
        return {
            'name': "Movimientos",
            'view_mode': 'tree,kanban,form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'target': "current",
            'domain': [('product_id.categ_id', 'in', ac_ids)],
            'views': [[tree_view.id, "tree"], [kanban_view.id, "kanban"], [form_view.id, "form"]],
            # 'context': {}
        }