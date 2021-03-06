# -*- coding: utf-8 -*
from odoo import api, fields, models

from datetime import datetime
import base64
import logging
_logger = logging.getLogger(__name__)

class SmsCompose(models.Model):
    _name = "sms.compose"
    _description = "SMS Compose"

    error_message = fields.Char(readonly=True)
    record_id = fields.Integer()
    model = fields.Char()
    sms_template_id = fields.Many2one('sms.template', string="Template")
    from_mobile_id = fields.Many2one('sms.number', required=True, string="From Mobile")
    to_number = fields.Char(required=True, string='To Mobile Number', readonly=True)
    sms_content = fields.Text(string='SMS Content')
    media_id = fields.Binary(string="Media (MMS)")
    media_filename = fields.Char(string="Media Filename")

    @api.onchange('sms_template_id')
    def _onchange_sms_template_id(self):
        """Prefills from mobile, sms_account and sms_content but allow them to manually change the content after"""
        if self.sms_template_id.id != False:
            sms_rendered_content = self.env['sms.template'].render_template(self.sms_template_id.template_body, self.sms_template_id.model_id.model, self.record_id)
            # self.from_mobile_id = self.sms_template_id.from_mobile_verified_id.id
            self.media_id = self.sms_template_id.media_id
            self.media_filename = self.sms_template_id.media_filename
            self.sms_content = sms_rendered_content

    # @api.multi
    # def send_entity(self):
    #     """Attempt to send the sms, if any error comes back show it to the user and only log the smses that successfully sent"""
    #     self.ensure_one()
    #     gateway_model = self.from_mobile_id.account_id.account_gateway_id.gateway_model_name
    #     my_sms = self.from_mobile_id.account_id.send_message(self.from_mobile_id.mobile_number, self.to_number, self.sms_content.encode('utf-8'), self.model, self.record_id, self.media_id)[0]
    #     if len(my_sms['messages']) > 0:
    #         pass
    #     else:
    #         error_message = my_sms['error']
    #
    #     #display the screen with an error code if the sms/mms was not successfully sent
    #     if len(my_sms['messages']) == 0:
    #         if my_sms['errorCode'] != False:
    #             return {
    #                'type':'ir.actions.act_window',
    #                'res_model':'sms.compose',
    #                'view_type':'form',
    #                'view_mode':'form',
    #                'target':'new',
    #                'context':{'default_to_number':self.to_number,'default_record_id':self.record_id,'default_model':self.model, 'default_error_message':error_message}
    #             }
    #     else:
    #         my_model = self.env['ir.model'].search([('model','=',self.model)])
    #
    #     #for single smses we only record succesful sms, failed ones reopen the form with the error message
    #     sms_message = self.env['sms.message'].create({
    #         'record_id': self.record_id,
    #         'model_id': my_model[0].id,
    #         'account_id': self.from_mobile_id.account_id.id,
    #         'from_mobile': self.from_mobile_id.mobile_number,
    #         'to_mobile': self.to_number,
    #         'sms_content': self.sms_content,
    #         'status_string': my_sms['error'] if 'error' in my_sms.keys() else False,
    #         'direction': 'O',
    #         'message_date': datetime.utcnow(),
    #         'status_code': my_sms['errorCode'] if 'errorCode' in my_sms.keys() else False,
    #         'sms_gateway_message_id': my_sms['id'] if 'id' in my_sms.keys() else False,
    #         'by_partner_id': self.env.user.partner_id.id
    #     })
    #     sms_subtype = self.env['ir.model.data'].get_object('sms_frame', 'sms_subtype')
    #     attachments = []
    #     if self.media_id:
    #         attachments.append((self.media_filename, base64.b64decode(self.media_id)) )
    #     self.env[self.model].search([('id','=', self.record_id)]).message_post(body=self.sms_content, subject="SMS Sent", message_type="comment", subtype_id=sms_subtype.id, attachments=attachments)
