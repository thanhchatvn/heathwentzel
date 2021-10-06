from odoo import fields, models, api, _
from suds.wsse import Security, UsernameToken
from suds.client import Client
from datetime import datetime, date, timedelta
from odoo.http import request
from odoo.exceptions import MissingError,Warning
import xml.etree.ElementTree as ET
import time
import json
import requests
import pytz



class calendar_event(models.Model):
    _inherit = 'calendar.event'
    _rec_name = 'meeting_subject_id'

    # start_date_check = fields.Datetime()
    # float_duration = fields.Float()

    @api.model
    def scheduler_send_sms_reminder(self):
        current_time = datetime.now()
        end_time = datetime.now() + timedelta(hours=24)
        event_ids = self.search([('start_datetime', '>=', current_time), ('start_datetime', '<=', end_time),
                                 ('reminder_sms', '=', True), ('sms_reminder_sent', '=', False)])
        sms_template_id = self.env.ref('TOMS.appointment_sms_template')
        for event in event_ids:
            if sms_template_id:
                if event.mobile:
                    template_body = "Hello %s \n This is reminder message of your appointment - %s on %s" % (
                        event.customer_id.name, event.meeting_subject_id.name, event.start_datetime)
                    sms_rendered_content = self.env['sms.template'].render_template(sms_template_id.template_body,
                                                                                    sms_template_id.model_id.model,
                                                                                        event)
                    sms_compose = self.env['sms.compose'].create({
                        'sms_template_id': sms_template_id.id,
                        'from_mobile_id': sms_template_id.from_mobile_verified_id.id,
                        'to_number': event.mobile,
                        'sms_content': sms_rendered_content,
                        'media_id': template_body,
                        'model': self._name,
                        'record_id': event.id
                    })
                    if sms_compose:
                        sms_compose.with_context(from_cron=True).send_entity()
                        event.write({
                            'sms_reminder_sent': True
                            })

    @api.model
    def default_get(self, fields):
        result = super(calendar_event, self).default_get(fields)
        result.update({
            'frontliner_id': self.env.user.id,
            'meeting_subject_id': self.env.ref('TOMS.meeting_subject_spec_exam').id,
        })
        print("\n\n\n self.env.context", self.env.context, result)
        if self.env.context.get('dafault_optometrist_id'):
            result.update({'optometrist_id':int(self.env.context.get('dafault_optometrist_id'))})
        return result

    @api.multi
    def _get_company_location(self):
        company_id = self.env.user.company_id
        location = []
        address_lst = [company_id.name, company_id.street, company_id.street2, company_id.city,
                       company_id.state_id.name, company_id.zip,
                       company_id.country_id.name]
        for each in address_lst:
            if each:
                location.append(each)
        return ", ".join(location)

    customer_id = fields.Many2one('res.partner', string="Customer")
    px_id = fields.Char(related='customer_id.id_number')
    optometrist_id = fields.Many2one('res.users', string="Optometrist")
    home_phone = fields.Char(string="Home Phone", related="customer_id.phone")
    mobile = fields.Char(string="Mobile")
    work_phone = fields.Char(string="Work Phone", related="customer_id.work_phone")
    medical_aid_id = fields.Many2one('res.partner', string="Medical Aid", related="customer_id.medical_aid_id",
                                     store=True)
    option_id = fields.Many2one('medical.aid.plan', string="Plan", related="customer_id.option_id")
    plan_option_id = fields.Many2one('medical.aid.plan.option', string="Option ", domain="[('plan_id','=',option_id)]",
                                     related="customer_id.plan_option_id")
    key_member_id = fields.Many2one('res.partner', string="Key Member")
    key_member = fields.Char(string="Key Member ID")
    reminder_sms = fields.Boolean(string="Reminder SMS", default=True)
    check_details = fields.Boolean(string="Check Details", default=True)
    telesales = fields.Boolean(string="Telesales")
    recall = fields.Boolean(string="Recall")
    present_for_appointment = fields.Boolean(string="Present", readonly=False)
    lost_reason_id = fields.Many2one('crm.lost.reason', 'Lost Reason')
    state = fields.Selection(selection_add=[('cancel', 'cancelled')])
    frontliner_id = fields.Many2one('res.users', string="Frontliner")
    location = fields.Char('Location', states={'done': [('readonly', True)]}, track_visibility='onchange',
                           help="Location of Event", default=_get_company_location)
    meeting_subject_id = fields.Many2one('meeting.subject', string="Meeting Subject ", required=True)
    name = fields.Char(required=False)
    calendar_display_name = fields.Char(compute='_get_display_name')
    sms_reminder_sent = fields.Boolean(string="Sent Reminder")
    exam_count = fields.Integer(string="Exam Count", compute="calculate_exam_count")
    msv_status = fields.Char()
    msv_later = fields.Boolean()
    msv_latest_date = fields.Datetime()
    patient = fields.Many2one('humint.medical.aid.confrimations')
    confrimation = fields.Many2one('humint.medical.aid.confrimations')
    overall_limit = fields.Float(related='confrimation.overall_limit')

    @api.multi
    def get_interval_custom(self, interval, tz=None):
        self.ensure_one()
        date = fields.Datetime.from_string(self.start)
        if tz and interval == '':
            timezone = pytz.timezone(tz or 'UTC')
            date = date.replace(tzinfo=pytz.timezone('UTC')).astimezone(timezone)
            res = str(date).split('+')[0]
            return res

    @api.multi
    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        """ Adapt the value of start_date(time)/stop_date(time) according to start/stop fields and allday. Also, compute
            the duration for not allday meeting ; otherwise the duration is set to zero, since the meeting last all the day.
        """
        for meeting in self:

            if meeting.allday and meeting.start and meeting.stop:
                meeting.start_date = meeting.start.date()
                meeting.start_datetime = False
                meeting.stop_date = meeting.stop.date()
                meeting.stop_datetime = False
                meeting.duration = 0.0
            else:
                meeting.start_date = False
                meeting.start_datetime = meeting.start
                meeting.stop_date = False
                meeting.stop_datetime = meeting.stop
                if meeting.start and meeting.stop:
                    meeting.duration = self._get_duration(meeting.start, meeting.stop)
                else:
                    meeting.duration = 0.5

    @api.model
    def calculate_exam_count(self):
        for each in self:
            count = self.env['clinical.examination'].search_count([('appointment_id', '=', each.id)])
            each.exam_count = count

    @api.onchange("meeting_subject_id")
    def onchnage_meeting_subject(self):
        self.name = self.meeting_subject_id.name

    @api.onchange('msv_latest_date')
    def onchange_start_date(self):
        self.start_datetime = self.msv_latest_date

    @api.onchange('customer_id')
    def on_customer_change(self):
        self.mobile = self.customer_id.mobile
        self.key_member_id = self.customer_id.id
        if self.customer_id.parent_id:
            self.key_member_id = self.customer_id.parent_id.id

    @api.one
    @api.depends('customer_id', 'mobile')
    def _get_display_name(self):
        display_name = ""
        if self.customer_id:
            display_name = self.customer_id.name
        if self.mobile:
            if self.customer_id:
                display_name += " : "
            display_name += self.mobile
        self.calendar_display_name = display_name

    @api.multi
    @api.onchange('optometrist_id')
    def onchange_optometrist(self):
        if self.optometrist_id:
            self.user_id = self.optometrist_id.id
        else:
            self.user_id = self.env.user

    @api.multi
    @api.onchange('customer_id', 'optometrist_id')
    def on_change_customer_id(self):
        self.partner_ids = False
        partner_lst = []
        for each in self.partner_ids:
            if each.id not in partner_lst:
                partner_lst.extend([each.id])
        if self.customer_id:
            partner_lst.extend([self.customer_id.id])
        if self.optometrist_id:
            partner_lst.extend([self.optometrist_id.partner_id.id])
        self.update({'partner_ids': [[6, 0, [each for each in partner_lst]]]})
        if self.customer_id.is_dependent:
            self.key_member_id = self.customer_id.parent_id
            self.key_member = self.customer_id.parent_id.id_number
        else:
            self.key_member_id = False
            self.key_member = False

    @api.model
    def create(self, vals):
        if vals.get('optometrist_id') and vals.get('start_datetime'):
            if any(rec for rec in self.env['calendar.event'].search([('optometrist_id', '=', vals.get('optometrist_id')),
                                                    ('start_datetime', '<=', fields.Datetime.from_string(vals.get('start_datetime'))),
                                                    ('stop_datetime', '>', fields.Datetime.from_string(vals.get('start_datetime')))])):
                raise Warning(_('This appointment clashes with another one for the Optometrist. Please select a different time.'))
        res = super(calendar_event, self).create(vals)
        return res

    @api.multi
    def mark_present(self):
        self.present_for_appointment = True

    @api.multi
    def send_sms_from_appointment(self):
        model_id = self.env['ir.model'].search([('model', '=', self._name)])
        job_sms_template_id = self.env['sms.template'].search([('model_id', '=', model_id.id)])
        if model_id:
            return {
                'name': 'SMS Compose',
                'type': 'ir.actions.act_window',
                'res_model': 'sms.compose',
                'view_id': self.env.ref('sms_frame.sms_compose_view_form').id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {'default_to_number': self.customer_id.mobile,
                            'default_model': self._name,
                            'default_record_id': self.id
                            }
            }

    @api.multi
    def start_examination(self):
        return {
            'name': 'Examination',
            'type': 'ir.actions.act_window',
            'res_model': 'clinical.examination',
            'view_id': self.env.ref('TOMS.clinical_examination_form_view').id,
            'view_type': 'form',
            'view_mode': 'form',
            'context': {'default_partner_id': self.customer_id.id,
                        'default_frontliner_id': self.frontliner_id.id,
                        'default_optometrist_id': self.optometrist_id.id,
                        'defalut_active': True,
                        'default_appointment_id': self.id,
                        'default_medical_aid_confirmation_ids': [(6, 0, [self.patient.id])],
                        'default_state': 'inprogress'
                        }
        }

    @api.multi
    def cancel_appointment(self):
        self.active = False
        return {
            'name': 'Lost Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead.lost',
            'view_id': self.env.ref('TOMS.cancel_appointment_wizard').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def datetime_range(self, start, end, delta):
        current = start
        while current < end:
            yield current
            current += delta

    def getEventList(self, context, **kw):
        event_list = []
        today_start_date = datetime.strptime(
            datetime.strftime(datetime.strptime(context.get('date'), "%Y-%m-%d"), "%Y-%m-%d 00:00:00"),
            '%Y-%m-%d %H:%M:%S')
        today_end_date = datetime.strptime(
            datetime.strftime(datetime.strptime(context.get('date'), "%Y-%m-%d"), "%Y-%m-%d 23:59:59"),
            '%Y-%m-%d %H:%M:%S')
        if self._context.get('tz'):
            tz = pytz.timezone(self._context.get('tz'))
        else:
            if context.get('timezone'):
                tz = pytz.timezone(context.get('timezone'))
            else:
                if self.env.user.tz:
                    tz = pytz.timezone(self.env.user.tz)
                else:
                    tz = pytz.utc
        print("\n\n tz-- get event data->", tz)
        c_time = datetime.now(tz)
        hour_tz = int(str(c_time)[-5:][:2])
        min_tz = int(str(c_time)[-5:][3:])
        sign = str(c_time)[-6][:1]

        for res in self.env.user.optometrist_ids:
            if res.active_roster_view:
                # if sign == '-':
                #     event_start_time = (today_start_date + timedelta(hours=hour_tz, minutes=min_tz))
                #     event_end_time = (today_end_date + timedelta(hours=hour_tz, minutes=min_tz))
                # if sign == '+':
                event_start_time = (today_start_date - timedelta(hours=5, minutes=30))
                event_end_time = (today_end_date - timedelta(hours=5, minutes=30))
                event_ids = self.search(
                    [('start_datetime', '>=', event_start_time), ('start_datetime', '<', event_end_time),
                     ('optometrist_id', '=', res.partner_id.id)])
                if event_ids:
                    for event in event_ids:
                        if event.duration:
                            timez = event.duration
                            result = '{0:02.0f}:{1:02.0f}'.format(*divmod(timez * 60, 60))
                            hours = str(result).split(':')
                            end_time = (event.start + timedelta(hours=int(hours[0]), minutes=int(hours[1])))
                            if sign == '+':
                                start_time = (event.start + timedelta(hours=hour_tz, minutes=min_tz))
                                end_time = (end_time + timedelta(hours=hour_tz, minutes=min_tz))
                            if sign == '-':
                                start_time = (event.start - timedelta(hours=hour_tz, minutes=min_tz))
                                end_time = (end_time - timedelta(hours=hour_tz, minutes=min_tz))
                            event_list.append({
                                'id': event.id,
                                'resourceId': event.optometrist_id.id,
                                'start': str(start_time.date()) + 'T' + str(start_time.time()),
                                'end': str(end_time.date()) + 'T' + str(end_time.time()),
                                'title': (event.meeting_subject_id.name or '') + '\n' + (event.customer_id.name or '') ,
                                'color': event.meeting_subject_id.color or event.optometrist_id.calendar_bg_color,
                                'textColor': event.optometrist_id.calendar_text_color or 'black',
                                'present': event.present_for_appointment,
                            })
                    # else:
                    #     event_list.append({
                    #         'start': str(start_time.date()) + 'T' + str(start_time.time()),
                    #         'end': str(end_time.date()) + 'T' + str(end_time.time()),
                    #         'title': 'Available',
                    #         'color': '#27ae60',
                    #         'textColor': 'black',
                    #         'resourceId': res.partner_id.id,
                    #     })
        # event_list.append({
        #     'id': 15302,
        #     'resourceId': 2,
        #     'start': '2021-05-21T00:40:00',
        #     'end': '2021-05-21T00:60:00',
        #     'title': 'Spec Exam\n',
        #     # 'color': event.meeting_subject_id.color or event.optometrist_id.calendar_bg_color,
        #     # 'textColor': event.optometrist_id.calendar_text_color or 'black',
        #     # 'present': event.present_for_appointment,
        # })
        return event_list

    def timezone(self, context, **kw):
        start_date = datetime.strptime(context.get('start_date'), '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(context.get('end_date'), '%Y-%m-%d %H:%M:%S')
        if context.get('timezone'):
            tz = pytz.timezone(context.get('timezone'))
        else:
            if self.env.user.tz:
                tz = pytz.timezone(self.env.user.tz)
            else:
                tz = pytz.utc

        print("\n\n\n tz timezone--->", tz)
        c_time = datetime.now(tz)
        hour_tz = int(str(c_time)[-5:][:2])
        min_tz = int(str(c_time)[-5:][3:])
        sign = str(c_time)[-6][:1]
        print("\n\n\n hours_tz--->", hour_tz)
        print("\n\n\n hours_tz--->", min_tz)
        if sign == '+':
            start_time = (start_date - timedelta(hours=hour_tz, minutes=min_tz))
            end_time = (end_date - timedelta(hours=hour_tz, minutes=min_tz))
        if sign == '-':
            start_time = (start_date + timedelta(hours=hour_tz, minutes=min_tz))
            end_time = (end_date + timedelta(hours=hour_tz, minutes=min_tz))
        print("n\n\n\n start_time-->", start_time)
        print("n\n\n\n end_time-->", end_time)
        return [start_time, end_time]

    def get_saved_data(self, context, **kw):
        for event in self.browse(context.get('id')):
            if event.duration:
                if self._context.get('tz'):
                    tz = pytz.timezone(self._context.get('tz'))
                else:
                    if context.get('timezone'):
                        tz = pytz.timezone(context.get('timezone'))
                    else:
                        if self.env.user.tz:
                            tz = pytz.timezone(self.env.user.tz)
                        else:
                            tz = pytz.utc
                print("\n\n\n tz saved_data--->", tz)
                c_time = datetime.now(tz)
                hour_tz = int(str(c_time)[-5:][:2])
                min_tz = int(str(c_time)[-5:][3:])
                sign = str(c_time)[-6][:1]

                timez = event.duration
                result = '{0:02.0f}:{1:02.0f}'.format(*divmod(timez * 60, 60))
                hours = str(result).split(':')
                end_time = (event.start + timedelta(hours=int(hours[0]), minutes=int(hours[1])))
                if sign == '+':
                    event_start_time = (event.start + timedelta(hours=hour_tz, minutes=min_tz))
                    event_end_time = (end_time + timedelta(hours=hour_tz, minutes=min_tz))
                if sign == '-':
                    event_start_time = (event.start - timedelta(hours=hour_tz, minutes=min_tz))
                    event_end_time = (end_time - timedelta(hours=hour_tz, minutes=min_tz))
                event_list = {
                    'id': event.id,
                    'resourceId': event.optometrist_id.id,
                    'start': str(event_start_time.date()) + 'T' + str(event_start_time.time()),
                    'end': str(event_end_time.date()) + 'T' + str(event_end_time.time()),
                    'title': (event.meeting_subject_id.name or '') + '\n' + (event.customer_id.name or ''),
                    'color': event.meeting_subject_id.color or event.optometrist_id.calendar_bg_color,
                    'textColor': event.optometrist_id.calendar_text_color or 'black',
                    'present': event.present_for_appointment,
                }
                print("\n\n\n event", event_list)
                return event_list

    @api.multi
    def id_msv(self):
        current_date_time = datetime.now().strftime("%Y%m%d%H%M")
        ir_config_obj = self.env['ir.config_parameter']
        practice_number = ir_config_obj.sudo().get_param('mediswitch_integration.practice_number')
        practice_name = ir_config_obj.sudo().get_param('mediswitch_integration.practice_name')
        for partner in self:
            partner = partner.customer_id
            if not partner.id_number:
                raise Warning(_('Please enter the ID Number of the patient before you can perform the ID MSV'))
            if not partner.medical_aid_id.msv_allowed:
                raise Warning(_('Sorry, MSV is not enabled for the patients Medical Aid.'))
            if not partner.surname:
                raise MissingError("Member Surname is missing")
            if not partner.name:
                raise MissingError("Member Name is missing")
            if not partner.individual_internal_ref:
                raise MissingError("Member Internal Ref is missing")
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
                '1', partner.id_number or '',
                partner.title.name[0:5] if partner.title else 'N',
                partner.initials or 'N',
                partner.surname[0:30] if partner.surname else '',
                partner.name[0:30] if partner.surname else  '', '', 'N', '',
                '',
                # Footer Record – Type ‘E’
                partner.id or '', '1',
            )
            partner.write({'payload_description': paylod})
            if self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.for_what') == 'test':
                username = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.user_name_test')
                password = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.password_test')
                package = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.package_test')
                mode = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.mode_test')
                txversion = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.txversion_test')
                url = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.test_url')
            else:
                username = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.user_name_production')
                password = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.password_production')
                package = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.package_production')
                mode = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.mode_production')
                txversion = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.txversion_production')
                url = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.production_url')
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
                                             <txVersion>%s</txVersion>
                                             <userRef>%s</userRef>
                                             <payload>%s</payload>
                                          </v2:submitOperation>
                                       </soapenv:Body>
                                    </soapenv:Envelope>
                                    """ % (
                username, password, package, partner.plan_option_id.destination_code, mode,
                txversion,
                partner.id, paylod)
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                raise Warning(_('502 Bad Gateway'))
            responsepayload = False
            list1 = []
            wizard_data = {'partner_id': partner.id, 'msv_type': 'id_msv', 'request_payload': paylod}
            for node in response_string.iter():
                if node.tag == 'responsePayload':
                    responsepayload = node.text
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
                                raise Warning(_(split_line[5]))
                if lines and lines[0] and lines[0].startswith('H'):
                    for line in lines:
                        effective_date = False
                        termination_date = False
                        if line.startswith('P'):
                            split_line = line.split("|")
                            partner.msv_status = split_line[10]
                            self.msv_status = split_line[10]
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
                                'medical_scheme_name': split_line[12],
                                'plan_name': split_line[15],
                                'option_name': split_line[15]
                            })
                        if line.startswith('RV'):
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
            self.msv_later = False
            wizard_id = self.env['msv.response'].create(wizard_data)
            if list1:
                for data in list1:
                    data.update({'msv_response_id': wizard_id.id})
                    self.env['msv.members'].create(data)
            partner.msv_latest_date = wizard_id.create_date
            self.msv_latest_date = wizard_id.create_date
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
    def surname_dob_msv(self):
        current_date_time = datetime.now().strftime("%Y%m%d%H%M")
        ir_config_obj = self.env['ir.config_parameter']
        practice_number = ir_config_obj.sudo().get_param('mediswitch_integration.practice_number')
        practice_name = ir_config_obj.sudo().get_param('mediswitch_integration.practice_name')
        for partner in self:
            partner = partner.customer_id
            if not partner.surname and not partner.birth_date:
                raise Warning(
                    _('Please enter the Surname and DOB of the patient before you can perform the Surname DOB MSV'))
            if not partner.medical_aid_id.msv_allowed:
                raise Warning(_('Sorry, MSV is not enabled for the patients Medical Aid.'))
            if not partner.name:
                raise MissingError("Member Name is missing")
            if not partner.individual_internal_ref:
                raise MissingError("Member Internal Ref is missing")
            birthday = partner.birth_date and partner.birth_date.strftime("%Y%m%d")
            if partner.gender:
                gender = partner.gender.upper()
            else:
                raise MissingError("Gender is missing")
            paylod = """H|%s|%s|%s|
S|%s|%s|%s|%s|
M|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|
P|%s|%s|%s|%s|%s|%s|%s|%s|
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
                partner.name[0:30] if partner.name else '', '', 'N', partner.medical_aid_id.destination_code or '', '',
                # # Patient Record – Type ‘P’
                partner.dependent_code or '', partner.surname or '',
                partner.initials or '',
                partner.name or '', birthday or '',
                gender or '', '',
                partner.id_number or '',
                # Footer Record – Type ‘E’
                partner.id or '', '1',
            )
            partner.write({'payload_description': paylod})
            if self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.for_what') == 'test':
                username = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.user_name_test')
                password = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.password_test')
                package = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.package_test')
                mode = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.mode_test')
                txversion = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.txversion_test')
                url = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.test_url')
            else:
                username = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.user_name_production')
                password = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.password_production')
                package = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.package_production')
                mode = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.mode_production')
                txversion = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.txversion_production')
                url = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.production_url')
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
                                                     <txVersion>%s</txVersion>
                                                     <userRef>%s</userRef>
                                                     <payload>%s</payload>
                                                  </v2:submitOperation>
                                               </soapenv:Body>
                                            </soapenv:Envelope>
                                            """ % (
                username, password, package, partner.plan_option_id.destination_code, mode,
                txversion,
                partner.id, paylod)
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                raise Warning(_('502 Bad Gateway'))
            responsepayload = False
            list1 = []
            wizard_data = {'partner_id': partner.id, 'msv_type': 'sur_dob_msv', 'request_payload': paylod}
            for node in response_string.iter():
                if node.tag == 'responsePayload':
                    responsepayload = node.text
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
                                raise Warning(_(split_line[5]))
                if lines and lines[0] and lines[0].startswith('H'):
                    for line in lines:
                        effective_date = False
                        termination_date = False
                        if line.startswith('P'):
                            split_line = line.split("|")
                            partner.msv_status = split_line[10]
                            self.msv_status = split_line[10]
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
                                'medical_scheme_name': split_line[12],
                                'plan_name': split_line[15],
                                'option_name': split_line[15]
                            })
                        if line.startswith('RV'):
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
            self.msv_later = False
            wizard_id = self.env['msv.response'].create(wizard_data)
            if list1:
                for data in list1:
                    data.update({'msv_response_id': wizard_id.id})
                    self.env['msv.members'].create(data)
            partner.msv_latest_date = wizard_id.create_date
            self.msv_latest_date = wizard_id.create_date
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
    def submit_msv(self):
        current_date_time = datetime.now().strftime("%Y%m%d%H%M")
        ir_config_obj = self.env['ir.config_parameter']
        practice_number = ir_config_obj.sudo().get_param('mediswitch_integration.practice_number')
        practice_name = ir_config_obj.sudo().get_param('mediswitch_integration.practice_name')
        for partner in self:
            partner = partner.customer_id
            if not partner.medical_aid_id.msv_allowed:
                raise Warning(_('Sorry, MSV is not enabled for the patients Medical Aid.'))
            if not partner.surname:
                raise MissingError("Member Surname is missing")
            if not partner.name:
                raise MissingError("Member Name is missing")
            if not partner.individual_internal_ref:
                raise MissingError("Member Internal Ref is missing")
            birthday = partner.birth_date and partner.birth_date.strftime("%Y%m%d")
            if partner.gender:
                gender = partner.gender.upper()
            else:
                raise MissingError("Gender is missing")
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
                partner.name[0:30] if partner.name else '' or '', partner.medical_aid_no or '', 'N', '',
                partner.medical_aid_id.destination_code or '',
                # Footer Record – Type ‘E’
                partner.id or '', '1',
            )
            partner.write({'payload_description': paylod})
            if self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.for_what') == 'test':
                username = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.user_name_test')
                password = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.password_test')
                package = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.package_test')
                mode = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.mode_test')
                txversion = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.txversion_test')
                url = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.test_url')
            else:
                username = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.user_name_production')
                password = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.password_production')
                package = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.package_production')
                mode = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.mode_production')
                txversion = self.env['ir.config_parameter'].sudo().get_param(
                    'mediswitch_integration.txversion_production')
                url = self.env['ir.config_parameter'].sudo().get_param('mediswitch_integration.production_url')
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
                                     <txVersion>%s</txVersion>
                                     <userRef>%s</userRef>
                                     <payload>%s</payload>
                                  </v2:submitOperation>
                               </soapenv:Body>
                            </soapenv:Envelope>
                            """ % (
                username, password, package, partner.plan_option_id.destination_code, mode,
                txversion,
                partner.id, paylod)
            try:
                headers = {'Content-Type': 'text/xml', 'charset': 'utf-8'}
                response = requests.post(url, headers=headers, data=xml1.encode('utf-8'))
                response_string = ET.fromstring(response.content)
            except Exception as e:
                raise Warning(_('502 Bad Gateway'))
            responsepayload = False
            list1 = []
            wizard_data = {'partner_id': partner.id, 'msv_type': 'msv', 'request_payload': paylod}
            for node in response_string.iter():
                if node.tag == 'responsePayload':
                    responsepayload = node.text
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
                                raise Warning(_(split_line[5]))
                if lines and lines[0] and lines[0].startswith('H'):
                    for line in lines:
                        effective_date = False
                        termination_date = False
                        if line.startswith('P'):
                            split_line = line.split("|")
                            partner.msv_status = split_line[10]
                            self.msv_status = split_line[10]
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
                                'medical_scheme_name': split_line[12],
                                'plan_name': split_line[15],
                                'option_name': split_line[15]
                            })
                        if line.startswith('RV'):
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
            self.msv_later_button = False
            wizard_id = self.env['msv.response'].create(wizard_data)
            if list1:
                for data in list1:
                    data.update({'msv_response_id': wizard_id.id})
                    self.env['msv.members'].create(data)
            partner.msv_latest_date = wizard_id.create_date
            self.msv_latest_date = wizard_id.create_date
            return {
                'name': 'Msv Response Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'msv.response',
                'res_id': wizard_id.id,
                'view_id': self.env.ref('mediswitch_integration.form_view_for_msv_response1').id,
                'view_mode': 'form',
                'target': 'new',
            }
class meeeting_subject(models.Model):
    _name = 'meeting.subject'
    _description = 'Meeting Subject'

    name = fields.Char("Meeting Subject", required=True)
    color= fields.Char(string="Color")

class CrmmLead(models.Model):
    _inherit = "crm.lead"

    first_name = fields.Char("First Name")
    last_name = fields.Char("Last Name")

    @api.multi
    def action_compose_sms_phone(self):
        self.ensure_one()
        number_id = self.env['sms.number'].search(
            [('company_id', '=', self.env.user.company_id.id)], limit=1)
        default_mobile = number_id
        return {
            'name': 'SMS Compose',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sms.compose',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_from_mobile_id': default_mobile.id, 'default_to_number': self.phone,
                        'default_record_id': self.id, 'default_model': 'res.partner'}
        }
# vim:extendpandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
