# -*- coding: utf-8 -*-
{
    'name': "Venta desde Excel con Paquetes",
    'version': '17.0.0.1',
    'category': 'sale',
    'author': 'Ing. Alejandro Garcia Magaña',
    'website': '',
    'license': 'LGPL-3',
    'summary': "Venta desde Excel con Paquetes",

    'depends': [
        'sale',
        'sale_mps',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_excel_import_views.xml'
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

