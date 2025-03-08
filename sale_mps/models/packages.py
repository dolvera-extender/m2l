# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from itertools import groupby
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet
import logging
_log = logging.getLogger("\n ===============[%s]===============" % __name__)


class SaleMps(models.Model):
    _name = "sale.mps"
    _description = "Movimiento manual de paquetes"
    # _order = "package_id asc"

    # selected = fields.Boolean(string="Selecto")
    sale_id_av = fields.Many2one('sale.order', string="Pedido de venta")
    sale_id_se = fields.Many2one('sale.order', string="Pedido de venta")
    package_id = fields.Many2one('stock.quant.package', string="Paquete")
    product_id = fields.Many2one('product.product', string="producto")
    product_qty = fields.Float(string="Cantidad disponible", compute="_compute_quantity_pack", store=False)

    # @api.onchange("selected")
    # def select_pack(self):
    #     # _log.info("\n\n SELECCIONANDO :::: %s con valor:: %s" % (self, self.selected))
    #     if self.selected:
    #         self.mps_select()
    #     else:
    #         self.mps_unselect()

    def mps_select(self):
        # _log.info("SELECTING...")
        self.sale_id_se = self.sale_id_av
        self.sale_id_av = False
        self.update_qty_selected()

    def mps_unselect(self):
        # _log.info("NOOO SELECTING...")
        self.sale_id_av = self.sale_id_se
        self.sale_id_se = False
        self.update_qty_selected()

    def update_qty_selected(self):
        so = self.sale_id_se if self.sale_id_se else self.sale_id_av
        ol = so.order_line.filtered(lambda x: x.product_id.id == self.product_id.id)
        quants_used = so.manual_package_selected_ids \
            .mapped('package_id') \
            .mapped('quant_ids') \
            .filtered(lambda x: x.product_id.id == self.product_id.id)
        quantity = sum(quants_used.mapped('quantity'))
        ol.product_uom_qty = quantity

    def _compute_quantity_pack(self):
        for rec in self:
            rec.product_qty = sum(rec.package_id.mapped('quant_ids').mapped('quantity'))


class StockPickingMps(models.Model):
    _inherit = "stock.picking"

    sale_order_id = fields.Many2one("sale.order", string="Venta")

    @api.model
    def create(self, vals):
        _log.info("\n CREATE CONTEXT::: %s " % self._context)
        _log.info("\nCREATE VALS::: %s " % vals)
        picking = super(StockPickingMps, self).create(vals)
        # Create move lines
        # mlids = []
        if 'mps_sale_id' in self._context:
            sale_id = self.env['sale.order'].browse(self._context.get('mps_sale_id'))
            if sale_id and sale_id.manual_package_selected_ids and len(sale_id.manual_package_selected_ids.ids) > 0:
                picking.sale_order_id = sale_id.id
                _log.info("SALE ORDER ::: %s" % sale_id)
        return picking

    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """

        self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.move_ids.filtered(lambda move: move.state not in ('draft', 'cancel', 'done')).sorted(
            key=lambda move: (-int(move.priority), not bool(move.date_deadline), move.date_deadline, move.date, move.id)
        )
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))

        # If a package level is done when confirmed its location can be different than where it will be reserved.
        # So we remove the move lines created when confirmed to set quantity done to the new reserved ones.
        package_level_done = self.mapped('package_level_ids').filtered(lambda pl: pl.is_done and pl.state == 'confirmed')
        package_level_done.write({'is_done': False})
        # if not self.sale_order_id:
        #     _log.info("SIN SALE")
        moves._action_assign()
        # else:
        #     _log.info("con sale")
        #     self.mps_manual_reserve()
        package_level_done.write({'is_done': True})

        return True

    def mps_manual_reserve(self):
        self.move_line_ids_without_package = False
        mlids = []
        for pack in self.sale_order_id.manual_package_selected_ids:
            lot_id = pack.package_id.quant_ids.mapped('lot_id')[0]
            qty = sum(pack.package_id.quant_ids.filtered(lambda x: x.product_id.id == pack.product_id.id).mapped('quantity'))
            ml_data = {
                'product_id': pack.product_id.id,
                'package_id': pack.package_id.id,
                'result_package_id': pack.package_id.id,
                'lot_id': lot_id.id,
                'product_uom_qty': qty,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'product_uom_id': lot_id.product_uom_id.id
            }
            mlids.append((0, 0, ml_data))
        _log.info("\n move lines ::: %s " % mlids)
        self.move_line_ids_without_package = mlids


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    #REMOVIDO


class StockMoveMPs(models.Model):
    _inherit = "stock.move"

    #REMOVIDO



class StockQuantMps(models.Model):
    _inherit = "stock.quant"

    # @api.model
    # def _get_removal_strategy(self, product_id, location_id):
    #     if product_id.categ_id.removal_strategy_id:
    #         return product_id.categ_id.removal_strategy_id.method
    #     loc = location_id
    #     while loc:
    #         if loc.removal_strategy_id:
    #             return loc.removal_strategy_id.method
    #         loc = loc.location_id
    #     return 'fifo'



    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, qty=0,package_ids=None):
        """ if records in self, the records are filtered based on the wanted characteristics passed to this function
            if not, a search is done with all the characteristics passed.
        """
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        domain = self._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)
        domain, order = self._get_removal_strategy_domain_order(domain, removal_strategy, qty)

        quants_cache = self.env.context.get('quants_cache')
        if quants_cache is not None and strict and removal_strategy != 'least_packages':
            res = self.env['stock.quant']
            if lot_id:
                res |= quants_cache[product_id.id, location_id.id, lot_id.id, package_id.id, owner_id.id]
            res |= quants_cache[product_id.id, location_id.id, False, package_id.id, owner_id.id]
        else:
            res = self.search(domain, order=order)
        if removal_strategy == "closest":
            res = res.sorted(lambda q: (q.location_id.complete_name, -q.id))

        if package_ids is None and self.env.context.get('mps_sale',False):
            mps_sale_id = self.env.context.get('mps_sale',False)
            package_ids = mps_sale_id.manual_package_selected_ids.package_id

        if package_ids is not None:
            _log.info("package_ids:: %s " % package_ids)
            res = res.filtered(lambda x: x.package_id.id in package_ids.ids)

        return res.sorted(lambda q: not q.lot_id)
