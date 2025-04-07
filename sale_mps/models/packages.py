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
import logging

from collections import defaultdict

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

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


    def _update_reserved_quantity(self, need, location_id, quant_ids=None, lot_id=None, package_id=None, owner_id=None,
                                  strict=True):
        """ Create or update move lines and reserves quantity from quants
            Expects the need (qty to reserve) and location_id to reserve from.
            `quant_ids` can be passed as an optimization since no search on the database
            is performed and reservation is done on the passed quants set
        """
        self.ensure_one()
        if quant_ids is None:
            quant_ids = self.env['stock.quant']
        if not lot_id:
            lot_id = self.env['stock.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        if self.picking_id.sale_id and self.picking_id.sale_id.manual_package_selected_ids:
            packs = self.picking_id.sale_id.manual_package_selected_ids.mapped('package_id')
            quants = quant_ids._get_reserve_quantity(
                self.product_id, location_id, need, product_packaging_id=self.product_packaging_id,
                uom_id=self.product_uom, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict,package_ids=packs)

        else:
            quants = quant_ids._get_reserve_quantity(
                self.product_id, location_id, need, product_packaging_id=self.product_packaging_id,
                uom_id=self.product_uom, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)

        taken_quantity = 0
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # Find a candidate move line to update or create a new one.
        candidate_lines = {}
        for line in self.move_line_ids:
            if line.result_package_id or line.product_id.tracking == 'serial':
                continue
            candidate_lines[(line.location_id, line.lot_id, line.package_id, line.owner_id)] = line
        move_line_vals = []
        grouped_quants = {}
        # Handle quants duplication
        for quant, quantity in quants:
            if (quant.location_id, quant.lot_id, quant.package_id, quant.owner_id) not in grouped_quants:
                grouped_quants[quant.location_id, quant.lot_id, quant.package_id, quant.owner_id] = [quant, quantity]
            else:
                grouped_quants[quant.location_id, quant.lot_id, quant.package_id, quant.owner_id][1] += quantity
        for reserved_quant, quantity in grouped_quants.values():
            taken_quantity += quantity
            to_update = candidate_lines.get(
                (reserved_quant.location_id, reserved_quant.lot_id, reserved_quant.package_id, reserved_quant.owner_id))
            if to_update:
                uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id,
                                                                        rounding_method='HALF-UP')
                uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity,
                                                                                              self.product_id.uom_id,
                                                                                              rounding_method='HALF-UP')
            if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                to_update.quantity += uom_quantity
            else:
                if self.product_id.tracking == 'serial':
                    vals_list = self._add_serial_move_line_to_vals_list(reserved_quant, quantity)
                    if vals_list:
                        move_line_vals += vals_list
                else:
                    move_line_vals.append(
                        self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        if move_line_vals:
            self.env['stock.move.line'].create(move_line_vals)
        return taken_quantity


    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False,
                                allow_negative=False):
        self.ensure_one()
        if location_id.should_bypass_reservation():
            return self.product_qty

        # Revisar el campo: picking_type_entire_packs es un booleano para mover únicamente paquetes completos.
        if self.picking_id.sale_id and self.picking_id.sale_id.manual_package_selected_ids:
            _log.info("Si tiene sale order y el sale order tiene lineas. ")
            package_ids = self.picking_id.sale_id.manual_package_selected_ids.mapped('package_id')
            return self.env['stock.quant']._get_available_quantity(self.product_id, location_id, lot_id=lot_id,
                                                                   package_id=package_id, owner_id=owner_id,
                                                                   strict=strict, allow_negative=allow_negative,
                                                                   package_ids=package_ids)
        return self.env['stock.quant']._get_available_quantity(self.product_id, location_id, lot_id=lot_id,
                                                               package_id=package_id, owner_id=owner_id, strict=strict,
                                                               allow_negative=allow_negative)


