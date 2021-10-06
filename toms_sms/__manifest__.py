# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'SMS',
    'version': '1.1',
    'author': 'Humint (Pty) Ltd',
    'category': 'Tools',
    'sequence': 60,
    'summary': 'SMS',
    'description': "",
    'website': 'https://www.humint.co.za/',
    'depends': ['sms_frame', 'base_automation'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/test_mass_sms_view.xml',
        'views/sms_views.xml',
        'data/toms_sms_data.xml',
    ],
    'test': [
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}
