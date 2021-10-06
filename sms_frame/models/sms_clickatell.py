# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# from clickatell.http import Http

from odoo import api, fields, models,_
from odoo.exceptions import MissingError,Warning
import requests
import json


class SmsGatewayClickatell(models.Model):
    _name = "sms.gateway.clickatell"
    _description = "SMS Gateway Clicktail"

    @api.multi
    def send_message(self, sms_gateway_id, from_number, to_number, sms_content, my_model_name='', my_record_id=0, media=None, queued_sms_message=None):
        sms_account = self.env['sms.account'].search([('id', '=', sms_gateway_id)], limit=1, order="id desc")
        if not sms_account:
            sms_account =  self.env['sms.account'].search([('account_gateway_id.name', '=', 'Clickatell')], limit=1, order="id desc")
        url='https://platform.clickatell.com/messages/http/send'
        record = self.env[my_model_name].browse(int(my_record_id))
        if record.mobile or record.phone or to_number:
            number = record.mobile or record.phone or to_number
            number = number.replace(" ",  "")
            if number.startswith('+'):
                to_number = number[3:]
            elif number.startswith('27'):
                to_number = number[2:]
            elif number.startswith('0027'):
                to_number = number[4:]
            if my_model_name == 'project.task':
                to_number = str(record.partner_id.country_id.phone_code) + str(to_number)
            else:
                if self.env.user:
                    to_number = str(self.env.user.country_id.phone_code) + str(to_number)
                else:
                    to_number = str(27) + str(to_number)
        else:
            raise Warning(_("Please Enter Mobile Number or Phone Number for this record!!!..."))
        PARAMS = {'to':int(to_number),'content':sms_content.decode('utf-8') if not isinstance(sms_content, str) else sms_content,'apiKey':sms_account.clicKatell_api,'from':from_number}
        response = requests.get(url,params=PARAMS)
        return response.json()

    def check_messages(self, account_id, message_id=""):
        return True

    def _add_message(self, sms_message, account_id):
        return True


class SmsAccountClickatell(models.Model):
    _inherit = "sms.account"
    _description = "Adds the Clickatell specific gateway settings to the sms gateway accounts"

    clicKatell_username = fields.Char(string='Username')
    clicKatell_password = fields.Char(string='Password')
    clicKatell_api = fields.Char(string="API Key")
