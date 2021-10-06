from odoo import models, api, _, fields
from odoo.tools.misc import format_date


class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"
    _description = "Partner Ledger"

    def _get_columns_name(self, options):
        columns = [
            {},
            {'name': _('JRNL')},
            {'name': _('Account')},
            {'name': _('Ref')},
            {'name': _('Due Date'), 'class': 'date'},
            {'name': _('Matching Number')},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'}]

        columns.append({'name': _('Balance'), 'class': 'number'})
        return columns


    @api.model
    def _get_lines(self, options, line_id=None):
        offset = int(options.get('lines_offset', 0))
        lines = []
        context = self.env.context
        company_id = context.get('company_id') or self.env.user.company_id
        if line_id:
            line_id = int(line_id.split('_')[1]) or None
        elif options.get('partner_ids') and len(options.get('partner_ids')) == 1:
            # If a default partner is set, we only want to load the line referring to it.
            partner_id = options['partner_ids'][0]
            line_id = partner_id
        if line_id:
            if 'partner_' + str(line_id) not in options.get('unfolded_lines', []):
                options.get('unfolded_lines', []).append('partner_' + str(line_id))

        grouped_partners = self._group_by_partner_id(options, line_id)
        sorted_partners = sorted(grouped_partners, key=lambda p: p.name or '')
        unfold_all = context.get('print_mode') and not options.get('unfolded_lines')
        total_initial_balance = total_debit = total_credit = total_balance = 0.0
        for partner in sorted_partners:
            debit = grouped_partners[partner]['debit']
            credit = grouped_partners[partner]['credit']
            balance = grouped_partners[partner]['balance']
            initial_balance = grouped_partners[partner]['initial_bal']['balance']
            total_initial_balance += initial_balance
            total_debit += debit
            total_credit += credit
            total_balance += balance
            columns = [self.format_value(debit), self.format_value(credit)]
            columns.append(self.format_value(balance))
            # don't add header for `load more`
            if offset == 0:
                lines.append({
                    'id': 'partner_' + str(partner.id),
                    'name': partner.name,
                    'columns': [{'name': v} for v in columns],
                    'level': 2,
                    'trust': partner.trust,
                    'unfoldable': True,
                    'unfolded': 'partner_' + str(partner.id) in options.get('unfolded_lines') or unfold_all,
                    'colspan': 6,
                })
            user_company = self.env.user.company_id
            used_currency = user_company.currency_id
            if 'partner_' + str(partner.id) in options.get('unfolded_lines') or unfold_all:
                if offset == 0:
                    progress = initial_balance
                else:
                    progress = float(options.get('lines_progress', initial_balance))
                domain_lines = []
                amls = grouped_partners[partner]['lines']

                remaining_lines = 0
                if not context.get('print_mode'):
                    remaining_lines = grouped_partners[partner]['total_lines'] - offset - len(amls)

                for line in amls:
                    if options.get('cash_basis'):
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    date = amls.env.context.get('date') or fields.Date.today()
                    line_currency = line.company_id.currency_id
                    line_debit = line_currency._convert(line_debit, used_currency, user_company, date)
                    line_credit = line_currency._convert(line_credit, used_currency, user_company, date)
                    progress = progress + line_debit - line_credit
                    caret_type = 'account.move'
                    if line.invoice_id:
                        caret_type = 'account.invoice.in' if line.invoice_id.type in (
                        'in_refund', 'in_invoice') else 'account.invoice.out'
                    elif line.payment_id:
                        caret_type = 'account.payment'
                    domain_columns = [line.journal_id.code, line.account_id.code, self._format_aml_name(line),
                                      line.date_maturity and format_date(self.env, line.date_maturity) or '',
                                      line.full_reconcile_id.name or '',
                                      line_debit != 0 and self.format_value(line_debit) or '',
                                      line_credit != 0 and self.format_value(line_credit) or '']
                    domain_columns.append(self.format_value(progress))
                    columns = [{'name': v} for v in domain_columns]
                    columns[3].update({'class': 'date'})
                    domain_lines.append({
                        'id': line.id,
                        'parent_id': 'partner_' + str(partner.id),
                        'name': format_date(self.env, line.date),
                        'class': 'date',
                        'columns': columns,
                        'caret_options': caret_type,
                        'level': 4,
                    })

                # load more
                if remaining_lines > 0:
                    domain_lines.append({
                        'id': 'loadmore_%s' % partner.id,
                        'offset': offset + self.MAX_LINES,
                        'progress': progress,
                        'class': 'o_account_reports_load_more text-center',
                        'parent_id': 'partner_%s' % partner.id,
                        'name': _('Load more... (%s remaining)') % remaining_lines,
                        'colspan': 10 if self.user_has_groups('base.group_multi_currency') else 9,
                        'columns': [{}],
                    })
                lines += domain_lines

        if not line_id:
            total_columns = ['', '', '', '', '', self.format_value(total_debit), self.format_value(total_credit)]
            total_columns.append(self.format_value(total_balance))
            lines.append({
                'id': 'grouped_partners_total',
                'name': _('Total'),
                'level': 0,
                'class': 'o_account_reports_domain_total',
                'columns': [{'name': v} for v in total_columns],
            })
        return lines