class StockQuantMps(models.Model):
    _inherit = "stock.quant"

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False,qty=0,
                package_ids=None):
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

        if package_ids is None and self.env.context.get('mps_sale', False):
            mps_sale_id = self.env.context.get('mps_sale', False)
            package_ids = mps_sale_id.manual_package_selected_ids.package_id

        if package_ids is not None:
            _log.info("package_ids:: %s " % package_ids)
            res = res.filtered(lambda x: x.package_id.id in package_ids.ids)

        return res.sorted(lambda q: not q.lot_id)

    def _get_available_quantity(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None,
                                strict=False, allow_negative=False, package_ids=None):
        """ Return the available quantity, i.e. the sum of `quantity` minus the sum of
        `reserved_quantity`, for the set of quants sharing the combination of `product_id,
        location_id` if `strict` is set to False or sharing the *exact same characteristics*
        otherwise.
        The set of quants to filter from can be in `self`, if not a search will be done
        This method is called in the following usecases:
            - when a stock move checks its availability
            - when a stock move actually assign
            - when editing a move line, to check if the new value is forced or not
            - when validating a move line with some forced values and have to potentially unlink an
              equivalent move line in another picking
        In the two first usecases, `strict` should be set to `False`, as we don't know what exact
        quants we'll reserve, and the characteristics are meaningless in this context.
        In the last ones, `strict` should be set to `True`, as we work on a specific set of
        characteristics.

        :return: available quantity as a float
        """
        self = self.sudo()
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict, package_ids=package_ids)
        rounding = product_id.uom_id.rounding
        if product_id.tracking == 'none':
            available_quantity = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if allow_negative:
                return available_quantity
            else:
                return available_quantity if float_compare(available_quantity, 0.0,
                                                           precision_rounding=rounding) >= 0.0 else 0.0
        else:
            availaible_quantities = {lot_id: 0.0 for lot_id in list(set(quants.mapped('lot_id'))) + ['untracked']}
            for quant in quants:
                if not quant.lot_id and strict and lot_id:
                    continue
                if not quant.lot_id:
                    availaible_quantities['untracked'] += quant.quantity - quant.reserved_quantity
                else:
                    availaible_quantities[quant.lot_id] += quant.quantity - quant.reserved_quantity
            if allow_negative:
                return sum(availaible_quantities.values())
            else:
                return sum([available_quantity for available_quantity in availaible_quantities.values() if
                            float_compare(available_quantity, 0, precision_rounding=rounding) > 0])

    def _get_reserve_quantity(self, product_id, location_id, quantity, product_packaging_id=None, uom_id=None,
                              lot_id=None, package_id=None, owner_id=None, strict=False, package_ids=None):
        """ Get the quantity available to reserve for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. If no quants are in self, `_gather` will do a search to fetch the quants
        Typically, this method is called before the `stock.move.line` creation to know the reserved_qty that could be use.
        It's also called by `_update_reserve_quantity` to find the quant to reserve.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            could be done and how much the system is able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding

        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict, qty=quantity, package_ids=package_ids)

        # avoid quants with negative qty to not lower available_qty
        available_quantity = quants._get_available_quantity(product_id, location_id, lot_id, package_id, owner_id,
                                                            strict,package_ids=package_ids)

        # do full packaging reservation when it's needed
        if product_packaging_id and product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
            available_quantity = product_packaging_id._check_qty(available_quantity, product_id.uom_id, "DOWN")

        quantity = min(quantity, available_quantity)

        # `quantity` is in the quants unit of measure. There's a possibility that the move's
        # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
        # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
        # to convert `quantity` to the move's unit of measure with a down rounding method and
        # then get it back in the quants unit of measure with an half-up rounding_method. This
        # way, we'll never reserve more than allowed. We do not apply this logic if
        # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
        # will take care of changing the UOM to the UOM of the product.
        if not strict and uom_id and product_id.uom_id != uom_id:
            quantity_move_uom = product_id.uom_id._compute_quantity(quantity, uom_id, rounding_method='DOWN')
            quantity = uom_id._compute_quantity(quantity_move_uom, product_id.uom_id, rounding_method='HALF-UP')

        if quants.product_id.tracking == 'serial':
            if float_compare(quantity, int(quantity), precision_rounding=rounding) != 0:
                quantity = 0

        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(
                quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped(
                    'quantity')) - sum(quants.mapped('reserved_quantity'))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.',
                                  product_id.display_name))
        else:
            return reserved_quants

        negative_reserved_quantity = defaultdict(float)
        for quant in quants:
            if float_compare(quant.quantity - quant.reserved_quantity, 0, precision_rounding=rounding) < 0:
                negative_reserved_quantity[(quant.location_id, quant.lot_id, quant.package_id,
                                            quant.owner_id)] += quant.quantity - quant.reserved_quantity
        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                negative_quantity = negative_reserved_quantity[
                    (quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)]
                if negative_quantity:
                    negative_qty_to_remove = min(abs(negative_quantity), max_quantity_on_quant)
                    negative_reserved_quantity[
                        (quant.location_id, quant.lot_id, quant.package_id, quant.owner_id)] += negative_qty_to_remove
                    max_quantity_on_quant -= negative_qty_to_remove
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity,
                                                                                     precision_rounding=rounding):
                break
        return reserved_quants
