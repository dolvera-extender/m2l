# -*- coding: utf-8 -*-

from cgitb import reset
from odoo import models, fields, api
import logging
_log = logging.getLogger("___name: %s" % __name__)
import re


class StockMoveGbp(models.Model):
    _inherit = "stock.move"

    def group_movelines_wop(self):
        list_packs = {}

        smlis = self.picking_id.move_line_ids_without_package.filtered(lambda x: x.product_id.id == self.product_id.id)
        # Group by result package
        for sml in smlis:
            if str(sml.result_package_id.id) in list_packs:
                # Actualizamos la cantidad total y la cantidad de paquetes en +1 
                lot_names_ori = list_packs[str(sml.result_package_id.id)]['lot_names'].split(", ")
                lot_names_ori.append(sml.lot_id.name)
                lot_names = ', '.join(lot_names_ori)
                new_data = {
                    'pqty': 1 + list_packs[str(sml.result_package_id.id)]['pqty'],
                    'pname': sml.result_package_id.name,
                    'product_qty': sml.qty_done + list_packs[str(sml.result_package_id.id)]['product_qty'],
                    'lot_names': lot_names
                }
                list_packs[str(sml.result_package_id.id)] = new_data
            else:
                # Si no está entonces agregamos el primero.
                lot_names = str(sml.lot_id.name)
                list_packs[str(sml.result_package_id.id)] = {
                    'pqty': 1,
                    'pname': sml.result_package_id.name,
                    'product_qty': sml.qty_done,
                    'lot_names': lot_names
                }
        return list_packs
