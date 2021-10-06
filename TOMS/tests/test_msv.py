from odoo.tests.common import TransactionCase
from odoo.tests import tagged
import random
from datetime import datetime
@tagged('-at_install', 'post_install')
class TestMsv(TransactionCase):
    """
        Test for MSV.
    """
    print('\n\n--------test MSV')
    def test_create_msv_data(self):
        random_id_number = random.randint(1111111111, 9999999999)
        random_individual_ref_no = 'SWKW-' + str(random.randint(111111, 999999))
        print("\n\n=======>random_individual_ref_no", random_individual_ref_no)
        print("\n\n==============>random_id_number", random_id_number)
        medical_aid_id = False
        option_id = False
        plan_option_id = False
        medical_aid = self.env['res.partner'].search([('name', '=', 'Private')], limit=1)
        if medical_aid:
            medical_aid_id = medical_aid.id
            print("\n\n=========>medical_aid_id", medical_aid_id)
        else:
            medical_aid = self.env['res.partner'].search([], limit=1)
            medical_aid_id = medical_aid.id
            print("\n\n=========>medical_aid_id", medical_aid_id)
        option = self.env['medical.aid.plan'].search([('name', '=', 'Private')], limit=1)
        if option:
            option_id = option.id
            print("\n\n==========>option_id", option_id)
        else:
            option = self.env['medical.aid.plan'].search([], limit=1)
            option_id = option.id
            print("\n\n==========>option_id", option_id)
        plan_option = self.env['medical.aid.plan.option'].search([('name', '=', 'Private')], limit=1)
        if plan_option:
            plan_option_id = plan_option.id
            print("\n\n==========>plan_option_id", plan_option_id)
        else:
            plan_option = self.env['medical.aid.plan.option'].search([], limit=1)
            plan_option_id = plan_option.id
            print("\n\n==========>plan_option_id", plan_option_id)
        property_account_receivable_id = self.env['account.account'].search([], limit=1)
        print("\n\n==========>property_account_receivable_id========>", property_account_receivable_id)
        if medical_aid_id and option_id and plan_option_id:
            partner = self.env['res.partner'].create({
                'name': 'New Test User',
                'medical_aid_id': medical_aid_id,
                'option_id': option_id,
                'plan_option_id': plan_option_id,
                'surname': 'New Test',
                'birth_date': datetime.strptime('2012-01-01', '%Y-%m-%d'),
                'first_name': 'New User',
                'id_number': random_id_number,
                'customer': True,
                'gender': 'm',
                'company_id': 3,
                'individual_internal_ref': random_individual_ref_no,
                'medical_aid_no': random_id_number,
                'property_account_receivable_id': property_account_receivable_id.id,
                'property_account_payable_id': property_account_receivable_id.id,
            })
            print("\n\n==========>partner", partner, partner.company_id)
            partner.medical_aid_id.write({'msv_allowed': True})
            partner.medical_aid_id.write({'destination_code': 'DHEA0000'})
            partner.submit_msv()
            msv = self.env['msv.response'].search([('partner_id', '=', partner.id), ('msv_type', '=', 'msv')])
            print("\n\n==========>msv has msv msv", msv)
            print("\n\n==========>msv has been submitted")
            partner.id_msv()
            id_msv = self.env['msv.response'].search([('partner_id', '=', partner.id), ('msv_type', '=', 'id_msv')])
            print("\n\n==================>id msv", id_msv)
            print("\n\n===========>id msv has been submitted.")
            partner.surname_dob_msv()
            sur_dob_msv_msv = self.env['msv.response'].search([('partner_id', '=', partner.id),
                                                               ('msv_type', '=', 'sur_dob_msv')])
            print("\n\n==================>surname DOB msv", sur_dob_msv_msv)
            print("\n\n===========>surname DOB msv has been submitted.")
