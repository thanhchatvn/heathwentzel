{
    'name': 'TOMS',
    'version': '15.31',
    'author': 'Strategic Dimensions',
    'website': "www.strategicdimensions.co.za",
    'depends': ['base', 'sale_management', 'calendar', 'sms_frame', 'account','account_accountant', 'stock','crm',
                'project',  'sale_stock','sms','note',
                'purchase'],
    'application': True,
    'data': [
        'data/ir_sequence_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/toms_demo_data.xml',
        'views/assets.xml',
        'views/res_partner.xml',
        'views/child_form.xml',
        'views/medical_aid_plan.xml',
        'views/medical_codes.xml',
        'views/product_template.xml',
        'data/humint_language.xml',
        'data/humint_occupation.xml',
        'data/humint_title.xml',
        'data/codes.xml',
        'data/automated_actions.xml',
        'data/paper_formats.xml',
        'views/calendar_event.xml',
        'views/clinic_examination.xml',
        'views/res_partner_contact.xml',
        'views/clinical_menus.xml',
        'views/purchase_order.xml',
        'views/payment_pivot.xml',
        'views/product_pricelist_views.xml',
        'wizard/crm_lead_lost_wizard.xml',
        'views/account_invioce.xml',
        'report/customer_invoice.xml',
        'report/product_report.xml',
        'report/custom_productlabel.xml',
        'report/custom_product_label_shipment.xml',
        'report/job_report.xml',
        'report/tray_label.xml',
        'views/project_task.xml',
        'wizard/wizard_final_rx.xml',
        'wizard/project_fitting_detail.xml',
        'wizard/detaching_dependent_wizard.xml',
        'wizard/wizard_receive_product.xml',
        'data/cron_recall_customer.xml',
        'views/res_company.xml',
        'views/appointment_view.xml',
        'views/res_users.xml',
        'views/stock_views.xml',
        'views/adjustment_lines.xml',
        'views/account_account.xml',
        'wizard/wizard_stock_take_validate.xml',
        'views/medical_aid_confrimations.xml',
        'views/project_views.xml',
    ],
    'qweb': [
        'static/src/xml/roster_view.xml',
        'static/src/xml/payment.xml',

    ],
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_check'
}
