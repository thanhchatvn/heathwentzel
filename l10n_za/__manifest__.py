# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2018 Mahmoud Abdel Latif (<http://mah007.com>) 01002688172

{
    'name': 'RSA - Accounting',
    'version': '11.8',
    'author': 'Strategic Dimensions',
    'website': 'http://www.strategicdimensions.co.za',
    'category': 'Localization',
    'license': 'AGPL-3',
    'description': """
South Africa accounting chart and localization.
=======================================================

    """,
    'depends': ['base', 'account'],
    'data': [
             'data/l10n_za_chart_data.xml',
             'data/account_tax.xml',
             'data/account_chart_template_configure_data.xml'
             ],
}
