# -*- encoding: utf-8 -*-

# Copyright (C) 2020 HuMint (Pty) Lts (<http://www.humint.co.za>).

{
    'name': 'Humint O - Localisation',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This is the latest basic South African localisation necessary to run Odoo in ZA:
================================================================================
    - a generic chart of accounts
    - SARS VAT Ready Structure""",
    'author': 'Humint',
    'website': 'https://www.humint.co.za',
    'depends': ['account', 'base_vat','l10n_za_humint_sub'],
    'data': [
        'data/product_categories.xml',
    ],
}
