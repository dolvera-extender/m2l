# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
{
    "name": "Sale MPS",
    'version': '17.0.0.1',
    'summary': 'Sale Manual package selection',
    'description': "Selección manual de paquetes en el pedido de venta.",
    'author': 'Ing. Isaac Chávez Arroyo',
    'website': 'https://isaaccv.ml',
    "depends": ["base", "sale", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale.xml",
        "views/picking.xml"
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3'
}
