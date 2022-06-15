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

    def mps_select(self):
        self.sale_id_se = self.sale_id_av.id
        self.sale_id_av = False
        self.update_qty_selected()

    def mps_unselect(self):
        self.sale_id_av = self.sale_id_se.id
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
            picking.sale_order_id = sale_id.id
            _log.info("SALE ORDER ::: %s" % sale_id)
            # wh_stock_id = sale_id.warehouse_id.lot_stock_id
            # # Segúnda parte: agregar una condición para la selección manual o no.
            # if wh_stock_id.id != picking.location_id.id:
            #     return picking
            # # Then create move_line_ids_without_package
            # for pack in sale_id.manual_package_ids.filtered(lambda x: x.selected == True):
            #     lot_id = pack.package_id.quant_ids.mapped('lot_id')[0]
            #     qty = sum(pack.package_id.quant_ids.filtered(lambda x: x.product_id.id == pack.product_id.id).mapped('quantity'))
            #     ml_data = {
            #         'product_id': pack.product_id.id,
            #         'package_id': pack.package_id.id,
            #         'result_package_id': pack.package_id.id,
            #         'lot_id': lot_id.id,
            #         'product_uom_qty': qty,
            #         'location_id': picking.location_id.id,
            #         'location_dest_id': picking.location_dest_id.id,
            #         'product_uom_id': lot_id.product_uom_id.id
            #     }
            #     mlids.append((0, 0, ml_data))
            #
            # picking.move_line_ids_without_package = mlids
            # # clean context
            # context = dict(self._context)
            # context.pop('mps_sale_id')
            # self = self.with_context(context)

        return picking

    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done')).sorted(
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


class StockMoveMPs(models.Model):
    _inherit = "stock.move"


