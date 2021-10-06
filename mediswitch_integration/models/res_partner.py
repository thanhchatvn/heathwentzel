from odoo import models, api, fields, _
from datetime import datetime,date
from ast import literal_eval
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError, ValidationError, Warning, MissingError
import requests
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    payload_description = fields.Text()


    @api.multi
    def submit_msv(self):
        # _logger.info("\n\n\n -------------Start The Method the payload generation part----------- %s",datetime.today().time())
        current_date_time = datetime.now().strftime("%Y%m%d%H%M")
        for partner in self:
            practice_number = partner.company_id.practice_number
            practice_name = partner.company_id.practice_name
            if not partner.medical_aid_id.msv_allowed:
                raise Warning(_('Sorry, MSV is not enabled for the patients Medical Aid.'))
            if not partner.surname:
                raise MissingError("Member Surname is missing")
            if not partner.name:
                raise MissingError("Member Name is missing")
            if not partner.individual_internal_ref:
                raise MissingError("Member Internal Ref is missing")
            if not partner.medical_aid_id.destination_code:
                raise MissingError("Destination code is missing")
            birthday = partner.birth_date and partner.birth_date.strftime("%Y%m%d")
            if partner.gender:
                gender = partner.gender.upper()
            else:
                raise MissingError("Gender is missing")
            _logger.info("\n\n\n\n\n -----------Finish The 1st Part(Checking destination code and etc.....)")
            paylod = """H|%s|%s|%s|
S|%s|%s|%s|%s|
M|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|
E|%s|%s|\n""" % (
                # P|%s|%s|%s|%s|%s|%s|%s|%s|
                # Header (Start of Message) Record – Type ‘H’
                partner.id or '', 121, 'TOMS:2',
                # Service Provider Record – Type ‘S’
                current_date_time, practice_number or '', practice_name or '', '',
                # Member Record – Type ‘M’
                '1', '',
                partner.title.name[0:5] if partner.title else 'N',
                partner.initials or 'N',
                partner.surname[0:30] if partner.surname else '',
                partner.name[0:30] if partner.name else '', partner.medical_aid_no or '', 'N', '',
                partner.medical_aid_id.destination_code or '',
                # Patient Record – Type ‘P’
                # partner.dependent_code or '', partner.surname or '',
                # partner.initials or '',
                # partner.name or '', birthday or '',
                # gender or '', '',
                # partner.id_number or '',
                # Footer Record – Type ‘E’
                partner.id or '', '1',
            )
            paylod = self.env['speacial.charcters'].speacial_char_escape(paylod)
            partner.write({'payload_description': paylod})
            _logger.info(
                "\n\n\n\n\n ----------Finish The 2nd Part(Creating the Payload and replace the speacial Character.....)")
            if partner.company_id:
                cmp_id = partner.company_id.id
            else:
                cmp_id = self.env.user.company_id.id
            # data = self.env['speacial.charcters'].echo_operation(cmp_id)
            cmp_id = self.env['res.company'].browse(cmp_id)

            if cmp_id.select_url == 'production_url':
                url = cmp_id.production_url
            elif cmp_id.select_url == 'fail_over_url':
                url = cmp_id.production_url2
            else:
                raise Warning(_('Mediswitch Gateway Offline!!'))

            _logger.info(
                "\n\n\n\n\n -----------Finish The 3rd Part(Check with mediswitch that which url is working.....)")
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
            # _logger.info("\n\n\n -------------End the payload generation part----------- %s", datetime.today().time())
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                # _logger.info("\n\n\n ---------Request Send to the Mediswitch------- %s", datetime.today().time())
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)

                _logger.info(
                    "\n\n\n\n\n -----------Finish The 4th Part(Send request to mediswitch and take response back.....)")
            except Exception as e:
                raise Warning(_('502 Bad Gateway'))
            responsepayload = False
            list1 = []
            wizard_data = {'partner_id': partner.id, 'msv_type': 'msv', 'request_payload': paylod}
            for node in response_string.iter():
                print("\n\n\n response_string--->", node.tag, node.text)
                if node.tag in ['faultstring', 'message']:
                    print('\n\nerror-----------------1')
                    raise Warning(_(
                        'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n" + "(" + node.text + ")"))
                print('\n\nerror-----------------2')
                if node.tag == 'responsePayload':
                    if node.text and node.text == 'Switch System Error':
                        raise Warning(
                            _('email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n" + "(" + node.text + ")"))
                    responsepayload = node.text
            # _logger.info("\n\n\n\n\n\n\n ---------Start Processing the Payload------- %s", datetime.today().time())
            if responsepayload:
                wizard_data.update({"response_payload": responsepayload})
                lines = responsepayload.split("\n")
                strings = ("Invalid Missing", "Invalid")
                if any(s in lines[0] for s in strings):
                    raise Warning(_(lines[0]))
                if lines and lines[0] and lines[0].startswith('H'):
                    for line in lines:
                        if line.startswith('RV'):
                            split_line = line.split("|")
                            if split_line[1] == '01':
                                wizard_data.update({'membership_status': "Invalid"})
                            elif split_line[1] == '02':
                                wizard_data.update({'membership_status': "Valid"})
                            elif split_line[1] == '02':
                                wizard_data.update({'membership_status': "Additional Information required"})
                if lines and lines[0] and lines[0].startswith('H'):
                    for line in lines:
                        effective_date = False
                        termination_date = False
                        if line.startswith('P'):
                            split_line = line.split("|")
                            partner.msv_status = split_line[10]
                            if split_line[5]:
                                dob = date(year=int(split_line[5][0:4]), month=int(split_line[5][4:6]),
                                           day=int(split_line[5][6:9]))
                            if split_line[8]:
                                effective_date = date(year=int(split_line[8][0:4]), month=int(split_line[8][4:6]),
                                                      day=int(split_line[8][6:9]))
                            if split_line[9]:
                                termination_date = date(year=int(split_line[9][0:4]), month=int(split_line[9][4:6]),
                                                        day=int(split_line[9][6:9]))
                            list1.append({
                                'name': split_line[4] or False,
                                'surname': split_line[2] or False,
                                'dependent_code': split_line[1] or False,
                                'initials': split_line[3] or False,
                                'dob': dob or False,
                                'id_number': split_line[6] or False,
                                'gender': split_line[7] or False,
                                'effective_date': effective_date,
                                'termination_date': termination_date,
                                'status_code_description': split_line[10] or False,
                            })
                        if line.startswith('M'):
                            split_line = line.split("|")
                            wizard_data.update({
                                'membership_number': split_line[4],
                                'name': split_line[12],
                                'plan_name': split_line[15],
                                'option_name': split_line[15],
                                'current_membership_number': partner.medical_aid_no,
                                'current_id_number': partner.id_number,
                            })
                        if line.startswith('RV'):
                            validation_code = False
                            split_line = line.split("|")
                            if split_line[6] and split_line[6] == '01':
                                validation_code = 'Check Digit Verification'
                            elif split_line[6] and split_line[6] == '02':
                                validation_code = 'Card Holder File'
                            elif split_line[6] and split_line[6] == '03':
                                validation_code = 'Switch out to Medical Scheme'
                            wizard_data.update({
                                'validation_code': validation_code or False,
                                'disclaimer': split_line[3] or False,
                                'status_code_description': split_line[5] or False,
                            })
            partner.msv_later_button = False
            wizard_id = self.env['msv.response'].create(wizard_data)
            if list1:
                for data in list1:
                    data.update({'msv_response_id': wizard_id.id})
                    self.env['msv.members'].create(data)
            partner.msv_latest_date = wizard_id.create_date
            _logger.info("\n\n\n\n\n -----------Finish The 5th Part(Payload Processing part.....)")
            # _logger.info("\n\n\n\n\n\n\n ---------Ending Processing the Payload------- %s", datetime.today().time())
            return {
                'name': 'Msv Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'msv.response',
                'res_id': wizard_id.id,
                'view_id': self.env.ref('mediswitch_integration.form_view_for_msv_response1').id,
                'view_mode': 'form',
                'target': 'new',
            }

    @api.multi
    def action_view_partner_msv(self):
        self.ensure_one()
        action = self.env.ref('mediswitch_integration.action_partner_msv1').read()[0]
        action['domain'] = [('partner_id', '=', self.id)]
        return action

    exam_count = fields.Integer(string="Exam Count", compute="calculate_exam_count")

    @api.model
    def calculate_exam_count(self):
        for each in self:
            count = self.env['clinical.examination'].search_count([('partner_id', '=', each.id)])
            each.exam_count = count

    @api.multi
    def open_partner_exam(self):
        return {
            'name': 'Examination',
            'type': 'ir.actions.act_window',
            'res_model': 'clinical.examination',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id), ('active', '=', True)]
        }

    @api.multi
    def action_benefit_check_partner(self):
        view_id = self.env['response.error.wizard'].sudo().create({'mediswitch_type':'Benefit'})
        return {
            'name': 'Response Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'response.error.wizard',
            'res_id': view_id.id,
            'view_id': self.env.ref('mediswitch_integration.response_error_wizard').id,
            'view_mode': 'form',
            'target': 'new',
        }

class MsvResponse(models.Model):
    _name = "msv.response"
    _description = "Response from MSV to Mediswitch"
    _order = 'create_date desc'
    #Member Details
    msv_type = fields.Selection([('msv', 'Msv'), ('id_msv', 'Id Msv'), ('sur_dob_msv', 'Surname Dob Msv')], string="Msv Type")
    partner_id = fields.Many2one("res.partner")
    membership_number = fields.Char(string="Membership Number")
    membership_status = fields.Char(string="Membership Status")
    name = fields.Char(string="Medical Aid")
    plan_name = fields.Char(string="Plan")
    option_name = fields.Char(string="Option")
    # Response Details
    status_code_description = fields.Char(string="Result Description", help="Patient’s Medical Scheme Status Code and Description")
    validation_code = fields.Char(string="Validation Status")
    responding_party = fields.Char(string="Responding Party")
    disclaimer = fields.Char(string="Disclaimer")
    request_payload = fields.Text()
    response_payload = fields.Text()
    msv_members_ids = fields.One2many("msv.members",'msv_response_id')
    current_membership_number = fields.Char(string="Current Membership number")
    current_id_number = fields.Char(string="Current ID number")


