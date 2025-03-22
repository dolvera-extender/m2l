# -*- coding: utf-8 -*-

from cgitb import reset
from odoo import models, fields, api
import time
import pytz
from datetime import timedelta
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby
from collections import defaultdict



import logging
_log = logging.getLogger("___name: %s" % __name__)


class StockPickingCustom(models.Model):
    _inherit = "stock.picking"

    use_multiplier = fields.Boolean(string="Usar divisor", compute="_check_use_multiplier", store=False)
    product_to_multiply = fields.Many2one('product.product', string="Producto a dividir")
    product_tm_domain = fields.One2many('product.product', 'product_multiplier_domain',
                                        string="Product tm domain", compute='_get_product_mult_domain', store=False)
    product_qty_pack = fields.Integer(string="Cantidad por paquete")

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
        if self.product_qty_pack <= 0:
            return
        move_id_multiply = self.move_ids_without_package.filtered(lambda li: li.product_id.id == self.product_to_multiply.id)
        move_id_multiply = move_id_multiply[0] if len(move_id_multiply)>1 else move_id_multiply
        qty_for_done = move_id_multiply.product_uom_qty - move_id_multiply.quantity # antes quantity_done
        if qty_for_done <= 0:
            return
        qty_iterations = int(qty_for_done/self.product_qty_pack)
        qty_residual = qty_for_done%self.product_qty_pack
        moves_for_add = []
        iteracion = 0

        # Prepare secuences.
        julian_today = fields.Datetime.now().strftime("%j")
        # Search the last seq 
        last_move = self.env['stock.move.line'].search([('julian_day','=', int(julian_today))], order='julian_day_seq asc')[-1:]
        if not last_move:
            st_seq = 0
        else:
            st_seq = last_move.julian_day_seq

        str_div = "/%s/" % self.picking_type_id.sequence_code
        picking_seq = self.name.split(str_div)[1]
        packages_list = [] # To invert the create order.
        while True:
            mln_data = {}
            # Set counters and finish case. 
            iteracion += 1
            if qty_iterations > 0:
                qty_done = self.product_qty_pack
            elif qty_iterations == 0 and qty_residual > 0:
                qty_done = qty_residual
            else:
                break
            st_seq += 1
 
            # Making new records
            mln_data['pack_name'] = "CNT-%s-%s-%s" % (fields.Datetime.now().strftime("%y"), julian_today, str(st_seq).zfill(4))
            # package_id = self.env['stock.quant.package'].create(pack_data)
            # Create line data without pack.
            line_data = {
                'picking_id': self.id,
                'package_level_id': False,
                'package_id': False, 
                'location_dest_id': self.location_dest_id.id,
                'lot_name': "%s-%s-%s" % (fields.Datetime.now().strftime("%y"), julian_today, picking_seq),
                # 'result_package_id': package_id.id,
                # 'qty_done': qty_done,
                'quantity': qty_done,
                'company_id': self.company_id.id,
                'product_id': move_id_multiply.product_id.id,
                'product_uom_id': move_id_multiply.product_uom.id,
                'location_id': self.location_id.id,
                'julian_day': int(julian_today),
                'julian_day_seq': st_seq
            }
            mln_data['line_data'] = line_data
            # moves_for_add.append((0, 0, line_data))
            # Decrease counters
            if qty_iterations > 0:
                qty_iterations -= 1
            elif qty_iterations == 0 and qty_residual > 0:
                qty_residual = 0
            # time.sleep(2)
            packages_list.append(mln_data)

        # Inverse creation order
        # packages_list.reverse()
        for pak in packages_list:
            package_id = self.env['stock.quant.package'].create({'name': pak['pack_name']})
            line_data = pak['line_data']
            line_data['result_package_id'] = package_id.id
            moves_for_add.append((0, 0, line_data))
        moves_for_add.reverse()
        # move_id_multiply.move_line_nosuggest_ids = moves_for_add
        move_id_multiply.move_line_ids = moves_for_add
        self.product_to_multiply = False
        self.product_qty_pack = 0

    def _get_product_mult_domain(self):
        # move_product_ids = self.move_ids_without_package.filtered(lambda x: x.product_uom_qty-x.quantity_done > 0).mapped('product_id').ids
        move_product_ids = self.move_ids_without_package.filtered(lambda x: x.product_uom_qty-x.quantity > 0).mapped('product_id').ids
        if len(move_product_ids) > 0:
            self.product_tm_domain = [(6, 0, move_product_ids)]
        else:
            self.product_tm_domain = False


class StockPickingTypeCustom(models.Model):
    _inherit = "stock.picking.type"

    use_multiplier = fields.Boolean(string="Usa divisor", default=False)


class ProductProductMultiply(models.Model):
    _inherit = "product.product"

    product_multiplier_domain = fields.Many2one('stock.picking', 'Movimiento dividido')


