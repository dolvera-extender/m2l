# -*- coding: utf-8 -*-

from odoo import models, fields, api
import math
import logging
_log = logging.getLogger("___name: %s" % __name__)

class SplitPacketWizard(models.TransientModel):
    _name = "split.packet.wizard"
    _description = "Wizard para la divisiòn de paquetes"

    """
    Divisor de paquetes:  
        - puede indicarse la cantidad por paquete
        - o la cantidad de paquetes 
        - el remanente se queda siempre en el paquete original

        Si requieren dividir todo el contenido y queda un remanente, se creará un último paquete con el sobrante.

        Cuando el paquete tenga diferentes lineas, puede o no existir coincidencia en los últimos, dependiendo de las cantidades de producto
        que tenga cada uno y lo que se vaya a transferir. 

    PAQUETES EJEMPLOS: CNT-22-215-0122V
    """
    package_id = fields.Many2one('stock.quant.package', string="Paquete", domain="[('location_id.usage', 'in', ['internal'])]")

    split_indicator = fields.Selection([
        ('qty_product', 'Cantidad de producto'),
        ('qty_packs', "Cantidad de paquetes")
        ], string="Mètodo de divisiòn")
    line_ids = fields.One2many('split.packet.wizard.line', 'split_packet_id', string="Lineas de paquete")

    def process_split_packet(self):
        sq_lines = self.line_ids.filtered(lambda l: l.split and l.product_split_qty > 0)
        if not sq_lines:
            return
        quants = self.env['stock.quant'].browse(sq_lines.mapped('quant_id_int'))
        start_index = self.package_id.current_split_squence
        for sq in sq_lines:
            _log.info(" PRODUCTO  :: %s " % sq.product_id.name)
            quant = quants.filtered(lambda q: q.id == sq.quant_id_int)
            # Todas las lineas se van a paquetes diferentes. 
            # Cuantos paquetes se harán ? 
            dest_packet_qry = self.package_id.current_split_squence # Ultimo index utilizado (mantiene la secuencia en los paquetes hijos)

            ## Necesitamos saber cuantos paquetes y de a cuanto producto por paquete. 
            if self.split_indicator == "qty_product":
                # cantidad de producto
                pack_qty = math.ceil(sq.product_split_qty/sq.product_packet_qty)
                product_qty = sq.product_packet_qty
            elif self.split_indicator == "qty_packs":
                # Cantidad de paquetes 
                pack_qty = sq.packet_qty
                product_qty = sq.product_split_qty/pack_qty
            
            # Realizamos un paquete nuevo 
            _log.info(" # PAQUETES %s  PRODUCT QTY:: %s " % (pack_qty, product_qty))

            qty_inpack = 0
            for n in range(0, int(pack_qty)):
                
                qty_inpack = qty_inpack + product_qty
                if qty_inpack > sq.product_split_qty:
                    # Aquí ya se pasó de la cantidad de producto. 
                    over_qty = qty_inpack - sq.product_split_qty
                    product_qty = product_qty - over_qty

                new_pack_data = {
                    'name': "%s-%s" % (self.package_id.name, start_index),
                    'location_id': self.package_id.location_id.id,
                    'quant_ids': [(0, 0, {
                        'product_id': quant.product_id.id,
                        'lot_id': quant.lot_id.id,
                        'quantity': product_qty,
                        'product_uom_id': quant.product_uom_id.id,
                        'location_id': quant.location_id.id
                    })]
                }

                # Creamos el paquete 
                new_pack = self.env['stock.quant.package'].create(new_pack_data)
                _log.info(" NUEVO PAQUETE :: %s " % new_pack)

                # ajustamos el quant del original
                quant.quantity = quant.quantity - product_qty

                # ajustamos el index en el paquete original. 
                start_index = start_index + 1
                self.package_id.current_split_squence = self.package_id.current_split_squence + 1


    @api.onchange('package_id')
    def show_package_content(self):
        self.line_ids = [(5, 0, 0)]
        new_lines = []
        for pline in self.package_id.quant_ids: 
            new_lines.append((0, 0, {
                'quant_id_int': pline.id,
                'product_id': pline.product_id.id,
                'product_qty': pline.quantity,
                'product_split_qty': pline.quantity
            }))
        self.line_ids = new_lines


class SplitPacketWizard(models.TransientModel):
    _name = "split.packet.wizard.line"
    _description = "Wizard para la divisiòn de paquetes"
    """
        We can split a package by  number of son packs or quantities per packet. 
        by default quantity to split is all product line quantity. 
    """


    split_packet_id = fields.Many2one('split.packet.wizard', string="Division de paquete")
    quant_id_int = fields.Integer(string="Quant")
    
    product_id = fields.Many2one('product.product', string="Producto")
    product_qty = fields.Float(string="Cantidad en paquete")
    product_split_qty = fields.Integer(string="Cantidad de producto a dividir")
    product_packet_qty = fields.Integer(string="Cantidad por paquete")
    packet_qty = fields.Float(string="Cantidad de paquetes")
    split = fields.Boolean(string="Dividir", default=False)


    @api.onchange('product_split_qty')
    def check_max_qty(self):
        if self.product_split_qty > self.product_qty:
            self.product_split_qty = self.product_qty
    
    @api.onchange('packet_qty')
    def check_packet_qty(self):
        if self.product_split_qty != 0 and self.packet_qty != 0:
            self.packet_qty = self.down_nearest_multiple(self.product_split_qty, self.packet_qty)

    @api.model
    def down_nearest_multiple(self, product_qty, pack_qty):
        qty = pack_qty
        while qty>0:
            if product_qty%qty == 0:
                return qty
            else:
                qty = qty-1
        return 0