def _action_assign(self):
    """ Reserve stock moves by creating their stock move lines. A stock move is
    considered reserved once the sum of `product_qty` for all its move lines is
    equal to its `product_qty`. If it is less, the stock move is considered
    partially available.
    """

    def _get_available_move_lines(move):
        move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
        keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

        def _keys_in_sorted(ml):
            return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

        grouped_move_lines_in = {}
        for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
            qty_done = 0
            for ml in g:
                qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            grouped_move_lines_in[k] = qty_done
        move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move) \
            .filtered(lambda m: m.state in ['done']) \
            .mapped('move_line_ids')
        # As we defer the write on the stock.move's state at the end of the loop, there
        # could be moves to consider in what our siblings already took.
        moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
        moves_out_siblings_to_consider = moves_out_siblings & (
                    StockMove.browse(assigned_moves_ids) + StockMove.browse(partially_available_moves_ids))
        reserved_moves_out_siblings = moves_out_siblings.filtered(
            lambda m: m.state in ['partially_available', 'assigned'])
        move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
        keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

        def _keys_out_sorted(ml):
            return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

        grouped_move_lines_out = {}
        for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
            qty_done = 0
            for ml in g:
                qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            grouped_move_lines_out[k] = qty_done
        for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
            grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
        available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in
                                grouped_move_lines_in}
        # pop key if the quantity available amount to 0
        rounding = move.product_id.uom_id.rounding
        return dict(
            (k, v) for k, v in available_move_lines.items() if float_compare(v, 0, precision_rounding=rounding) > 0)

    StockMove = self.env['stock.move']
    assigned_moves_ids = OrderedSet()
    partially_available_moves_ids = OrderedSet()
    # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
    # cache invalidation when actually reserving the move.
    reserved_availability = {move: move.reserved_availability for move in self}
    roundings = {move: move.product_id.uom_id.rounding for move in self}
    move_line_vals_list = []
    for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
        rounding = roundings[move]
        missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
        missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity,
                                                                       move.product_id.uom_id,
                                                                       rounding_method='HALF-UP')
        if move._should_bypass_reservation():
            # create the move line(s) but do not impact quants
            if move.move_orig_ids:
                available_move_lines = _get_available_move_lines(move)
                _log.info("\n AV MOVE LINES ::: %s " % available_move_lines)
                for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                    qty_added = min(missing_reserved_quantity, quantity)
                    move_line_vals = move._prepare_move_line_vals(qty_added)
                    move_line_vals.update({
                        'location_id': location_id.id,
                        'lot_id': lot_id.id,
                        'lot_name': lot_id.name,
                        'owner_id': owner_id.id,
                    })
                    move_line_vals_list.append(move_line_vals)
                    missing_reserved_quantity -= qty_added
                    if float_is_zero(missing_reserved_quantity, precision_rounding=move.product_id.uom_id.rounding):
                        break

            if missing_reserved_quantity and move.product_id.tracking == 'serial' and (
                    move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                for i in range(0, int(missing_reserved_quantity)):
                    move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
            elif missing_reserved_quantity:
                to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                                   ml.location_id == move.location_id and
                                                                   ml.location_dest_id == move.location_dest_id and
                                                                   ml.picking_id == move.picking_id and
                                                                   not ml.lot_id and
                                                                   not ml.package_id and
                                                                   not ml.owner_id)
                if to_update:
                    to_update[0].product_uom_qty += move.product_id.uom_id._compute_quantity(
                        missing_reserved_quantity, move.product_uom, rounding_method='HALF-UP')
                else:
                    move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
            assigned_moves_ids.add(move.id)
        else:
            if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                assigned_moves_ids.add(move.id)
            elif not move.move_orig_ids:
                if move.procure_method == 'make_to_order':
                    continue
                # If we don't need any quantity, consider the move assigned.
                need = missing_reserved_quantity
                if float_is_zero(need, precision_rounding=rounding):
                    assigned_moves_ids.add(move.id)
                    continue
                # Reserve new quants and create move lines accordingly.
                forced_package_id = move.package_level_id.package_id or None
                available_quantity = move._get_available_quantity(move.location_id, package_id=forced_package_id)
                if available_quantity <= 0:
                    continue
                taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id,
                                                                package_id=forced_package_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=rounding):
                    continue
                if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                    assigned_moves_ids.add(move.id)
                else:
                    partially_available_moves_ids.add(move.id)
            else:
                # Check what our parents brought and what our siblings took in order to
                # determine what we can distribute.
                # `qty_done` is in `ml.product_uom_id` and, as we will later increase
                # the reserved quantity on the quants, convert it here in
                # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                available_move_lines = _get_available_move_lines(move)
                if not available_move_lines:
                    continue
                for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                    if available_move_lines.get(
                            (move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
                        available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id,
                                              move_line.owner_id)] -= move_line.product_qty
                for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                    need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                    # `quantity` is what is brought by chained done move lines. We double check
                    # here this quantity is available on the quants themselves. If not, this
                    # could be the result of an inventory adjustment that removed totally of
                    # partially `quantity`. When this happens, we chose to reserve the maximum
                    # still available. This situation could not happen on MTS move, because in
                    # this case `quantity` is directly the quantity on the quants themselves.
                    available_quantity = move._get_available_quantity(location_id, lot_id=lot_id, package_id=package_id,
                                                                      owner_id=owner_id, strict=True)
                    if float_is_zero(available_quantity, precision_rounding=rounding):
                        continue
                    taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity),
                                                                    location_id, lot_id, package_id, owner_id)
                    if float_is_zero(taken_quantity, precision_rounding=rounding):
                        continue
                    if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                        assigned_moves_ids.add(move.id)
                        break
                    partially_available_moves_ids.add(move.id)
        if move.product_id.tracking == 'serial':
            move.next_serial_count = move.product_uom_qty

    _log.info("\n AV MOVE LINES  LIST ::: %s " % move_line_vals_list)
    self.env['stock.move.line'].create(move_line_vals_list)
    StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
    StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
    if self.env.context.get('bypass_entire_pack'):
        return
    self.mapped('picking_id')._check_entire_pack()