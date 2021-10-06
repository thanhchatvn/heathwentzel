from _datetime import datetime
from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement.cashbox"

    actual_eft = fields.Float(string="Actual in EFT")
    actual_voucher = fields.Float(string="Actual in Voucher")
    actual_credit = fields.Float(string="Actual in Credit Card")
    actual_debit = fields.Float(string="Actual in Debit Card")
    actual_loyalty = fields.Float(string="Actual in Loyalty")
    actual_nupay = fields.Float(string="Actual in NUPay")
    actual_inter_comp = fields.Float(string="Actual Inter-Company Cash")

    total = fields.Float(compute='_compute_total')

    @api.depends('cashbox_lines_ids', 'cashbox_lines_ids.coin_value', 'cashbox_lines_ids.number')
    def _compute_total(self):
        for cashbox in self:
            cashbox.total = sum([line.subtotal for line in cashbox.cashbox_lines_ids])

    def save_cashbox_line(self):
        self.ensure_one()
        session_id = self._context.get('session_id',False)
        if session_id:
            session_id = self.env['session.session'].browse(session_id)
            if self._context.get('balance','') == 'open':
                values = {
                    'journal_id':session_id.journal_id.filtered(lambda x:x.type.lower() == 'cash').id,
                    'name':session_id.session_id,
                    'balance_start':self.total,
                    'date':datetime.today().date(),
                    'company_id':self.env.user.company_id.id
                }
                bank_statement_id  = self.env['account.bank.statement'].create(values)
                session_id.write({'state':'opening_control','account_bank_statement_id':bank_statement_id.id})
            elif self._context.get('balance','') == 'close':
                cash_journal = session_id.journal_id.filtered(lambda x: x.type.lower() == 'cash').ids
                bank_state = session_id.account_bank_statement_id
                if bank_state.id:
                    bank_state.balance_end = self.total
                values = {
                    'state': 'closed_posted',
                    'closing_date':datetime.now(),
                    'actual_cash': self.total,
                    'actual_eft': self.actual_eft,
                    'actual_voucher': self.actual_voucher,
                    'actual_credit': self.actual_credit,
                    'actual_debit': self.actual_debit,
                    'actual_loyalty': self.actual_loyalty,
                    'actual_nupay': self.actual_nupay,
                    'actual_inter_comp': self.actual_inter_comp,
                }
                domain = session_id._get_common_domain()
                domain += [('partner_type', '=', 'customer'), ('journal_id', 'in', session_id.journal_id.ids)]
                payments = self.env['account.payment'].search(domain)
                if len(payments.ids):
                    values.update({
                        'diff_eft': self.actual_eft - sum(
                            payments.filtered(lambda x: 'eft' in x.journal_id.name.lower()).mapped(
                                'amount')),
                        'diff_voucher': self.actual_voucher - sum(
                            payments.filtered(lambda x: 'voucher' in x.journal_id.name.lower()).mapped(
                                'amount')),
                        'diff_credit': self.actual_credit - sum(
                            payments.filtered(lambda x: 'credit' in x.journal_id.name.lower()).mapped(
                                'amount')),
                        'diff_debit': self.actual_debit - sum(
                            payments.filtered(lambda x: 'debit' in x.journal_id.name.lower()).mapped(
                                'amount')),
                        'diff_loyalty': self.actual_loyalty - sum(
                            payments.filtered(lambda x: 'loyalty' in x.journal_id.name.lower()).mapped(
                                'amount')),
                        'diff_nupay': self.actual_nupay - sum(
                            payments.filtered(lambda x: 'nupay' in x.journal_id.name.lower()).mapped(
                                'amount')),
                    })
                session_id.write(values)
