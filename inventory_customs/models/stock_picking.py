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

    def _action_assign(self, force_qty=False):
        #if not self.picking_type_id.use_multiplier:
        self = self.filtered(lambda sm: sm.picking_type_id and not sm.picking_type_id.use_multiplier)
        return super(MlStockMove,self)._action_assign(force_qty=force_qty)
        

   

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