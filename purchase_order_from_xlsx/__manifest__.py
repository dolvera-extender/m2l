# -*- coding: utf-8 -*-
{
    'name': 'Crear compra desde excel',
    'version': '17.0.0.1',
    'category': 'sale',
    'author': 'Ing. Alejandro Garcia Magaña',
    'website': '',
    'license': 'LGPL-3',
    'summary': 'Crear compra desde excel',

    'depends': [
        'purchase',
        'purchase_stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/purchase_order_security.xml',
        'wizard/purchase_xlsx_wizard_views.xml',
    ],
    'assets': {

    },
    'demo': [],
    'external_dependencies': {
    },
    'support': '',
    'application': False,
    'installable': True,
    'auto_install': False,
}

