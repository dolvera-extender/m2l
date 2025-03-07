# -*- coding: utf-8 -*-
{
    "name": "Inventory Customs",
    'version': '17.0.0.1',
    'author': 'Ing. Isaac Chávez Arroyo',
    'website': 'https://isaaccv.ml',
    "depends": ["base", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking.xml",
        "wizard/split_packet.xml",
        "reports/count_sheet.xml"
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3'
}
