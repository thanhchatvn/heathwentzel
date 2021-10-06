from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SessionDayEnd(models.Model):
    _name = 'session.day.end'
    _description = "Day End"
    _rec_name = "user_id"

    user_id = fields.Many2one("res.users", string="User")
    # store_id = fields.Many2one("stores", string="Stores")
    session_ids = fields.Many2many("session.session", string="Session", )
    company_id = fields.Many2one("res.company", string="Company", )
    cash_pickup_ids = fields.One2many("session.cash.pickups", inverse_name="session_day_end_id",
                                      string="Cash Pickups", )
    date = fields.Date(string="Date", default=fields.Date.today())
    is_processed = fields.Boolean(string="Processed", default=False)
    actual_cash = fields.Float(string="Actual Cash")
    actual_eft = fields.Float(string="Actual EFT")
    actual_voucher = fields.Float(string="Actual Voucher")
    actual_credit = fields.Float(string="Actual Credit Card")
    actual_debit = fields.Float(string="Actual Debit Card")
    actual_loyalty = fields.Float(string="Actual Loyalty")
    actual_nupay = fields.Float(string="Actual NUPay")

    expected_cash = fields.Float(string="Expected Cash")
    expected_eft = fields.Float(string="Expected EFT")
    expected_voucher = fields.Float(string="Expected Voucher")
    expected_credit = fields.Float(string="Expected Credit Card")
    expected_debit = fields.Float(string="Expected Debit Card")
    expected_loyalty = fields.Float(string="Expected Loyalty")
    expected_nupay = fields.Float(string="Expected NUPay")

    diff_cash = fields.Float(string="Difference in Cash")
    diff_eft = fields.Float(string="Difference in EFT")
    diff_voucher = fields.Float(string="Difference in Voucher")
    diff_credit = fields.Float(string="Difference in Credit Card")
    diff_debit = fields.Float(string="Difference in Debit Card")
    diff_loyalty = fields.Float(string="Difference in Loyalty")
    diff_nupay = fields.Float(string="Difference in NUPay")
    diff_nupay = fields.Float(string="Difference in NUPay")

    account_sale_count = fields.Integer(string="Total Account Sale Count", )
    account_sale_total = fields.Float(string="Total Account Sale Amount", )
    cash_sale_count = fields.Integer(string="Total cash Sale", )
    cash_sale_total = fields.Float(string="Total Cash Sale Amount", )
    hp_sale_count = fields.Integer(string="Total Hire Purchase Sale", )
    hp_sale_total = fields.Float(string="Total Hire Purchase Sale Amount", )

    # @api.onchange('user_id', 'date')
    # def onchange_user_id(self):
    #     for rec in self:
    #         if rec.date:
    #             day_ends = rec.search([('date', '=', rec.date), ('user_id', '=', rec.env.user.id)])
    #             if len(day_ends.ids):
    #                 raise UserError(_("A Day end already exists for {}".format(rec.date)))
    #         values = rec.session_day_end_values(search_date=rec.date)
    #         rec.write(values)

    def session_day_end_values(self, search_date=False):
        user = self.user_id or self.env.user
        if user.id:
            sessions = self.session_ids.sudo().search([])
            sessions = sessions.sudo().filtered(lambda x: x.opening_date.date() == search_date)

            return {
                'user_id': user.id,
                'session_ids': len(sessions.ids) and [(6, 0, sessions.ids)] or False,
                'company_id': user.company_id.id,
                'date': search_date,
                'cash_pickup_ids': [(6, 0, sessions.out_money_ids.ids)]
            }

    # def session_day_end_values(self, search_date=False):
    #     user = self.user_id.id and self.user_id or self.env.user
    #     if user.id:
    #         store = self.store_id.search([('member_ids', 'child_of', [user.id])])
    #         sessions = self.session_ids.sudo().search([('store_id', '=', store.id)])
    #         sessions = sessions.sudo().filtered(lambda x: x.opening_date.date() == search_date)
    #         return {
    #             'user_id': user.id,
    #             'store_id': store.id,
    #             'session_ids': len(sessions.ids) and [(6, 0, sessions.ids)] or False,
    #             'company_id': user.company_id.id,
    #             'date': search_date,
    #             'cash_pickup_ids': [(6, 0, sessions.out_money_ids.ids)]
    #         }

    def write(self, values):
        if values.get('date', False):
            values = self.session_day_end_values(search_date=fields.Date.from_string(values.get('date')))
        return super(SessionDayEnd, self).write(values)

    @api.model
    def create(self, vals):
        search_date = vals.get('date', False) and fields.Date.from_string(vals.get('date', '')) or date.today()
        session_values = self.session_day_end_values(search_date=search_date)
        res = super(SessionDayEnd, self).create(session_values)
        return res

    def process_day_end(self):
        self.ensure_one()
        sessions = self.session_ids
        open_sessions = sessions.filtered(lambda x: x.state != 'closed_posted')
        if len(open_sessions):
            raise UserError("Please close this following session for Process Day end:\n{}".format(
                "\n".join(open_sessions.mapped('session_id'))))
        values = {}
        if len(sessions.ids):
            values = {
                'is_processed': True,
                'actual_cash': sum(sessions.mapped('actual_cash')),
                'actual_eft': sum(sessions.mapped('actual_eft')),
                'actual_voucher': sum(sessions.mapped('actual_voucher')),
                'actual_credit': sum(sessions.mapped('actual_credit')),
                'actual_debit': sum(sessions.mapped('actual_debit')),
                'actual_loyalty': sum(sessions.mapped('actual_loyalty')),
                'actual_nupay': sum(sessions.mapped('actual_nupay')),
                'diff_cash': sum(sessions.mapped('difference')),
                'diff_eft': sum(sessions.mapped('diff_eft')),
                'diff_voucher': sum(sessions.mapped('diff_voucher')),
                'diff_credit': sum(sessions.mapped('diff_credit')),
                'diff_debit': sum(sessions.mapped('diff_debit')),
                'diff_loyalty': sum(sessions.mapped('diff_loyalty')),
                'diff_nupay': sum(sessions.mapped('diff_nupay')),
            }
        out_payments = self.env['account.payment'].search([
                # ('create_uid', 'in', self.),
                # ('journal_id', 'in', self.store_id.payment_ids.ids),
                ('payment_type', '=', 'outbound')
            ]).filtered(lambda x: x.create_date.date() == self.date)
        in_payments = self.env['account.payment'].search([
                # ('create_uid', 'in', self.store_id.member_ids.ids),
                # ('journal_id', 'in', self.store_id.payment_ids.ids),
                ('payment_type', '=', 'inbound')
            ]).filtered(lambda x: x.create_date.date() == self.date)
        if len(out_payments.ids) or len(in_payments.ids):
            values.update({
                'expected_cash': sum(
                    in_payments.filtered(lambda x: 'cash' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'cash' in x.journal_id.name.lower()).mapped('amount')),
                'expected_eft': sum(
                    in_payments.filtered(lambda x: 'eft' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'eft' in x.journal_id.name.lower()).mapped('amount')),
                'expected_voucher': sum(
                    in_payments.filtered(lambda x: 'voucher' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'voucher' in x.journal_id.name.lower()).mapped('amount')),
                'expected_credit': sum(
                    in_payments.filtered(lambda x: 'credit' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'credit' in x.journal_id.name.lower()).mapped('amount')),
                'expected_debit': sum(
                    in_payments.filtered(lambda x: 'debit' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'debit' in x.journal_id.name.lower()).mapped('amount')),
                'expected_loyalty': sum(
                    in_payments.filtered(lambda x: 'loyalty' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'loyalty' in x.journal_id.name.lower()).mapped('amount')),
                'expected_nupay': sum(
                    in_payments.filtered(lambda x: 'nupay' in x.journal_id.name.lower()).mapped('amount')) - sum(
                    out_payments.filtered(lambda x: 'nupay' in x.journal_id.name.lower()).mapped('amount')),
            })

        # orders = self.env['sale.order'].search([('user_id', 'in', self.user_id)])
        # if (len(orders.ids)):
        #     sale_values = {
        #         'cash': self.env['sale.order'],
        #         'hire_purchase': self.env['sale.order'],
        #         'account_sale': self.env['sale.order'],
        #     }
        #     for ot in sale_values.keys():
        #         for session in self.session_ids:
        #             order = orders.filtered(lambda x: x.sale_type == ot)
        #             order = order.filtered(
        #                 lambda x: x.create_date>=session.opening_date and x.create_date<=session.closing_date)
        #             if sale_values[ot]:
        #                 sale_values[ot] |= order
        #             else:
        #                 sale_values[ot] = order
        #     values.update({
        #         'account_sale_count': len(sale_values['account_sale'].ids),
        #         'account_sale_total': sum(sale_values['account_sale'].mapped('amount_total')),
        #         'cash_sale_count': len(sale_values['cash'].ids),
        #         'cash_sale_total': sum(sale_values['cash'].mapped('amount_total')),
        #         'hp_sale_count': len(sale_values['hire_purchase'].ids),
        #         'hp_sale_total': sum(sale_values['hire_purchase'].mapped('amount_total')),
        #     })
        if len(values):
            self.write(values)
            # self.session_ids.write({'is_day_end_processed': True})


class SessionCashPickups(models.Model):
    _name = 'session.cash.pickups'
    _description = "Cash Pickups for Day end"

    session_day_end_id = fields.Many2one("session.day.end", string="Day End")
    session_id = fields.Many2one("session.session", string="Session")
    user_id = fields.Many2one("res.users",related="session_id.user_id", string="User", )
    # store_id = fields.Many2one("stores", related="session_id.store_id",string="Store", )
    date = fields.Datetime(string="Date", )
    reason = fields.Char(string="Reason", )
    amount = fields.Float(string="Amount", )
    sequence = fields.Char(string="Sequence", )

    @api.model
    def create(self, values):
        res = super(SessionCashPickups, self).create(values)
        if res.session_id.id:
            res['date'] = datetime.now()
            session_id = res.session_id
            sequence = len(session_id.out_money_ids.ids)
            # sequence = "{} / {} / {}".format(sess_name[:7], session_id.user_id.name[:3], "{:05d}".format(sequence))
            sequence = "{} / {} / {}".format(res.session_id.session_id and res.session_id.session_id[:7] or "-",
                                             session_id.user_id.name and session_id.user_id.name[:3] or "-",
                                             "{:05d}".format(sequence))
            res['sequence'] = sequence
        return res
