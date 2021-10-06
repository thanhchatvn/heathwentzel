
from odoo import fields, models, api , _
from suds.wsse import Security, UsernameToken
from suds.client import Client
from datetime import datetime,date
from odoo.http import request
from odoo.exceptions import MissingError , Warning
import xml.etree.ElementTree as ET
import time
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class MediswitchSubmitClaim(models.Model):
    _name = "mediswitch.submit.claim"
    _description='Submit the claim to the mediswitch'
    _rec_name = 'name'

    name = fields.Char(string="Name")
    response_payload_date = fields.Datetime(string="Date")
    destination_code = fields.Char(string="Destination Code")
    user_reference = fields.Integer(string="User Reference")
    generated_payload = fields.Text(string="Payload")
    status = fields.Char(string="Status")
    switch_reference = fields.Char(string="Switch Reference")
    retry = fields.Integer(string="Retry")
    response_payload = fields.Text(string="Response Payload")
    force=fields.Integer(string="Force")
    invoice_id = fields.Many2one("account.invoice",string="Invoice Ref",readonly="1")
    fetch_claim_id=fields.One2many("mediswitch.fetch.claim",'claim_ref_id')
    status_morefiles = fields.Char(string="Status Of MoreFiles",invisible="1")
    response_error = fields.Text(string="Response Error")
    general_comments = fields.Text(string="General Comments")
    view_id = fields.Many2one('response.error.wizard')
    is_last_claim = fields.Boolean()
    mediswitch_type = fields.Selection([('Claim', 'Claim'), ('Benefit', 'Benefit')],
                                string="Type")

    @api.multi
    def view_response(self):
        if self.view_id:
            return {
                'name': 'Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'response.error.wizard',
                'res_id': self.view_id.id,
                'view_id': self.env.ref('mediswitch_integration.response_error_wizard_1').id,
                'view_mode': 'form',
                'target': 'new',
            }
        elif not self.view_id and self.response_payload:
            responsepayload = self.response_payload
            for invoice in self.invoice_id:
                if responsepayload:
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
                        # print("\n\n\n callll->")
                        # total_approved_price = 7140
                        # status_claim_level = 'Claim Accepted for delivery'
                        for each in invoice.invoice_line_ids:
                            if len(claim_status_lines) > 0 and claim_status_lines[number]:
                                status = claim_status_lines[number]
                            else:
                                status = ""
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
                            {'name': message, 'response_error': rejection_count or '', 'practise_name': invoice.company_id.practice_name,
                             'practise_number': invoice.company_id.practice_number, 'Medical_aid': invoice.partner_id.medical_aid_id.name,
                             'patient_name': invoice.patient_id.id, 'patient_dob': invoice.patient_id.birth_date,
                             'invoice_id': invoice.id or '', 'member_no': invoice.partner_id.medical_aid_no,
                             'claim_status_lines_ids': order_lines, 'general_comments': general_comments,
                             'responding_party': invoice.responding_party,
                             })
                        self.view_id = view_id.id
                        return {
                            'name': 'Response Wizard',
                            'type': 'ir.actions.act_window',
                            'res_model': 'response.error.wizard',
                            'res_id': view_id.id,
                            'view_id': self.env.ref('mediswitch_integration.response_error_wizard_1').id,
                            'view_mode': 'form',
                            'target': 'new',
                        }




    @api.multi
    def fetch_operations(self):
        if self.env.context.get('fetch_response'):
            invoice_ids = self.invoice_id
        else:
            invoice_ids = self.env['account.invoice'].search([('claim_level_mediswitch_status', 'in', ['01', '02'])])

        for invoice in invoice_ids:
            if invoice.company_id.for_what == 'test':
                username = invoice.company_id.user_name_test
                password = invoice.company_id.password_test
                package = invoice.company_id.package_test
            else:
                username = invoice.company_id.user_name_production
                password = invoice.company_id.password_production
                package = invoice.company_id.package_production
            # data = self.env['speacial.charcters'].echo_operation(invoice.company_id.id)
            # if data[1] == 'OK':
            #     url = data[0]
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

            xml = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                           <soapenv:Header/>
                           <soapenv:Body>
                              <v2:fetchOperation>
                                 <user>%s</user>
                                 <passwd>%s</passwd>
                                 <package>%s</package>
                                 <txType>302</txType>
                                 <swref>%s</swref>
                                 <force>%s</force>
                              </v2:fetchOperation>
                           </soapenv:Body>
                        </soapenv:Envelope>""" % (
                username, password, package, invoice.user_ref, 0)
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                _logger.error(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit'))
            data_dict = {}
            responsepayload = False
            for node in response_string.iter():
                if node.tag == 'originalSwref':
                    data_dict.update({'origial_swref': node.text})
                elif node.tag == 'responsePayload':
                    if node.text and node.text == 'Switch System Error':
                        raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit'))
                    data_dict.update({'response_payload': node.text})
                elif node.tag == 'feedbackType':
                    data_dict.update({'feedback_type': node.text})
                elif node.tag == 'feedbackVersion':
                    data_dict.update({'feedback_version': node.text})
                elif node.tag == 'moreFiles':
                    data_dict.update({'morefiles': int(node.text)})
                elif node.tag == 'originalUserRef':
                    data_dict.update({'original_userref': node.text})
                elif node.tag == 'originalDataSetId':
                    if node.text:
                        data_dict.update({'original_dataset_id': int(node.text)})
                elif node.tag == 'fileName':
                    data_dict.update({'filename': node.text})
                elif node.tag == 'fileDate':
                    data_dict.update({'filedate': node.text or date.today()})
                elif node.tag == 'message':
                    raise Warning(_(node.text))
                else:
                    data_dict.update({str(node.tag): node.text})
            claim_id = self.env['mediswitch.submit.claim'].search([('switch_reference', '=', invoice.user_ref)],
                                                                  limit=1)
            data_dict.update(
                {'claim_ref_id': claim_id.id})
            fetch_id = self.env['mediswitch.fetch.claim'].create(data_dict)
            if responsepayload:
                claim_status_lines = []
                lines = responsepayload.split("\n")
                strings = ("Invalid Missing", "Invalid")
                if any(s in lines[0] for s in strings):
                    raise Warning(_(lines[0]))
                if lines and lines[0] and lines[0].startswith('H'):
                    flag = 1
                    treatment_line = 0
                    balance_price = 0
                    approved_price = 0
                    total_approved_price = 0
                    list1 = []
                    number = 0
                    message = ''
                    for line in lines:
                        split_line = line.split("|")
                        if line.startswith('S'):
                            if int(line.split("|")[5]) >= 0:
                                flag = 1
                        if line.startswith('G'):
                            rejection_count += "\n" + split_line[1]
                        if line.startswith('R') and flag == 1:
                            rejection_count = split_line[2] + ' - ' + split_line[1]
                            fetch_id.response_error = rejection_count
                        if line.startswith('FR') and flag == 1:
                            rejection_count = split_line[1]
                            fetch_id.response_error = rejection_count
                        if line.startswith('P') and flag == 1:
                            message11, message2, message3 = invoice.claim_messages(split_line[13], split_line[14],
                                                                                split_line[15])
                            message = message3 + ' - ' + message11 + ', from ' + message2 + '\n'
                            invoice.claim_level_mediswitch_status = split_line[13]
                        if line.startswith('T') and flag == 1:
                            treatment_line += 1
                            message1, message2, message3 = invoice.claim_messages(split_line[14], split_line[15],
                                                                               split_line[16])
                            claim_status_lines.append(message1)
                        if line.startswith('Z'):
                            if split_line[18]:
                                approved_price = int(split_line[18]) / 100
                                total_approved_price += approved_price
                            if split_line[16]:
                                balance_price = int(split_line[16]) / 100
                            list1.append({'approve': approved_price, 'balance': balance_price})
                    if total_approved_price:
                        invoice.action_invoice_open()
                        vals = {}
                        if invoice.company_id.do_payment:
                            accquire_id = self.env['payment.acquirer'].search([('name','=','Mediswitch Payment Gateway'),('company_id','=',self.env.user.company_id.id)])
                            vals.update({
                                'amount': total_approved_price,
                                'currency_id': self.env.user.company_id.currency_id.id,
                                'partner_id': invoice.partner_id.id,
                                'invoice_ids': [(6, 0, invoice.ids)],
                                'state': 'done',
                            })
                            vals['acquirer_id'] = accquire_id.id
                            vals['reference'] = invoice.name
                            transaction = self.env['payment.transaction'].create(vals)
                            # journal_id = request.env['account.journal'].sudo().search(
                            #     [('type', '=', 'bank'),('company_id','=',self.env.user.company_id.id)], limit=1)
                            if not invoice.company_id.journal_id:
                                raise Warning(_("Please Select Journal for Mediswitch Payment...!!"))
                            payment_method_id = self.env['account.payment.method'].search(
                                [('name', '=', 'Manual'), ('payment_type', '=', 'outbound')], limit=1)
                            payments = {
                                'payment_type': 'inbound',
                                'partner_type': 'customer',
                                'partner_id': invoice.partner_id.id,
                                'amount': total_approved_price,
                                'journal_id': invoice.company_id.journal_id.id,
                                'payment_date': date.today(),
                                'communication': invoice.number,
                                'payment_method_id': payment_method_id.id,
                                'invoice_ids': [(4, invoice.id)],
                                'payment_transaction_id': transaction.id,
                            }
                            payment_id = self.env['account.payment'].create(payments)
                            payment_id.post()
                    for each in invoice.invoice_line_ids:
                        if len(claim_status_lines) > 0 and claim_status_lines[number]:
                            status = claim_status_lines[number]
                        else:
                            status = ""
                        each.approved_amount = list1[number].get('approve')
                        each.balance_amount = list1[number].get('balance')
                        each.claim_status = status
                        number += 1

    @api.model
    def create(self, vals):
        res = super(MediswitchSubmitClaim, self).create(vals)
        name = self.env['ir.sequence'].next_by_code('claim_sequence')
        if res.invoice_id and res.invoice_id.sequence_number_next and res.invoice_id.sequence_number_next_prefix:
            res.name = name + '-' + res.invoice_id.sequence_number_next_prefix + res.invoice_id.sequence_number_next
        else:
            res.name = name
        return res

class MediswitchFetchClaim(models.Model):
    _name="mediswitch.fetch.claim"
    _description="fetch the response of the mediswitch"
    _rec_name="origial_swref"

    claim_ref_id=fields.Many2one("mediswitch.submit.claim",string="Claim Ref",readonly="1")
    status=fields.Char(string="Fetch Status")
    feedback_type=fields.Char(string="Feedback Type")
    feedback_version=fields.Char(string="FeedBack Version")
    morefiles=fields.Integer(string="More Files")
    origial_swref=fields.Char(string="Switch Reference")
    original_userref=fields.Char(string="User Reference")
    original_dataset_id=fields.Integer(string="DataSet Id")
    filename=fields.Char(string="File Name")
    filedate=fields.Date(string="File Date")
    response_payload=fields.Text(string="Response Payload")
    response_error = fields.Text(string="Response Error")


class Globalfetch(models.Model):
    _name = "global.fetch.claim"
    _description = "To fetch claim from mediswitch"

    name = fields.Char(string="Status")
    f_type = fields.Char(string="feedbackType")
    f_version = fields.Char(string="feedbackVersion")
    morefiles= fields.Char(string="moreFiles")
    originalswref= fields.Char(string="originalSwref")
    originaluserref= fields.Char(string="originalUserRef")
    originaldatasetid= fields.Char(string="originalDataSetId")
    filename= fields.Char(string="fileName")
    filedate= fields.Char(string="fileDate")
    responsepayload= fields.Char(string="responsePayload")
    txtype= fields.Char(string="txType")
    swref= fields.Char(string="swRef")
    force= fields.Integer(string="force", default=0)
    invoice_id = fields.Many2one("account.invoice", string="Invoice Ref")

    @api.model
    def create_global_fetch_record(self):
        view_id = self.env.ref('mediswitch_integration.global_fetch_claims_form_view_1').id
        return view_id

    def fetch_response(self):
        # data = self.env['speacial.charcters'].echo_operation(self.company_id.id)
        # if data[1] == 'OK':
        #     url = data[0]
        # else:
        #     raise Warning(_('Mediswitch Gateway Busy!!'))
        cmp_id = self.env['res.company'].browse(self.company_id.id)

        if cmp_id.select_url == 'production_url':
            url = cmp_id.production_url
        elif cmp_id.select_url == 'fail_over_url':
            url = cmp_id.production_url2
        else:
            raise Warning(_('Mediswitch Gateway Offline!!'))

        for partner in self:
            if partner.company_id.for_what == 'test':
                username = partner.company_id.user_name_test
                password = partner.company_id.password_test
                package = partner.company_id.package_test
            else:
                username = partner.company_id.user_name_production
                password = partner.company_id.password_production
                package = partner.company_id.package_production
            xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                       <soapenv:Header/>
                       <soapenv:Body>
                          <v2:fetchOperation>
                             <user>%s</user>
                             <passwd>%s</passwd>
                             <package>%s</package>
                             <txType>%s</txType>
                             <swref>%s</swref>
                             <force>%s</force>
                          </v2:fetchOperation>
                       </soapenv:Body>
                    </soapenv:Envelope>
                """ % (
                username, password, package, partner.txtype or '',partner.swref or '',partner.force or '0')
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                raise Warning(_('502 Bad Gateway'))
            responsepayload = False
            data = {}
            for node in response_string.iter():
                if node.tag == 'status':
                    data.update({'status':node.text})
                    partner.name = node.text
                if node.tag == 'feedbackType':
                    data.update({'feedback_type': node.text})
                    partner.f_type = node.text
                if node.tag == 'feedbackVersion':
                    data.update({'feedback_version': node.text})
                    partner.f_version = node.text
                if node.tag == 'moreFiles':
                    data.update({'morefiles': int(node.text)})
                    partner.morefiles = node.text
                if node.tag == 'originalSwref':
                    id = False
                    if node.text:
                        id = self.env['mediswitch.submit.claim'].search([('switch_reference','=',node.text)], limit=1)
                        if id:
                            partner.invoice_id = id.invoice_id.id
                            id.invoice_id.user_ref = id.switch_reference
                            invoice = id.invoice_id
                    data.update({'origial_swref': node.text,'claim_ref_id':id.id if id else False})
                    partner.originalswref = node.text
                if node.tag == 'originalUserRef':
                    data.update({'original_userref': node.text})
                    partner.originaluserref = node.text
                if node.tag == 'originalDataSetId':
                    data.update({'original_dataset_id': node.text})
                    partner.originaldatasetid = node.text
                if node.tag == 'fileName':
                    data.update({'filename': node.text})
                    partner.filename = node.text
                if node.tag == 'fileDate':
                    partner.filedate = node.text
                if node.tag == 'responsePayload':
                    data.update({'response_payload': node.text})
                    partner.responsepayload = node.text
                    responsepayload = node.text
            self.env['mediswitch.fetch.claim'].create(data)
            if responsepayload and id:
                claim_status_lines = []
                lines = responsepayload.split("\n")
                strings = ("Invalid Missing", "Invalid")
                if any(s in lines[0] for s in strings):
                    raise Warning(_(lines[0]))
                if lines and lines[0] and lines[0].startswith('H'):
                    flag = 0
                    balance_price = 0
                    approved_price = 0
                    total_approved_price = 0
                    list1 = []
                    number = 0
                    for line in lines:
                        split_line = line.split("|")
                        if line.startswith('S'):
                            if int(line.split("|")[5]) >= 0:
                                flag = 1
                        if line.startswith('P') and flag == 1:
                            id.invoice_id.claim_level_mediswitch_status = split_line[13]
                        if line.startswith('T') and flag == 1:
                            message1= invoice.claim_messages(split_line[14])
                            claim_status_lines.append(message1)
                        if line.startswith('Z'):
                            if split_line[18]:
                                approved_price = int(split_line[18]) / 100
                                total_approved_price += approved_price
                            if split_line[16]:
                                balance_price = int(split_line[16]) / 100
                            list1.append({'approve': approved_price, 'balance': balance_price})
                    if total_approved_price:
                        invoice.action_invoice_open()
                        vals = {}
                        if partner.company_id.do_payment:
                            accquire_id = self.env['payment.acquirer'].search([('name','=','Mediswitch Payment Gateway'),('company_id','=',self.env.user.company_id.id)])
                            vals.update({
                                'amount': total_approved_price,
                                'currency_id': self.env.user.company_id.currency_id.id,
                                'partner_id': invoice.partner_id.id,
                                'invoice_ids': [(6, 0, invoice.ids)],
                                'state': 'done',
                            })
                            vals['acquirer_id'] = accquire_id.id
                            vals['reference'] = invoice.name
                            transaction = self.env['payment.transaction'].create(vals)
                            # journal_id = request.env['account.journal'].sudo().search(
                            #     [('type', '=', 'bank'),('company_id','=',self.env.user.company_id.id)], limit=1)
                            if not invoice.company_id.journal_id:
                                raise Warning(_("Please Select Journal for Mediswitch Payment...!!"))
                            payment_method_id = self.env['account.payment.method'].search(
                                [('name', '=', 'Manual'), ('payment_type', '=', 'outbound')], limit=1)
                            payments = {
                                'payment_type': 'inbound',
                                'partner_type': 'customer',
                                'partner_id': invoice.partner_id.id,
                                'amount': total_approved_price,
                                'journal_id': invoice.company_id.journal_id.id,
                                'payment_date': date.today(),
                                'communication': invoice.number,
                                'payment_method_id': payment_method_id.id,
                                'invoice_ids': [(4, invoice.id)],
                                'payment_transaction_id': transaction.id,
                            }
                            payment_id = self.env['account.payment'].create(payments)
                            payment_id.post()
                    for each in invoice.invoice_line_ids:
                        if len(claim_status_lines) > 0 and claim_status_lines[number]:
                            status = claim_status_lines[number]
                        else:
                            status = ""
                        if list1:
                            each.approved_amount = list1[number].get('approve')
                            each.balance_amount = list1[number].get('balance')
                        each.claim_status = status
                        number += 1
            return {
                'name': 'Global Fetch Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'global.fetch.claim',
                'res_id': partner.id,
                'view_id': self.env.ref('mediswitch_integration.global_fetch_claims_form_view_1').id,
                'view_mode': 'form',
                'target': 'new',
            }

    @api.model
    def global_fetch_cron(self):
        morefiles = 1
        company_id = self.env.user.company_id
        # data = self.env['speacial.charcters'].echo_operation(company_id.id)
        # if data[1] == 'OK':
        #     url = data[0]
        # else:
        #     raise Warning(_('Mediswitch Gateway Busy!!'))
        cmp_id = self.env['res.company'].browse(company_id.id)

        if cmp_id.select_url == 'production_url':
            url = cmp_id.production_url
        elif cmp_id.select_url == 'fail_over_url':
            url = cmp_id.production_url2
        else:
            raise Warning(_('Mediswitch Gateway Offline!!'))

        if company_id.for_what == 'test':
            username = company_id.user_name_test
            password = company_id.password_test
            package = company_id.package_test
        else:
            username = company_id.user_name_production
            password = company_id.password_production
            package = company_id.package_production
        while morefiles >= 1:
            xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                           <soapenv:Header/>
                           <soapenv:Body>
                              <v2:fetchOperation>
                                 <user>%s</user>
                                 <passwd>%s</passwd>
                                 <package>%s</package>
                                 <txType>%s</txType>
                                 <swref>%s</swref>
                                 <force>%s</force>
                              </v2:fetchOperation>
                           </soapenv:Body>
                        </soapenv:Envelope>
                                            """ % (
                username, password, package, '', '', '0')
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                _logger.error(_('502 Bad Gateway'))
            responsepayload = False
            data = {}
            for node in response_string.iter():
                if node.tag == 'status':
                    data.update({'status': node.text})
                if node.tag == 'feedbackType':
                    data.update({'feedback_type': node.text})
                if node.tag == 'feedbackVersion':
                    data.update({'feedback_version': node.text})
                if node.tag == 'moreFiles':
                    morefiles = int(node.text)
                    data.update({'morefiles': int(node.text)})
                if node.tag == 'originalSwref':
                    id = False
                    if node.text:
                        id = self.env['mediswitch.submit.claim'].search([('switch_reference', '=', node.text)])
                        if id:
                            id.invoice_id.user_ref = id.switch_reference
                            invoice = id.invoice_id
                    data.update({'origial_swref': node.text, 'claim_ref_id': id.id if id else False})
                if node.tag == 'originalUserRef':
                    data.update({'original_userref': node.text})
                if node.tag == 'originalDataSetId':
                    data.update({'original_dataset_id': node.text})
                if node.tag == 'fileName':
                    data.update({'filename': node.text})
                if node.tag == 'responsePayload':
                    data.update({'response_payload': node.text})
                    responsepayload = node.text
            self.env['mediswitch.fetch.claim'].create(data)
            if responsepayload and id:
                claim_status_lines = []
                lines = responsepayload.split("\n")
                strings = ("Invalid Missing", "Invalid")
                if any(s in lines[0] for s in strings):
                    raise Warning(_(lines[0]))
                if lines and lines[0] and lines[0].startswith('H'):
                    flag = 0
                    balance_price = 0
                    approved_price = 0
                    total_approved_price = 0
                    list1 = []
                    number = 0
                    for line in lines:
                        split_line = line.split("|")
                        if line.startswith('S') and split_line[0] == 'S':
                            if int(line.split("|")[5]) >= 0:
                                flag = 1
                        if line.startswith('P') and split_line[0] == 'P' and flag == 1:
                            id.invoice_id.claim_level_mediswitch_status = split_line[13]
                        if line.startswith('T') and split_line[0] == 'T' and flag == 1:
                            message1 = self.claim_messages(split_line[14])
                            claim_status_lines.append(message1)
                        if line.startswith('Z') and split_line[0] == 'Z' and flag == 1:
                            if split_line[18]:
                                approved_price = int(split_line[18]) / 100
                                total_approved_price += approved_price
                            if split_line[16]:
                                balance_price = int(split_line[16]) / 100
                            list1.append({'approve': approved_price, 'balance': balance_price})
                    if total_approved_price:
                        invoice.action_invoice_open()
                        vals = {}
                        if company_id.do_payment:
                            accquire_id = self.env['payment.acquirer'].search([('name','=','Mediswitch Payment Gateway'),('company_id','=',self.env.user.company_id.id)])
                            vals.update({
                                'amount': total_approved_price,
                                'currency_id': self.env.user.company_id.currency_id.id,
                                'partner_id': invoice.partner_id.id,
                                'invoice_ids': [(6, 0, invoice.ids)],
                                'state': 'done',
                            })
                            vals['acquirer_id'] = accquire_id.id
                            vals['reference'] = invoice.name
                            transaction = self.env['payment.transaction'].create(vals)
                            # journal_id = request.env['account.journal'].sudo().search(
                            #     [('type', '=', 'bank'),('company_id','=',self.env.user.company_id.id)], limit=1)
                            if not invoice.company_id.journal_id:
                                raise Warning(_("Please Select Journal for Mediswitch Payment...!!"))
                            payment_method_id = self.env['account.payment.method'].search(
                                [('name', '=', 'Manual'), ('payment_type', '=', 'outbound')], limit=1)
                            payments = {
                                'payment_type': 'inbound',
                                'partner_type': 'customer',
                                'partner_id': invoice.partner_id.id,
                                'amount': total_approved_price,
                                'journal_id': invoice.company_id.journal_id.id,
                                'payment_date': date.today(),
                                'communication': invoice.number,
                                'payment_method_id': payment_method_id.id,
                                'invoice_ids': [(4, invoice.id)],
                                'payment_transaction_id': transaction.id,
                            }
                            payment_id = self.env['account.payment'].create(payments)
                            payment_id.post()
                    invoice.response_description = ''
                    for each in invoice.invoice_line_ids:
                        if len(claim_status_lines) > 0 and claim_status_lines[number]:
                            status = claim_status_lines[number]
                        else:
                            status = ""
                        if list1:
                            each.approved_amount = list1[number].get('approve')
                            each.balance_amount = list1[number].get('balance')
                        each.claim_status = status
                        number += 1



    def claim_messages(self, no1):
        message_1 = ''
        if no1 and str(no1) in ['01', '02', '03', '04', '05', '06','07']:
            if str(no1) == '01':
                message_1 = 'Claim Accepted for delivery'
            elif str(no1) == '02':
                message_1 = 'Claim Accepted for processing'
            elif str(no1) == '03':
                message_1 = 'Claim Rejected'
            elif str(no1) == '04':
                message_1 = 'Claim Approved for Payment'
            elif str(no1) == '05':
                message_1 = 'Claim Approved for Part Payment'
            elif str(no1) == '06':
                message_1 = 'Claim Reversal Accepted'
            elif str(no1) == '07':
                message_1 = 'Claim Reversal Rejected'
        return message_1


class MarkToMsv(models.Model):
    _name = "mark.msv"
    _description = "To mark all the customer for msv later"

    name = fields.Char(readonly=1)

    def mark_to_msv(self):
        for id in self.env.context.get('active_ids'):
            id = self.env['res.partner'].browse(id)
            if not id.msv_later_button and id.medical_aid_id.msv_allowed:
                id.msv_later_button = True

class RemoveMsv(models.Model):
    _name = "remove.mark.msv"
    _description = "To Remove all the customer from msv later"

    name = fields.Char(readonly=1)

    def remove_msv(self):
        for id in self.env.context.get('active_ids'):
            id = self.env['res.partner'].browse(id)
            if id.msv_later_button:
                id.msv_later_button = False


class BulkMsv(models.Model):
    _name = 'bulk.msv'
    _description = "To check the customer for msv in bulk"

    name = fields.Char(readonly=1)

    @api.multi
    def bulk_msv(self):
        current_date_time = datetime.now().strftime("%Y%m%d%H%M")
        ir_config_obj = self.env['ir.config_parameter']
        practice_number = ir_config_obj.sudo().get_param('mediswitch_integration.practice_number')
        practice_name = ir_config_obj.sudo().get_param('mediswitch_integration.practice_name')
        for partner in self.env['res.partner'].search([('msv_later_button','=', True),('customer','=',True)]):
            practice_number = partner.company_id.practice_number
            practice_name = partner.company_id.practice_name
            if not partner.medical_aid_id.msv_allowed:
                wizard_data.update({'name':'Sorry, MSV is not enabled for the patients Medical Aid.'})
            if not partner.surname:
                wizard_data.update({'name':"Member Surname is missing"})
            if not partner.name:
                wizard_data.update({'name':"Member Name is missing"})
            if not partner.individual_internal_ref:
                wizard_data.update({'name':"Member Internal Ref is missing"})
            paylod = """H|%s|%s|%s|
