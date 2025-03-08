# -*- coding: utf-8 -*-
{
    'name': 'Inventory package count',
    'version': '17.0.0.1',
    'summary': 'Conteo y revision de paquetes en una ubicación',
    "author": "Ing. Isaac Chávez Arroyo",
    'description': "",
    'website': 'https://isaaccv.ml',
    'depends': ['barcodes_gs1_nomenclature', 'stock', 'web_tour', 'web_mobile','stock_barcode'],
    'category': 'Inventory/Inventory',
    'sequence': 98,
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/audit_packages_wizard.xml',
        'views/views.xml',
        'views/actions.xml',
        'views/menu.xml',
        'views/report.xml'
        
    ],
    'assets': {
        'web.assets_backend': [
            'inventory_audit/static/src/*.js',
            #'inventory_audit/static/src/legacy/*.js',
            'inventory_audit/static/src/*.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}