class StockMoveLineCu(models.Model):
    _inherit = "stock.move.line"

    julian_day = fields.Integer(string="Dia juliano")
    julian_day_seq = fields.Integer(string="Secuencia del día")

class MlStockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        # Use OrderedSet of id (instead of recordset + |= ) for performance
        move_create_proc, move_to_confirm, move_waiting = OrderedSet(), OrderedSet(), OrderedSet()
        to_assign = defaultdict(OrderedSet)
        for move in self:
            if move.state != 'draft':
                continue
            # if the move is preceded, then it's waiting (if preceding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                move_waiting.add(move.id)
            else:
                if move.procure_method == 'make_to_order':
                    move_create_proc.add(move.id)
                else:
                    move_to_confirm.add(move.id)
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                to_assign[key].add(move.id)

        move_create_proc, move_to_confirm, move_waiting = self.browse(move_create_proc), self.browse(move_to_confirm), self.browse(move_waiting)

        # create procurements for make to order moves
        procurement_requests = []
        for move in move_create_proc:
            values = move._prepare_procurement_values()
            origin = move._prepare_procurement_origin()
            procurement_requests.append(self.env['procurement.group'].Procurement(
                move.product_id, move.product_uom_qty, move.product_uom,
                move.location_id, move.rule_id and move.rule_id.name or "/",
                origin, move.company_id, values))
        self.env['procurement.group'].run(procurement_requests, raise_user_error=not self.env.context.get('from_orderpoint'))

        move_to_confirm.write({'state': 'confirmed'})
        (move_waiting | move_create_proc).write({'state': 'waiting'})
        # procure_method sometimes changes with certain workflows so just in case, apply to all moves
        (move_to_confirm | move_waiting | move_create_proc).filtered(lambda m: m.picking_type_id.reservation_method == 'at_confirm')\
            .write({'reservation_date': fields.Date.today()})

        # assign picking in batch for all confirmed move that share the same details
        for moves_ids in to_assign.values():
            self.browse(moves_ids).with_context(clean_context(self.env.context))._assign_picking()
        new_push_moves = self._push_apply()
        self._check_company()
        moves = self
        if merge:
            moves = self._merge_moves(merge_into=merge_into)

        # Transform remaining move in return in case of negative initial demand
        neg_r_moves = moves.filtered(lambda move: float_compare(
            move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding) < 0)
        for move in neg_r_moves:
            move.location_id, move.location_dest_id = move.location_dest_id, move.location_id
            orig_move_ids, dest_move_ids = [], []
            for m in move.move_orig_ids | move.move_dest_ids:
                from_loc, to_loc = m.location_id, m.location_dest_id
                if float_compare(m.product_uom_qty, 0, precision_rounding=m.product_uom.rounding) < 0:
                    from_loc, to_loc = to_loc, from_loc
                if to_loc == move.location_id:
                    orig_move_ids += m.ids
                elif move.location_dest_id == from_loc:
                    dest_move_ids += m.ids
            move.move_orig_ids, move.move_dest_ids = [(6, 0, orig_move_ids)], [(6, 0, dest_move_ids)]
            move.product_uom_qty *= -1
            if move.picking_type_id.return_picking_type_id:
                move.picking_type_id = move.picking_type_id.return_picking_type_id
            # We are returning some products, we must take them in the source location
            move.procure_method = 'make_to_stock'
        neg_r_moves._assign_picking()

        # call `_action_assign` on every confirmed move which location_id bypasses the reservation + those expected to be auto-assigned
        # Si usa el multiplicador evitamos crear la reserva.
        _log.info(f" EVITA RESERVA ?? {self.picking_type_id.use_multiplier}")
        if not self.picking_type_id.use_multiplier:
            moves.filtered(lambda move: move.state in ('confirmed', 'partially_available')
                        and (move._should_bypass_reservation()
                                or move.picking_type_id.reservation_method == 'at_confirm'
                                or (move.reservation_date and move.reservation_date <= fields.Date.today())))\
                ._action_assign()
        if new_push_moves:
            neg_push_moves = new_push_moves.filtered(lambda sm: float_compare(sm.product_uom_qty, 0, precision_rounding=sm.product_uom.rounding) < 0)
            (new_push_moves - neg_push_moves).sudo()._action_confirm()
            # Negative moves do not have any picking, so we should try to merge it with their siblings
            neg_push_moves._action_confirm(merge_into=neg_push_moves.move_orig_ids.move_dest_ids)

        return moves


class StockQuantPackageM2l(models.Model):
    _inherit = "stock.quant.package"

    current_split_squence = fields.Integer(string="Ultimo split index", default=1)
    

class StockQuantM2l(models.Model):
    _inherit = "stock.quant"

    @api.model
    def get_report_date(self):
        user_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        printdate = fields.Datetime.now()
        printdate = pytz.utc.localize(printdate).astimezone(user_tz)
        return printdate.strftime('%d/%m/%Y %I:%M %p')