S|%s|%s|%s|%s|
M|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|
E|%s|%s|\n""" % (
                # Header (Start of Message) Record – Type ‘H’
                partner.id or '', 121, 'TOMS:2',
                # Service Provider Record – Type ‘S’
                current_date_time, practice_number or '', practice_name or '', '',
                # Member Record – Type ‘M’
                '1', '',
                partner.title.name or 'N',
                partner.initials or 'N',
                partner.surname or '',
                partner.name or '', partner.medical_aid_no or '', 'N', '',
                partner.medical_aid_id.destination_code or '',
                # Footer Record – Type ‘E’
                partner.id or '', '1',
            )
            paylod = self.env['speacial.charcters'].speacial_char_escape(paylod)
            partner.write({'payload_description': paylod})
            if partner.company_id:
                cmp_id = partner.company_id.id
            else:
                cmp_id = self.env.user.company_id.id
            # data = self.env['speacial.charcters'].echo_operation(cmp_id)
            # cmp_id = self.env['speacial.charcters'].browse(cmp_id)
            # if data[1] == 'OK':
            #     url = data[0]
            # else:
            #     raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit'))
            cmp_id = self.env['res.company'].browse(cmp_id)

            if cmp_id.select_url == 'production_url':
                url = cmp_id.production_url
            elif cmp_id.select_url == 'fail_over_url':
                url = cmp_id.production_url2
            else:
                raise Warning(_('Mediswitch Gateway Offline!!'))

            if cmp_id.for_what == 'test':
                username = cmp_id.user_name_test
                password = cmp_id.password_test
                package = cmp_id.package_test
                mode = cmp_id.mode_test
            else:
                username = cmp_id.user_name_production
                password = cmp_id.password_production
                package = cmp_id.package_production
                mode = cmp_id.mode_production
            xml1 = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v2="http://gateway.switchonline.co.za/MediswitchGateway/v2">
                                   <soapenv:Header/>
                                   <soapenv:Body>
                                      <v2:submitOperation>
                                         <user>%s</user>
                                         <passwd>%s</passwd>
                                         <package>%s</package>
                                         <destination>%s</destination>
                                         <txType>301</txType>
                                         <mode>%s</mode>
                                         <txVersion>121</txVersion>
                                         <userRef>%s</userRef>
                                         <payload>%s</payload>
                                      </v2:submitOperation>
                                   </soapenv:Body>
                                </soapenv:Envelope>
                                """ % (
                username, password, package, partner.medical_aid_id.destination_code, mode,
                partner.id, paylod)
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit'))
            responsepayload = False
            wizard_data = {'partner_id': partner.id, 'msv_type': 'msv', 'request_payload': paylod}
            for node in response_string.iter():
                if node.tag == 'responsePayload':
                    if node.text and node.text == 'Switch System Error':
                        raise Warning(_('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit'))
                    responsepayload = node.text
            list1 = []
            msv_status = ''
            if responsepayload:
                wizard_data.update({"response_payload": responsepayload})
                lines = responsepayload.split("\n")
                is_valid = False
                strings = ("Invalid Missing", "Invalid")
                if any(s in lines[0] for s in strings):
                    wizard_data.update({'name':lines[0]})
                if lines and lines[0] and lines[0].startswith('H'):
                    for line in lines:
                        if line.startswith('RV'):
                            split_line = line.split("|")
                            if split_line[1] == '01':
                                error_text = split_line[5]
                                is_valid = True
                if not is_valid:
                    if lines and lines[0] and lines[0].startswith('H'):
                        for line in lines:
                            effective_date = False
                            termination_date = False
                            if line.startswith('P'):
                                split_line = line.split("|")
                                msv_status = split_line[10] or ''
                                if split_line[5] and len(split_line[5]) == 8:

                                    dob = date(year=int(split_line[5][0:4]), month=int(split_line[5][4:6]),
                                               day=int(split_line[5][6:9]))
                                if split_line[8] and len(split_line[8]) == 8:
                                    effective_date = date(year=int(split_line[8][0:4]), month=int(split_line[8][4:6]),
                                                          day=int(split_line[8][6:9]))
                                if split_line[9] and len(split_line[9]) == 8:
                                    termination_date = date(year=int(split_line[9][0:4]), month=int(split_line[9][4:6]),
                                                            day=int(split_line[9][6:9]))
                                list1.append({
                                    'name':split_line[4] or False,
                                    'surname':split_line[2] or False,
                                    'dependent_code':split_line[1] or False,
                                    'initials':split_line[3] or False,
                                    'dob':dob or False,
                                    'id_number':split_line[6] or False,
                                    'gender':split_line[7] or False,
                                    'effective_date':effective_date,
                                    'termination_date':termination_date,
                                    'status_code_description':split_line[10] or False,
                                })
                            if line.startswith('M'):
                                split_line = line.split("|")
                                wizard_data.update({
                                    'membership_number': split_line[4] or False,
                                    'name': split_line[12] or False,
                                    'plan_name': split_line[15] or False,
                                    'option_name': split_line[15] or False,
                                    'current_membership_number': partner.medical_aid_no,
                                    'current_id_number': partner.id_number,
                                })
                            if line.startswith('RV'):
                                validation_code = False
                                split_line = line.split("|")
                                if split_line[6] and split_line[6] == '01':
                                    validation_code = '01 - CDV (Check Digit Verification)'
                                elif split_line[6] and split_line[6] == '02':
                                    validation_code = '02 - CHF (Card Holder File)'
                                elif split_line[6] and split_line[6] == '03':
                                    validation_code = '03 - SO (Switch out to Medical Scheme)'
                                wizard_data.update({
                                    'validation_code': validation_code or False,
                                    'disclaimer': split_line[3] or False,
                                    'status_code_description': split_line[5] or False,
                                })
                    partner.msv_later_button = False
                else:
                    wizard_data.update({'name':error_text})
            wizard_id = self.env['msv.response'].create(wizard_data)
            if list1:
                for data in list1:
                    self.env['msv.members'].create(data.update({'msv_response_id':wizard_id.id}))
            partner.msv_latest_date = wizard_id.create_date
            partner.msv_status = msv_status or ''
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class MsvMembers(models.Model):
    _name = "msv.members"
    _description = "To check the customer is MSV or not."

    name = fields.Char(string="Name")
    surname = fields.Char(string="Surname")
    dependent_code = fields.Char(string="Dependant Code")
    initials = fields.Char(string="Initials")
    dob = fields.Date(string="DOB")
    id_number = fields.Char(string="Id/Passport Number")
    gender = fields.Char(string="Gender")
    effective_date = fields.Date(string="Effective Date")
    termination_date = fields.Date(string="Termination Date")
    status_code_description = fields.Char(string="status Code Description")
    msv_response_id = fields.Many2one("msv.response",string="Msv response")
    operations = fields.Selection([('search', 'Search'), ('create', 'Create'), ('update', 'Update')],
                                  string="Operations", default="search")
    search_id = fields.Many2one("res.partner", string="Member")
    current_membership_number = fields.Char(string="Current Membership number")
    current_id_number = fields.Char(string="Current ID number")

    def search_record(self):
        if self.id_number:
            record = self.env['res.partner'].search([('id_number', '=', self.id_number)], limit=1)
            if record:
                self.operations = 'update'
                self.search_id = record.id
            elif not record and self.dob and self.surname:
                record = self.env['res.partner'].search([('birth_date', '=', self.dob), ('surname', '=', self.surname)],
                                                        limit=1)
                if record:
                    self.operations = 'update'
                    self.search_id = record.id
                else:
                    self.operations = 'create'
        elif not self.id_number and self.dob and self.surname:
            record = self.env['res.partner'].search([('birth_date', '=', self.dob), ('surname', '=', self.surname)], limit=1)
            if record:
                self.operations = 'update'
                self.search_id = record.id
            else:
                self.operations = 'create'
        else:
            self.operations = 'create'
        if self.env.context.get('plan_id'):
            return {
                'name': 'Msv Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'msv.response',
                'res_id': self.msv_response_id.id,
                'view_id': self.env.ref('mediswitch_integration.form_view_for_msv_response1').id,
                'view_mode': 'form',
                'target': 'new',
            }

    def update_record(self):
        medical_detail = self.env['res.partner'].search([('name', 'ilike', self.msv_response_id.name)], limit=1)

        plan_detail = self.env['medical.aid.plan'].search([('name', 'ilike', self.msv_response_id.plan_name),
                                                           ('medical_aid_id', '=', medical_detail.id)], limit=1)
        option_detail = self.env['medical.aid.plan'].search([('name', 'ilike', self.msv_response_id.option_name),
                                                         ('medical_aid_id', '=', medical_detail.id)], limit=1)
        data = {
            'name': self.name.title() + ' ' + self.surname.title(),
            'first_name': self.name.title(),
            'surname': self.surname.title(),
            'initials': self.initials,
            'dependent_code': self.dependent_code,
            'birth_date': self.dob,
            'id_number': self.id_number,
            'gender': self.gender.lower(),
            'medical_aid_id': medical_detail.id if medical_detail else self.search_id.medical_aid_id.id,
            'option_id': plan_detail.id if plan_detail else self.search_id.option_id.id,
            'plan_option_id': option_detail.id if option_detail else self.search_id.plan_option_id.id,
        }
        if self.search_id:
            if self.msv_response_id.membership_number:
                self.search_id.medical_aid_no = self.msv_response_id.membership_number
        self.search_id.update(data)
        if self.env.context.get('plan_id'):
            return {
                'name': 'Msv Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'msv.response',
                'res_id': self.msv_response_id.id,
                'view_id': self.env.ref('mediswitch_integration.form_view_for_msv_response1').id,
                'view_mode': 'form',
                'target': 'new',
            }

    def create_record(self):
        medical_detail = self.env['res.partner'].search([('name', 'ilike', self.msv_response_id.name)], limit=1)

        plan_detail = self.env['medical.aid.plan'].search([('name', 'ilike', self.msv_response_id.plan_name),
                                                           ('medical_aid_id', '=', medical_detail.id)], limit=1)
        option_detail = self.env['medical.aid.plan'].search([('name', 'ilike', self.msv_response_id.option_name),
                                                             ('medical_aid_id', '=', medical_detail.id)], limit=1)
        data = {
            'name': self.name.title() + ' ' + self.surname.title(),
            'first_name': self.name.title(),
            'surname': self.surname.title(),
            'initials': self.initials,
            'dependent_code': self.dependent_code,
            'birth_date': self.dob,
            'id_number': self.id_number,
            'gender': self.gender.lower(),
            'medical_aid_id': medical_detail.id if medical_detail else self.search_id.medical_aid_id.id,
            'option_id': plan_detail.id if plan_detail else self.search_id.option_id.id,
            'plan_option_id': option_detail.id if option_detail else self.search_id.plan_option_id.id,
        }
        code = ['0','00']
        if self.dependent_code in code:
            parent_id = self.env['res.partner'].create(data)
            self.search_id = parent_id.id
            self.operations = 'update'
        else:
            parent_id = self.search([('msv_response_id','=',self.msv_response_id.id),('dependent_code','in',code)],limit=1)
            if not parent_id:
                parent_id = self.search(
                    [('msv_response_id', '=', self.msv_response_id.id), ('dependent_code', '<', self.dependent_code)],
                    limit=1)
            if parent_id.search_id and parent_id:
                data.update({'parent_id':parent_id.search_id.id})
                self.env['res.partner'].create(data)
                self.operations = 'update'
            else:
                data1 = {
                    'name': self.name + ' ' + self.surname,
                    'first_name': parent_id.name,
                    'surname': parent_id.surname,
                    'initials': parent_id.initials,
                    'dependent_code': parent_id.dependent_code,
                    'birth_date': parent_id.dob,
                    'id_number': parent_id.id_number,
                    'gender': parent_id.gender.lower(),
                    'customer': True,
                    'medical_aid_id': medical_detail.id if medical_detail else self.search_id.medical_aid_id.id,
                    'option_id': plan_detail.id if plan_detail else self.search_id.option_id.id,
                    'plan_option_id': option_detail.id if option_detail else self.search_id.plan_option_id.id,
                }
                id = self.env['res.partner'].create(data1)
                parent_id.search_id = id.id
                self.operations = 'update'
                data.update({'parent_id': id.id})
                self.env['res.partner'].create(data)
        if self.env.context.get('plan_id'):
            return {
                'name': 'Msv Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'msv.response',
                'res_id': self.msv_response_id.id,
                'view_id': self.env.ref('mediswitch_integration.form_view_for_msv_response1').id,
                'view_mode': 'form',
                'target': 'new',
            }
