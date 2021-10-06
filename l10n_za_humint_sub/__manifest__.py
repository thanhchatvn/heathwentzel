# -*- encoding: utf-8 -*-

# Copyright (C) 2020 HuMint (Pty) Lts (<http://www.humint.co.za>).

{
    'name': 'Humint O - Localisation(Sub Module)',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This is the latest basic South African localisation necessary to run Odoo in ZA:
================================================================================
    - a generic chart of accounts
    - SARS VAT Ready Structure""",
    'author': 'Humint',
    'website': 'https://www.humint.co.za',
    'depends': ['account', 'base_vat'],
    'data': [
        'data/account.account.tag.csv',
        'data/account.tax.group.csv',
        'data/account_groups.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_post_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/mini_income_statment.xml',
    ],
    'post_init_hook': '_default_chart_template_id',
}
