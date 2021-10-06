from odoo.exceptions import UserError
from odoo import models, fields, _
from datetime import datetime

class CashBoxInOut(models.TransientModel):
    _name = 'cashbox.in.out'
    _description = 'Cashbox In Out'

    reason = fields.Char(string="Reason", )
    amount = fields.Float(string="Amount", )

    def action_take_inout(self):
        context = self._context
        session = self.env[context.get('active_model')].browse(context.get('active_id'))
        statement_id = session.account_bank_statement_id
        if statement_id.id:
            if statement_id.state == 'confirm':
                raise UserError(_("You cannot put/take money in/out for a bank statement which is closed."))

            if not statement_id.journal_id.company_id.transfer_account_id:
                raise UserError(_("You have to define an 'Internal Transfer Account' in your cash register's journal."))

            values = {
            'date': datetime.today().date(),
            'statement_id': statement_id.id,
            'journal_id': statement_id.journal_id.id,
            'amount': self.amount,
            'account_id': statement_id.journal_id.company_id.transfer_account_id.id,
            'name': self.reason,}
            statement_id.write({'line_ids': [(0, False, values)]})
            session.transaction += self.amount