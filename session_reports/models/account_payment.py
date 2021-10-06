from _datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def create(self, vals):
        if not vals.get('context'):
            if not len(self.env['session.session'].search([('user_id','=',self.env.user.id),('state','!=','closed_posted')]).ids):
                raise UserError(_("There is no Open session for Payments, Please create and open a sessions to capture any payments"))
        rslt = super(AccountPayment, self).create(vals)
        return rslt

    # def post(self):
    #     if not len(self.env['session.session'].search([('user_id','=',self.env.user.id),('state','!=','closed_posted')]).ids):
    #         raise UserError(_("There is no open session for Payments"))
    #     return super(AccountPayment, self).post()

# class AccountInvoice(models.Model):
#     _inherit = 'account.invoice'

#     def action_submit_claim(self):
#         if not len(self.env['session.session'].search([('user_id','=',self.env.user.id),('state','!=','closed_posted')]).ids):
#             raise UserError(_("There is no open session for Payments"))
#         return super(AccountInvoice, self).action_submit_claim()