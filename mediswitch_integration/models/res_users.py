from odoo import models, api, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    op_number = fields.Char(string="OP Number")
    optometrist = fields.Boolean(string="Optometrist")




class ResCompany(models.Model):
    _inherit = 'res.company'

    # mediswitch per user

    production_url = fields.Char(string="Production URL", default='https://wsgateway1.mediswitch.co.za/wsgateway/MediswitchGatewayV2')
    test_url = fields.Char(string="Test URL", default='https://wsgateway1.mediswitch.co.za/qa/wsgateway/MediswitchGatewayV2')
    production_url2 = fields.Char(string="Fail Over Production URL", default='https://wsgateway2.mediswitch.co.za/wsgateway/MediswitchGatewayV2')
    test_url2 = fields.Char(string="Fail Over Test URL", default="https://wsgateway2.mediswitch.co.za/qa/wsgateway/MediswitchGatewayV2")
    claim_reversal = fields.Boolean(string="Claims & Reversals")
    do_payment = fields.Boolean(string="Auto Validate Payment")
    benefit_check = fields.Boolean(string="Benefit Check")
    membership_status_validation = fields.Boolean(string="Membership Status Validation (MSV)")
    electronic_remittance_advice = fields.Boolean(string="Electronic Remittance Advice (eRA)")
    practice_number = fields.Char(string="Practice Number")
    practice_name = fields.Char(string="Practice Name")
    for_what = fields.Selection([('test', 'Testing'), ('production', 'Production')], string="For",default='test')
    user_name_test = fields.Char(string="UserName Test", default='TEST7025')
    user_name_production = fields.Char(string="UserName Production")
    password_test = fields.Char(string="Password Test", default='test3614')
    password_production = fields.Char(string="Password Production")
    package_test = fields.Char(string="Package Name Test", default='SWITCHON')
    package_production = fields.Char(string="Package Name Production")
    txtype_test = fields.Char(string="Tx Type Test", default='302')
    txtype_production = fields.Char(string="Tx Type Production")
    mode_test = fields.Char(string="Mode Test", default='realtime')
    mode_production = fields.Char(string="Mode Production")
    txversion_test = fields.Char(string="Tx Version Test", default='121')
    txversion_production = fields.Char(string="Tx Version Production", default='121')
    journal_id = fields.Many2one("account.journal", string="Payment Journal")

    select_url = fields.Selection([('fail_over_url', 'Fail Over Url'), ('production_url', 'Production Url'),
                                   ('error', 'Error')], string="Select Url")
