# -*- coding: utf-8 -*-
{
    'name': 'Inventory user reports',
    'version': '0.1b',
    'summary': 'Reportes de movimientos de inventario y productos',
    "author": "Ing. Isaac Chávez Arroyo",
    'description': "",
    'website': 'https://isaaccv.ml',
    'depends': ['base', 'stock'],
    'category': 'Inventory/Inventory',
    'sequence': 88,
    'data': [
        'security/groups.xml',
        'views/views.xml',
        'views/views_partner.xml',
        'views/actions.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_qweb': [
        ],
        'web.assets_backend': [
        ]
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
