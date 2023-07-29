# -*- coding: utf-8 -*-
{
    'name': 'Inventory user reports',
    'version': '0.1b',
    'summary': 'Reportes de movimientos de inventario y productos',
    "author": "Ing. Isaac Chávez Arroyo",
    'description': "",
    'website': 'https://isaaccv.ml',
    'depends': ['base', 'stock', "l10n_mx_edi_stock"],
    'category': 'Inventory/Inventory',
    'sequence': 88,
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/views_partner.xml',
        'views/actions.xml',
        'views/menus.xml',
        'wizard/pcover_ref_wizard.xml',
        'views/reports.xml'
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
