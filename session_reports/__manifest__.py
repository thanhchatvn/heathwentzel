# -*- coding: utf-8 -*-
{
    'name': "Session and Reports",
    'version': '1.3.4',
    'category': 'Finance',
    'summary': """Session and Reports""",
    'depends': ['account'],
    'author': "Strategic Dimensions",
    'description': """
        Session and Reports
    """,
    'website': "http://www.strategicdimensions.co.za",
    'data': [
        'data/ir_sequence.xml',
        # 'data/ir_cron.xml',
        'security/session_reports_access.xml',
        'security/ir.model.access.csv',
        # 'report/session_cash_control_report.xml',
        # 'report/session_day_end_report.xml',
        'views/session_session.xml',
        # 'views/session_hp_reports.xml',
        # 'views/session_sales_report.xml',
        'views/account_bank_statement_view.xml',
        # 'views/session_payment_report.xml',
        # 'views/session_inventory_report.xml',
        'views/session_day_end_view.xml',
        'wizard/cash_box_in_out.xml',
        # 'report/stock_picking_templates.xml'
    ],
    "active": False,
    "installable": True,
}
