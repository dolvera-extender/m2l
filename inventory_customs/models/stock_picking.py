# -*- coding: utf-8 -*-

from cgitb import reset
from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)


class StockPickingCustom(models.Model):
    _inherit = "stock.picking"

    use_multiplier = fields.Boolean(string="Usar multiplicador", compute="_check_use_multiplier", store=False)
    product_to_multiply = fields.Many2one('product.product', string="Producto a multiplicar")
    product_tm_domain = fields.One2many('product.product', 'product_multiplier_domain',
                                        string="Product tm domain", compute="_get_product_mult_domain", store=False)
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
        move_id_multiply = self.move_ids_without_package.filtered(lambda li: li.product_id.id == self.product_to_multiply.id)

        for line in move_id_multiply.move_line_nosuggest_ids:
            _log.info("\n\nqty_done:: %s \n\nproduct_uom_qty:: %s \n\nstate:: %s \n\npicking_code:: %s " % (line.qty_done, line.product_uom_qty, line.state, line.picking_code))
        
        qty_for_done = move_id_multiply.product_uom_qty - move_id_multiply.quantity_done
        if qty_for_done <= 0:
            return
        qty_iterations = int(qty_for_done/self.product_qty_pack)
        qty_residual = qty_for_done%self.product_qty_pack
        moves_for_add = []
        iteracion = 0

        # Prepare secuences.

        julian_today = fields.Datetime.now().strftime("%j")
        _log.info("\nDIA JULIANO ::: %s " % julian_today)
        # Search the last seq 
        last_move = self.env['stock.move.line'].search([('julian_day','=', int(julian_today))], order='julian_day_seq asc')[-1:]
        if not last_move:
            st_seq = 0
        else:
            st_seq = last_move.julian_day_seq

        while True:

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
            package_id = self.env['stock.quant.package'].create({
                'name': "CNT-%s-%s" % (julian_today, st_seq)
            })
            new_pack = {
                'picking_id': self.id,
                'package_level_id': False,
                'package_id': False, 
                'location_dest_id': self.location_dest_id.id,
                'lot_name': "%s-%s" % (julian_today, st_seq),
                'result_package_id': package_id.id,
                'qty_done': qty_done,
                'company_id': self.company_id.id,
                'product_id': move_id_multiply.product_id.id,
                'product_uom_id': move_id_multiply.product_uom.id,
                'location_id': self.location_id.id,
                'julian_day': int(julian_today),
                'julian_day_seq': st_seq

            }
            moves_for_add.append((0, 0, new_pack))

            # Decrease counters
            if qty_iterations > 0:
                qty_iterations -= 1
            elif qty_iterations == 0 and qty_residual >0:
                qty_residual = 0
        _log.info("\nDatos a agregar::: %s ")
        move_id_multiply.move_line_nosuggest_ids = moves_for_add
        self.product_to_multiply = False
        self.product_qty_pack = 0

        
        
    # @api.onchange('product_to_multiply')
    # def default_product_av_qty(self):
    #     pass

    def _get_product_mult_domain(self):
        move_product_ids = self.move_ids_without_package.mapped('product_id').ids
        if len(move_product_ids) > 0:
            self.write({
                'product_tm_domain': [(6, 0, move_product_ids)]
            })


class StockPickingTypeCustom(models.Model):
    _inherit = "stock.picking.type"

    use_multiplier = fields.Boolean(string="Usa multiplicador", default=False)


class ProductProductMultiply(models.Model):
    _inherit = "product.product"

    product_multiplier_domain = fields.Many2one('stock.picking', 'Movimiento multiplicado')


class StockMoveLineCu(models.Model):
    _inherit = "stock.move.line"

    julian_day = fields.Integer(string="Dia juliano")
    julian_day_seq = fields.Integer(string="Secuencia del día")

#     @api.model_create_multi
#     def create(self, vals_list):
#         _log.info(" CREANDO NUEVA LINEA CON LOS VALORES:::  %s " % vals_list)
#         result = super(StockMoveLineCu, self).create(vals_list)
#         return result