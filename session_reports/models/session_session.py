
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..__init__ import _set_trace


class SessionSession(models.Model):
    _name = 'session.session'
    _description = "Session for the Cash Control"
    _rec_name = 'session_id'

    session_id = fields.Char(string="Session ID")
    # store_id = fields.Many2one("res.users", string="Store")
    journal_id = fields.Many2many("account.journal", string="Payment Method",
        default=lambda self: self.env['account.journal'].search([('company_id', '=', self.env.user.company_id.id)]))
    user_id = fields.Many2one("res.users", string="Responsible")
    opening_date = fields.Datetime(string="Opening Date")
    closing_date = fields.Datetime(string="Closing Date")
    starting_cash = fields.Float(string="Starting Cash")
    actual_cash = fields.Float(string="Actual in Cash")
    transaction = fields.Float(string="Transactions Cash", compute="_get_sale_hp_payment_count")
    expected_cash = fields.Float(string="Expected in Cash", compute="_get_expected_cash")
    difference = fields.Float(string="Difference", compute="_get_difference")
    state = fields.Selection(string="Status", selection=[
        ('new_session', 'New Session'), ('opening_control', 'Opening Control'),
        ('in_progress', 'In Progress'), ('closing_control', 'Closing Control'),
        ('closed_posted', 'Closed & Posted')], default='new_session')
    account_bank_statement_id = fields.Many2one(comodel_name="account.bank.statement", string="Bank Statement")
    out_money_ids = fields.One2many("session.cash.pickups", inverse_name="session_id", string="Out Money")
    sale_order_count = fields.Integer(string="Total Sale")
    payment_count = fields.Integer(string="Total Payment", compute="_get_sale_hp_payment_count")
    # hp_count = fields.Integer(string="Total HP", compute="_get_sale_hp_payment_count")
    actual_eft = fields.Float(string="Actual in EFT")
    actual_voucher = fields.Float(string="Actual in Voucher")
    actual_credit = fields.Float(string="Actual in Credit Card")
    actual_debit = fields.Float(string="Actual in Debit Card")
    actual_loyalty = fields.Float(string="Actual in Loyalty")
    actual_nupay = fields.Float(string="Actual in NUPay")
    actual_inter_comp = fields.Float(string="Actual Inter-Company Cash")
    diff_eft = fields.Float(string="Difference in EFT")
    diff_voucher = fields.Float(string="Difference in Voucher")
    diff_credit = fields.Float(string="Difference in Credit Card")
    diff_debit = fields.Float(string="Difference in Debit Card")
    diff_loyalty = fields.Float(string="Difference in Loyalty")
    diff_nupay = fields.Float(string="Difference in NUPay")
    # is_day_end_processed = fields.Boolean(string="Is Dayend Processed")

    # @api.onchange('user_id')
    # def change_store_id(self):

    @api.depends('actual_cash', 'expected_cash')
    def _get_difference(self):
        for record in self:
            record.difference = record.actual_cash - record.expected_cash

    @api.depends('transaction', 'starting_cash','out_money_ids')
    def _get_expected_cash(self):
        for record in self:
            record.expected_cash = (record.starting_cash + record.transaction) - sum(record.out_money_ids.mapped('amount'))

    @api.model
    def create(self, vals):
        # _set_trace()
        session = self
        if vals.get('user_id',False):
            session =session.search([('user_id','=',vals.get('user_id',False))],order='create_date desc')
        if len(session.filtered(lambda x:x.state != 'closed_posted').ids):
            raise UserError(_("A session already in progress"))
        # if len(session.filtered(lambda x:not x.is_day_end_processed).ids):
        #     raise UserError(_("Request Manager to Process Day End"))
        vals.update({'opening_date': datetime.now()})

        if len(session.ids) and session[0].actual_cash:
            vals.update({'starting_cash':session[0].actual_cash,'state':'opening_control'})
        vals['session_id'] = self.env['ir.sequence'].next_by_code('session.number')
        res = super(SessionSession, self).create(vals)
        # session = 101
        # res.session_id = res.user_id.name
        return res

    def _get_common_domain(self):
        domain = [('create_date', '>=', self.opening_date and self.opening_date or False),
                ('create_uid', '=', self.user_id.id)]
        if self.closing_date:
            domain.append(('create_date','<=',self.closing_date))
        return domain

    @api.depends('user_id', 'opening_date', 'closing_date')
    def _get_sale_hp_payment_count(self):
        for record in self:
            domain = record._get_common_domain()
            payment_domain = [('partner_type', '=', 'customer'),('payment_type','=','inbound')]
            refund_domain = [('partner_type', '=', 'customer'),('payment_type','=','outbound')]
            transfer_domain = [('payment_type','=','transfer')]
            payments = self.env['account.payment'].search(domain + payment_domain)
            refunds = self.env['account.payment'].search(domain + refund_domain)
            transfer = self.env['account.payment'].search(domain + transfer_domain)
            tot_payments = ( payments + refunds + transfer )
            # orders = self.env['sale.order'].search(domain)
            # hp_accounts = self.env['account.hp'].sudo().search(domain)
            record.payment_count = len(tot_payments)
            # record.sale_order_count = len(orders)
            # record.hp_count = len(hp_accounts)
            record.transaction = (
                sum(payments.filtered(lambda x: 'cash' in x.journal_id.name.lower()).mapped('amount')) -
                sum(refunds.filtered(lambda x: 'cash' in x.journal_id.name.lower()).mapped('amount')) -
                sum(transfer.filtered(lambda x: 'cash' in x.journal_id.name.lower()).mapped('amount'))
            ) or 0.0

    # @api.depends('user_id', 'opening_date', 'closing_date')
    # def _get_sale_hp_payment_count(self):
    #     # _set_trace()
    #     for record in self:
    #         domain = record._get_common_domain()
    #         payment_domain = [('partner_type', '=', 'customer')]
    #         payments = self.env['account.payment'].search(domain + payment_domain)
    #         # payments = self.env['account.payment'].search(payment_domain)
    #         # orders = self.env['sale.order'].search(domain)
    #         # hp_accounts = self.env['account.hp'].sudo().search(domain)
    #         record.payment_count = len(payments)
    #         # record.sale_order_count = len(orders)
    #         # record.hp_count = len(hp_accounts)
    #         record.transaction = len(payments) and sum(
    #             payments.filtered(lambda x: 'cash' in x.journal_id.name.lower()).mapped('amount')) or 0.0

    def action_view_sale_orders(self):
        '''
             Opens the tree view of sale.order to show Sale Order Records
        '''
        self.ensure_one()
        domain = self._get_common_domain()
        sale_orders = self.env['sale.order'].search(domain)
        action = self.env.ref('sale.action_orders').read()[0]
        if len(sale_orders.ids):
            action['views'] = [(self.env.ref('sale.view_order_tree').id, 'tree')]
            action['domain'] = [('id', 'in', sale_orders.ids)]
        return action

    def action_view_payments(self):
        domain = self._get_common_domain()
        domain = domain + [('partner_type', '=', 'customer'), ('journal_id', 'in', self.journal_id.ids)]
        return {
            'name': _('HP Payments'),
            'domain': domain,
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('account.view_account_payment_tree').id, 'tree'), (False, 'form')],
        }

    def open_cashbox_id(self):
        self.ensure_one()
        cash_journal = self.journal_id.filtered(lambda x: x.type.lower() == 'cash').ids
        if not len(cash_journal):
            raise UserError(_("No cash journal is set"))
        elif len(cash_journal)>1:
            raise UserError(_("More than one cash journal is set"))
        context = dict(self.env.context or {})
        context.update({
            'session_id': self.id
        })
        if context.get('balance'):
            action = {
                'name': _('Cash Control'),
                'view_mode': 'form',
                'res_model': 'account.bank.statement.cashbox',
                'view_id': self.env.ref('session_reports.view_account_bnk_stmt_cashbox_footer_inherit').id,
                'type': 'ir.actions.act_window',
                'res_id': False,
                'context': context,
                'target': 'new'
            }
            return action

    def open_session(self):
        self.ensure_one()
        cash_journal = self.journal_id.filtered(lambda x: x.type.lower() == 'cash').ids
        bank_state = self.env['account.bank.statement'].search([
            ('name', '=', self.session_id),
            ('journal_id', 'in', cash_journal)
        ])
        for bank in bank_state:
            self.starting_cash += bank.id and bank.balance_start or 0.0
        self.state = 'in_progress'

    def action_view_hps(self):
        self.ensure_one()
        domain = self._get_common_domain()
        return {
            'name': _('HP Payments'),
            'domain': domain,
            'res_model': 'account.hp',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('hire_purchase.account_hp_tree').id, 'tree'), (False, 'form')],
        }

    def close_daily_session(self):
        sessions = self.search([('state', 'not in', ['closed_posted'])])
        sessions.write({'state': 'closed_posted', 'closing_date': datetime.now()})

    def open_bank_statement(self):
        self.ensure_one()
        return {
            'name': _('Account Bank Statement'),
            'res_model': 'account.bank.statement',
            'res_id': self.account_bank_statement_id.id,
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('account.view_bank_statement_form').id, 'form')],
        }

    def unlink(self):
        self.mapped('account_bank_statement_id').unlink()
        return super(SessionSession, self).unlink()
