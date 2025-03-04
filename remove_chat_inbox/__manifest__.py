# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Hide Inbox Chat",
    'license': 'AGPL-3',
    'summary': """Hide Chatter & Inbox
Hide Discussion Menu and chatter from Odoo Tray""",
    'description': """
        Hide Chatter & Inbox
        Hide Discussion Menu and chatter from Odoo Tray
        
    """,
    'version': "17.0.0.1",
    'author': "David Montero Crespo",
    'support': 'softwareescarlata@gmail.com',
    'images': ['static/description/img.png'],
    'category' : 'tools',
    'depends': ['base','mail'],
    'data':[

    ],
    'assets': {
        'web.assets_backend': [
            'remove_chat_inbox/static/src/xml/*.xml',
        ],
    },
    'installable' : True,
    'application' : False,
    'auto_install' : False,

}
