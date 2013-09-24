# -*- encoding: utf-8 -*-

{
    'name': 'OpenERP DNS',
    'version': '0.2',
    'category': 'Network/DNS',
    'description': """
        DNS
    """,
    'author': 'mrshelly',
    'website': 'https://github.com/mrshelly/openerp-dns',
    'depends': ['base'],
    'init_xml': [
    ],
    'update_xml': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'view/res_view.xml',
        'res_data.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
