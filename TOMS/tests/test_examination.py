from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import MissingError
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime
from odoo import _
from odoo.http import request
from datetime import date
import xml.etree.ElementTree as ET
import requests
# from odoo.tests import common

@tagged('-at_install', 'post_install')
class TestExamination(TransactionCase):
    """
        Tests for Examination Flow.
    """
    def test_createdata(self):
        # Create a new project with the test
        partner_id = self.env['res.partner'].browse(7082)
        company_id = self.env['res.company'].search([('name', '=', 'Spectacle Warehouse Atterbury')], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].search([], limit=1)
        test_clinic_exam = self.env['clinical.examination'].create({
            'partner_id': partner_id.id,
            'company_id': company_id.id
        })
        product_id = self.env['product.product'].search([('name', '=', 'Cases')], limit=1)
        # product_line = [()]
        # Check if the project name and the task name match
        # self.assertEqual(test_clinic_exam, 'TestProject')
        # self.assertEqual(test_project_task.name, 'ExampleTask')
        # Check if the project assigned to the task is in fact the correct id
        # self.assertEqual(test_project_task.project_id.id, test_project.id)
        # Do a little print to show it visually for this demo - in production you don't really need this.
        print('Your test was succesfull!', test_clinic_exam)
        print('Your test was succesfull!', test_clinic_exam.partner_id, test_clinic_exam.partner_id.name)
        icd_codes_ids = self.env['icd.codes'].search([], limit=1)

        line_values = {'product_id': product_id.id,
                       'name': product_id.display_name,
                       'product_uom_qty': 1,
                       'price_unit': product_id.lst_price,
                       'icd_codes_ids': [(4, icd_codes_ids.id)]}

        test_clinic_exam.write({'examination_line_ids': [(0, 0, line_values)]})
        print('\n\n======examination line created!!!!', test_clinic_exam.examination_line_ids)
        print('\n\n state', test_clinic_exam.state)
        test_clinic_exam.progress_examination()
        print('\n\n state11111', test_clinic_exam.state)

        clinical_final_rx_value = {'name': 'Test',
                                   'od_syh': 2,
                                   'od_cyl': 2,
                                   'od_axis': 2,
                                   'od_add': 2,
                                   'od_va': 2,
                                   'os_syh': 2,
                                   'os_cyl': 2,
                                   'os_axis': 2,
                                   'os_add': 2,
                                   'os_va': 2,
                                   'dispense': True,
                                   }

        test_clinic_exam.write({'clinical_final_rx_ids': [(0, 0, clinical_final_rx_value)]})
        print('\n\n----->test_clinic_exam.clinical_final_rx_ids------', test_clinic_exam.clinical_final_rx_ids)
        print('\n\n----->test_clinic_exam.clinical_final_rx_dis_ids------', test_clinic_exam.clinical_final_rx_dis_ids)

        wizard_final_rx_obj = self.env['wizard.final.rx']

        product_ids = self.env['product.template'].search([('categ_id.name','=','Lenses')
                                                           ], limit=2)
        # ('lens_material_id', '=', lens_material)
        # wizard_final_rx_value = {'lens_type_od': [(4, product_ids.ids)],
        #                          'lens_type_os': [(4, product_ids.ids)],
        #                          }
        print('\n\n========id----------', product_ids, product_ids.ids)
        frame_product_id = self.env['product.template'].search([('default_code','=','43529')])
        if frame_product_id:
            wizard_final_rx_id = wizard_final_rx_obj.create({'clinical_final_rx_id': test_clinic_exam.clinical_final_rx_dis_ids.ids[0],
                                                             'lens_type_od': [(6,0, product_ids.ids)],
                                                             'lens_type_os': [(6,0, product_ids.ids)],
                                                             'frame_model': frame_product_id.id,
                                                             'clinical_exam_id': test_clinic_exam.id
                                                             })
            print('\n\n=========wizard_final_rx_id', wizard_final_rx_id)
            wizard_final_rx_id.with_context(default_clinical_final_rx_id=test_clinic_exam.clinical_final_rx_dis_ids.ids[0]).fitting_details_apply()
            print('\n\n=======calllll')
            wizard_final_rx_id.submit_fitting_details()


        print('\n\n=========test line ------------',test_clinic_exam.dispensing_line_ids)
        invoice_id = test_clinic_exam.examination_invoice()
        print('\n\n=======invoice========', test_clinic_exam.company_id)
        print('\n\n=======invoice========', test_clinic_exam.invoice_id)
        test_clinic_exam.invoice_id.write({'company_id': test_clinic_exam.company_id.id})
        print('\n\n=======invoice========', test_clinic_exam.invoice_id.company_id)
        print('\n\n=======invoice========', test_clinic_exam.invoice_id.invoice_line_ids)
        print('\n\nuser', self.env.user.id)
        print('\n\nuser', self.env.user.name)
        # test_clinic_exam.invoice_id.action_submit_claim()
        self.submit_claim(test_clinic_exam.invoice_id)

    def submit_claim(self, invoice_id):

        print('\n\n-----call my submit claim', invoice_id)
        user_id = self.env['res.users'].sudo().search([('login', '=', 'admin')], limit=1)
        print('\n\n-----call my submit claim user', user_id)

        if not len(self.env['session.session'].search(
                [('user_id', '=', user_id.id), ('state', '!=', 'closed_posted')]).ids):
            raise UserError(
                _("There is no Open session for Payments, Please create and open a sessions to capture any payments"))
        current_date_time = datetime.now().strftime("%Y%m%d%H%M")
        ir_config_obj = self.env['ir.config_parameter']
        # practice_number = ir_config_obj.sudo().get_param('mediswitch_integration.practice_number')


        # practice_name = ir_config_obj.sudo().get_param('mediswitch_integration.practice_name')

        # print('\n\n=====invoice', invoice_id, invoice_id.company_id, invoice_id.company_id.name)

        for invoice in invoice_id:
            practice_number = invoice_id.company_id.practice_number
            print("\n\n==========>practice_number",practice_number)
            practice_name = invoice_id.company_id.practice_name
            if not invoice.partner_id.surname:
                raise MissingError("Member Surname is missing")
            if not invoice.partner_id.name:
                raise MissingError("Member Name is missing")
            if not invoice.partner_id.individual_internal_ref:
                raise MissingError("Member Internal Ref is missing")
            if not invoice.patient_id.surname:
                raise MissingError("Patient Surname is missing")
            if not invoice.patient_id.name:
                raise MissingError("Patient Name is missing")
            if not invoice.partner_id.medical_aid_id.destination_code:
                raise MissingError(_("Destination Code is Empty Please Correct?"))
            if not invoice.partner_id.medical_aid_no:
                raise MissingError(_("Missing Medical Aid Membership number, please Correct and Retry"))
            # if not invoice.optometrist_id.op_number:
            #     raise MissingError("Doctor PCNS number is missing")
            birthday = invoice.patient_id.birth_date and invoice.patient_id.birth_date.strftime("%Y%m%d")
            recall_exam_date = invoice.patient_id.recall_exam_date and invoice.patient_id.recall_exam_date.strftime(
                "%Y%m%d")
            invoice_date = invoice.date_invoice and invoice.date_invoice.strftime(
                "%Y%m%d")
            if invoice.patient_id.dependent_code and len(invoice.patient_id.dependent_code) > 12:
                p2_val = invoice.patient_id.dependent_code[0:12]
            else:
                p2_val = invoice.patient_id.dependent_code
            if invoice.partner_id.name and len(invoice.partner_id.name) > 30:
                m6_val = invoice.partner_id.name[0:30]
            else:
                m6_val = invoice.partner_id.name
            if invoice.partner_id.medical_aid_id.name and len(invoice.partner_id.medical_aid_id.name) > 20:
                m17_val = invoice.partner_id.medical_aid_id.name[0:20]
            else:
                m17_val = invoice.partner_id.medical_aid_id.name
            new_individual_internal_ref = ''
            if invoice.partner_id and invoice.partner_id.individual_internal_ref and '-' in invoice.partner_id.individual_internal_ref:
                new_individual_internal_ref = invoice.partner_id.individual_internal_ref.replace('-', '')
            if invoice.patient_id.name and len(invoice.patient_id.name) > 30:
                p5_val = invoice.patient_id.name[0:30]
            else:
                p5_val = invoice.patient_id.name
            paylod = """H|%s|%s|%s|%s|
S|%s|%s|%s|%s|%s|
M|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|
P|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n""" % (
                # Header (Start of Message) Record – Type ‘H’
                invoice.id or '', 120, 'TOMS2', '',
                # Service Provider Record – Type ‘S’
                current_date_time, practice_number or '', practice_name or '', '',
                self.env.user.company_id.vat or '',
                # Member Record – Type ‘M’
                invoice.partner_id.id_number or '', invoice.partner_id.title.shortcut or '',
                invoice.partner_id.initials or 'N',
                invoice.partner_id.surname or '',
                m6_val or '', invoice.partner_id.medical_aid_no or '', 'N',
                new_individual_internal_ref,
                invoice.partner_id.street or '', invoice.partner_id.street2 or '', invoice.partner_id.city or '',
                invoice.partner_id.zip or '',
                invoice.partner_id.mobile or '', invoice.partner_id.option_id.name or '', '',
                m17_val or '', invoice.partner_id.medical_aid_id.ref or '', '03',
                'network',
                invoice.partner_id.medical_aid_id.destination_code or '',
                # Patient Record – Type ‘P’
                p2_val or '', invoice.patient_id.surname or '',
                invoice.patient_id.initials or '',
                p5_val or '', birthday or '',
                invoice.patient_id.gender and invoice.patient_id.gender.upper() or '', '',
                invoice.patient_id.id_number or '', recall_exam_date or '', '', '', '', '', '', '', '', '',
                '', '01', '', '', invoice.id or '',
            )
            count = 1
            t11 = False
            # wdb.set_trace()
            for line in invoice.invoice_line_ids:
                if not line.product_id.default_code:
                    raise MissingError("Tariff Code/Ref is missing")
                if invoice.partner_id.option_id.code == 'SAOA':
                    t11 = line.product_id.saoa_code_id.code
                    if not t11:
                        raise MissingError(_("Tariff Code is not populated, please correct and retry(SAOA)"))
                elif invoice.partner_id.option_id.code == 'PPN!':
                    t11 = line.product_id.ppn1_code_id.code
                    if not t11:
                        raise MissingError(_("Tariff Code is not populated, please correct and retry(PPN1)"))
                # T
                paylod += """T|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n""" % (
                    # Treatment Record – Type ‘T’
                    count, invoice_date, invoice_date, '', invoice.id or '',
                    line.id, '02',
                    int(line.quantity * 100 or 0), '06', t11, '05', '',
                    '', '10',
                    line.product_id.name or '',
                    '',
                    '', '', '',
                    '', '', '', '', '', '', '11')
                # OP records
                if line.final_rx_id:
                    rx_data = line.final_rx_id

                    # Left side values
                    op_count = 1
                    L_v12_val = ''
                    L_v13_val = ''
                    if rx_data.od_prism:
                        L_v12_val = int(str(rx_data.od_prism)[0]) * 100
                        if len(rx_data.od_prism) > 1:
                            L_v13_val = rx_data.od_prism[1:]
                    if line.product_id.name and len(line.product_id.name) > 50:
                        v4_val = line.product_id.name[0:50]
                    else:
                        v4_val = line.product_id.name
                    # v12_val = rx_data.od_prism.isdigit()
                    paylod += """OP|{v2}|{v3}|{v4}|{v5}|{v6}|{v7}|{v8}|{v9}|{v10}|{v11}|{v12}|{v13}|{v14}|{v15}|\n""".format(
                        # OP Record – Type ‘OP’
                        v2=op_count,
                        v3=line.product_id.seller_ids and line.product_id.seller_ids[
                            0].display_name or "None Specified",
                        v4=v4_val or '',
                        v5='',
                        v6='',
                        v7='L',
                        v8=int(rx_data.od_syh * 100) or '',
                        v9=int(rx_data.od_cyl * 100) or '',
                        v10=int(rx_data.od_axis * 100) or '',
                        v11=int(rx_data.od_add * 100) or '',
                        v12=L_v12_val,
                        v13=L_v13_val, v14='',
                        v15=line.product_id.name or '',
                    )

                    # Right_side_values
                    op_count += 1
                    R_v12_val = ''
                    R_v13_val = ''
                    if rx_data.os_prism:
                        R_v12_val = int(rx_data.os_prism[0]) * 100
                        if len(rx_data.os_prism) > 1:
                            R_v13_val = rx_data.os_prism[1:]
                    paylod += """OP|{v2}|{v3}|{v4}|{v5}|{v6}|{v7}|{v8}|{v9}|{v10}|{v11}|{v12}|{v13}|{v14}|{v15}|\n""".format(
                        # OP Record – Type ‘OP’
                        v2=op_count,
                        v3=line.product_id.seller_ids and line.product_id.seller_ids[
                            0].display_name or "None Specified",
                        v4=v4_val or '',
                        v5='',
                        v6='',
                        v7='R',
                        v8=int(rx_data.os_syh * 100) or '',
                        v9=int(rx_data.os_cyl * 100) or '',
                        v10=int(rx_data.os_axis * 100) or '',
                        v11=int(rx_data.os_add * 100) or '',
                        v12=R_v12_val,
                        v13=R_v13_val, v14='',
                        v15=line.product_id.name or '',
                    )
                # DR
                # print("\n\n\n\n")
                paylod += """DR|%s|%s|%s|%s|%s|%s|%s|%s|\n""" % (
                    practice_number or '', practice_name or '', '01',
                    invoice.optometrist_id.op_number or '', '01', '', '', '',
                )
                d_count = 1

                for each in line.icd_codes_ids:
                    paylod += """D|%s|%s|%s|%s|%s|\n""" % (  # D
                        '01', '01', each.code, '', '01' if d_count == 1 else '02',)
                    d_count += 1
                paylod += """Z|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n""" % (
                    # Treatment Financial Record – Type ‘Z’
                    int(line.price_total * 100),
                    int(line.price_total * 100), '', '', '', '', '', '', '',
                    int(line.price_total * 100), '', '', '', '', '',
                    int(line.price_total * 100), '',
                )
                count += 1
            paylod += """F|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|
E|%s|%s|%s|\n""" % (
                # Claim Financial Record – Type ‘F’
                int(invoice.amount_total * 100), int(invoice.amount_total * 100), int(invoice.amount_total * 100),
                '', '', '', '',
                invoice.id or '',
                '', int(invoice.amount_total * 100), '',
                # Footer (End of Message) Record – Type ‘E’
                invoice.id or '', '1', int(invoice.amount_total * 100),
            )
            paylod = self.env['speacial.charcters'].speacial_char_escape(paylod)
            print('\n\n=======paylod', paylod)
            invoice.write({'comment': paylod.strip()})
            print('\n\n======', invoice.company_id, invoice.company_id.name)
            # data = self.env['speacial.charcters'].echo_operation(invoice.company_id.id)
            # print('\n\n====data', data)
            # if data is not None:
            #     if data[1] == 'OK':
            #         url = data[0]
            #     else:
            #         raise Warning(_(
            #             'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(502 Bad Gateway)"))
            # else:
            #     raise Warning(_(
            #         'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit'))
            cmp_id = self.env['res.company'].browse(invoice.company_id.id)

            if cmp_id.select_url == 'production_url':
                url = cmp_id.production_url
            elif cmp_id.select_url == 'fail_over_url':
                url = cmp_id.production_url2
            else:
                raise Warning(_('Mediswitch Gateway Offline!!'))

            if invoice.company_id.for_what == 'test':
                username = invoice.company_id.user_name_test
                password = invoice.company_id.password_test
                package = invoice.company_id.package_test
                mode = invoice.company_id.mode_test
                txversion = invoice.company_id.txversion_test
                txtype = invoice.company_id.txtype_test
            else:
                username = invoice.company_id.user_name_production
                password = invoice.company_id.password_production
                package = invoice.company_id.package_production
                mode = invoice.company_id.mode_production
                txversion = invoice.company_id.txversion_production
                txtype = invoice.company_id.txtype_test
            xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <v2:submitOperation>
                             <user>%s</user>
                             <passwd>%s</passwd>
                             <package>%s</package>
                             <destination>%s</destination>
                             <txType>%s</txType>
                             <mode>%s</mode>
                             <txVersion>%s</txVersion>
                             <userRef>%s</userRef>
                             <payload>%s</payload>
                          </v2:submitOperation>
                       </soapenv:Body>
                    </soapenv:Envelope>
                    """ % (
                username, password, package, invoice.partner_id.plan_option_id.destination_code, txtype, mode,
                txversion,
                invoice.id, paylod)
            print('\n\n======xml1======', xml1)
            headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
            response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
            print('\n\n=========response========', response)
            response_string = ET.fromstring(response.content)
            data_dict = {}
            responsepayload = False
            for node in response_string.iter():
                if node.tag == 'swref':
                    invoice.user_ref = node.text
                    data_dict.update({'switch_reference': node.text})
                elif node.tag == 'responsePayload':
                    print('\n\n=======responsepayload', node.text)
                    invoice.response_payload = node.text
                    if node.text and node.text == 'Switch System Error':
                        raise Warning(_(
                            'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(Switch System Error)"))
                    data_dict.update({'response_payload': node.text})
                    responsepayload = node.text
                elif node.tag == 'message':
                    raise Warning(_(
                        'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(" + node.text + ")"))
                else:
                    data_dict.update({str(node.tag): node.text})
            data_dict.update(
                {'invoice_id': invoice.id, 'destination_code': invoice.partner_id.plan_option_id.destination_code or '',
                 'user_reference': invoice.id or '', 'generated_payload': paylod,
                 'response_payload_date': datetime.now()})
            print('\n\n=========data dict======', data_dict)
            # 5/0
            claim_id = self.env['mediswitch.submit.claim'].create(data_dict)
            print('\n\n==========clain id========', claim_id)
            if responsepayload:
                print("\n\n=========>responsepayload", responsepayload)
                claim_status_lines = []
                order_lines = []
                lines = responsepayload.split("\n")
                strings = ("Invalid Missing", "Invalid")
                if any(s in lines[0] for s in strings):
                    raise Warning(_(
                        'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(" +
                        lines[0] + ")"))
                if lines and lines[0] and lines[0].startswith('H'):
                    flag = 0
                    treatment_line = 0
                    balance_price = 0
                    approved_price = 0
                    total_approved_price = 0
                    general_comments = ''
                    rejection_count = ''
                    status_claim_level = ''
                    list1 = []
                    r_list = []
                    g_list = []
                    number = 0
                    message = ''
                    check_element_list = ['T', 'E', 'FR', 'F']
                    for line in lines:
                        r_line = ''
                        position = lines.index(line)
                        pos = position
                        split_line = line.split("|")
                        if line.startswith('S'):
                            if int(line.split("|")[5]) >= 0:
                                flag = 1
                        if line.startswith('R') and flag == 1:
                            rejection_count += "\n" + split_line[2] + ' - ' + split_line[1]
                        if line.startswith('FR') and flag == 1:
                            rejection_count += "\n" + split_line[1]
                        if line.startswith('G'):
                            general_comments = split_line[1]
                        if line.startswith('P') and flag == 1:
                            message11, message2, message3 = invoice.claim_messages(split_line[13], split_line[14],
                                                                                split_line[15])
                            message = message3 + ' - ' + message11 + ', from ' + message2 + '\n'
                            invoice.claim_level_mediswitch_status = split_line[13]
                            invoice.authorization_code = split_line[7]
                            if split_line[14] == '01':
                                invoice.responding_party = "MediSwitch"
                            elif split_line[14] == '02':
                                invoice.responding_party = "Medical Scheme / Administrator"
                            status_claim_level = invoice.claim_level_status(split_line[13])
                        if line.startswith('T') and flag == 1:
                            treatment_line += 1
                            message1, message2, message3 = invoice.claim_messages(split_line[14], split_line[15],
                                                                               split_line[16])
                            claim_status_lines.append(message1)
                            position = position + 1

                            while lines[position] and position > 0 and lines[position][0] not in check_element_list:
                                if lines[position].startswith('R'):
                                    split_list = lines[position].split("|")
                                    r_line += "\n" + split_list[2] + ' - ' + split_list[1]
                                else:
                                    pass
                                position = position + 1
                            r_list.append(r_line)
                            pos = pos + 1
                            if lines[pos].startswith('G'):
                                split_list = lines[pos].split("|")
                                g_list.append(split_list[1])
                            else:
                                g_list.append(" ")
                        if line.startswith('Z'):
                            if split_line[18]:
                                approved_price = int(split_line[18]) / 100
                                total_approved_price += approved_price
                            if split_line[16]:
                                balance_price = int(split_line[16]) / 100
                            list1.append({'approve': approved_price, 'balance': balance_price})
                        claim_id.response_error = rejection_count
                        invoice.response_description = rejection_count
                        invoice.general_comments = general_comments
                    if total_approved_price or status_claim_level == 'Claim Accepted for delivery' or status_claim_level == 'Claim Accepted for processing':
                        invoice.action_invoice_open()
                        vals = {}
                        accquire_id = self.env['payment.acquirer'].search([('name', '=', 'Mediswitch Payment Gateway'),('company_id','=',invoice.company_id.id)])
                        vals.update({
                            'amount': total_approved_price if total_approved_price else invoice.amount_total,
                            'currency_id': self.env.user.company_id.currency_id.id,
                            'partner_id': invoice.partner_id.id,
                            'invoice_ids': [(6, 0, invoice.ids)],
                            'state': 'done',
                        })
                        vals['acquirer_id'] = accquire_id.id
                        vals['reference'] = invoice.name
                        transaction = self.env['payment.transaction'].create(vals)
                        journal_id = self.env['account.journal'].sudo().search([('type', '=', 'bank'), ('company_id', '=', invoice.company_id.id)], limit=1)
                        payment_method_id = self.env['account.payment.method'].search([('name', '=', 'Manual'), ('payment_type', '=', 'outbound')], limit=1)
                        payments = {
                            'payment_type': 'outbound',
                            'partner_type': 'customer',
                            'partner_id': invoice.partner_id.id,
                            'amount': total_approved_price,
                            'journal_id': journal_id.id,
                            'payment_date': date.today(),
                            'communication': invoice.number,
                            'payment_method_id': payment_method_id.id,
                            'invoice_ids': [(4, invoice.id)],
                            'payment_transaction_id': transaction.id,
                            'company_id': invoice.company_id.id
                        }
                        payment_id = self.env['account.payment'].create(payments)
                        print('\n\n======payment_id--->',payment_id)
                        payment_id.post()
                    elif status_claim_level == 'Claim Rejected':
                        invoice.state = 'draft'
                    for each in invoice.invoice_line_ids:
                        if len(claim_status_lines) > 0 and claim_status_lines[number]:
                            status = claim_status_lines[number]
                        else:
                            status = ""
                        each.approved_amount = list1[number].get('approve')
                        each.balance_amount = list1[number].get('balance')
                        if r_list:
                            each.description_line = r_list[number]
                        if g_list:
                            each.commments_line = g_list[number]

                        each.claim_status = status
                        line = [0, 0, {'product_id': each.product_id.id,
                                       'quantity': each.quantity,
                                       'price_unit': each.price_unit,
                                       'approved_amount': list1[number].get('approve'),
                                       'balance_amount': list1[number].get('balance'),
                                       'tax_ids': [[4, id.id] for id in
                                                   each.invoice_line_tax_ids] if each.invoice_line_tax_ids else False,
                                       'price_subtotal': each.price_subtotal, 'status': status}]
                        order_lines.append(line)
                        number += 1

                    view_id = self.env['response.error.wizard'].sudo().create(
                        {'name': message, 'response_error': rejection_count or '', 'practise_name': practice_name,
                         'practise_number': practice_number, 'Medical_aid': invoice.partner_id.medical_aid_id.name,
                         'patient_name': invoice.patient_id.id, 'patient_dob': invoice.patient_id.birth_date,
                         'invoice_id': invoice.id or '', 'member_no': invoice.partner_id.medical_aid_no,
                         'claim_status_lines_ids': order_lines, 'general_comments': general_comments,
                         'responding_party': invoice.responding_party,
                         })
                    return {
                        'name': 'Response Wizard',
                        'type': 'ir.actions.act_window',
                        'res_model': 'response.error.wizard',
                        'res_id': view_id.id,
                        'view_id': self.env.ref('mediswitch_integration.response_error_wizard').id,
                        'view_mode': 'form',
                        'target': 'new',
                    }