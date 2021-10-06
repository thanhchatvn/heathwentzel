# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, _
_logger = logging.getLogger(__name__)
# from clickatell.http import Http
from odoo.exceptions import Warning

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post_send_sms(self, sms_message, numbers=None, partners=None, note_msg=None, log_error=False):
        """ This is the custom method especially made for Clickatell api call // Added by Dhruvil
            Send an SMS text message and post an internal note in the chatter if successfull
            :param sms_message: plaintext message to send by sms
            :param partners: the numbers to send to, if none are given it will take those
                                from partners or _get_default_sms_recipients
            :param partners: the recipients partners, if none are given it will take those
                                from _get_default_sms_recipients, this argument
                                is ignored if numbers is defined
            :param note_msg: message to log in the chatter, if none is given a default one
                             containing the sms_message is logged
        """
        if not numbers:
            if not partners:
                partners = self._get_default_sms_recipients()

                # Collect numbers, we will consider the message to be sent if at least one number can be found
                numbers = list(set([i.mobile for i in partners if i.mobile]))
        if numbers:
            try:
                model = self.env.context.get('active_model')
                sms_number_id = self.env['sms.number'].search([('company_id', '=', self.env.user.company_id.id)],
                                                              limit=1)
                if sms_number_id and sms_number_id.account_id.account_gateway_id.gateway_model_name == "sms.gateway.clickatell":

                    from_number = sms_number_id.mobile_number if sms_number_id else ''
                    for each_number in numbers:
                        data = sms_number_id.account_id.send_message(from_number, each_number, sms_message, model, False, False)
                        if data.get('errorCode'):
                            raise Warning(_(data.get('error') + "\n(" + data.get('errorDescription') + ")"))
                else:
                    if sms_number_id.account_id:
                        for each_number in numbers:
                            self.env['sms.api'].smsapi(sms_number_id.account_id, each_number, sms_message, False, model, False, False, False)
            except Exception as e:
                if not log_error:
                    raise e
        return False
