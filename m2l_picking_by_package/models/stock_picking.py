# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_picking_lines_by_package(self):
        """
        Devuelve las líneas de movimiento agrupadas por (paquete, producto),
        fusionando cantidades de líneas con misma combinación.

        Orden de salida: primero por nombre de producto, luego por nombre de paquete.

        Retorna una lista plana de dicts:
        [
            {
                'product_id': product.product,
                'quantity': float,
                'product_uom_id': uom.uom,
                'location_id': stock.location,
                'location_dest_id': stock.location,
                'lot_ids': stock.lot (recordset),
                'lot_names': list[str],
                'package': stock.quant.package | False,
            },
            ...
        ]
        """
        # (pkg_id, prod_id) -> datos acumulados
        grouped = {}
        # pkg_id -> registro de paquete (o False)
        packages_map = {}

        for ml in self.move_line_ids_without_package:
            pkg = ml.result_package_id or ml.package_id
            pkg_id = pkg.id if pkg else 0
            prod_id = ml.product_id.id

            if pkg_id not in packages_map:
                packages_map[pkg_id] = pkg if pkg else False

            key = (pkg_id, prod_id)
            if key not in grouped:
                grouped[key] = {
                    'product_id': ml.product_id,
                    'quantity': 0.0,
                    'product_uom_id': ml.product_uom_id,
                    'location_id': ml.location_id,
                    'location_dest_id': ml.location_dest_id,
                    'lot_ids': self.env['stock.lot'].browse(),
                    'lot_names': [],
                    'package': pkg if pkg else False,
                }

            grouped[key]['quantity'] += ml.quantity

            if ml.lot_id and ml.lot_id not in grouped[key]['lot_ids']:
                grouped[key]['lot_ids'] |= ml.lot_id
            if ml.lot_name and ml.lot_name not in grouped[key]['lot_names']:
                grouped[key]['lot_names'].append(ml.lot_name)

        # Ordenar: primero por nombre de producto, luego por nombre de paquete
        return sorted(
            grouped.values(),
            key=lambda d: (
                (d['product_id'].display_name or '').lower(),
                (d['package'].name if d['package'] else '').lower(),
            ),
        )
