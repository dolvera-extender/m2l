# -*- coding: utf-8 -*-
# Ing. Isaac Chavez Arroyo: www.isaaccv.ml
{
    "name": "Sale MPS",
    'version': '0.01b',
    'summary': 'Sale Manual package selection',
    'description': "Selección manual de paquetes en el pedido de venta.",
    'author': 'Ing. Isaac Chávez Arroyo',
    'website': 'https://isaaccv.ml',
    "depends": ["base", "sale", "sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale.xml"
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3'
}
