#################################################################################

from odoo import models,fields,api ,_
from datetime import date

class ResponseWizard(models.Model):
    _name="response.error.wizard"
    _description="To view the information of the response payload"

    name = fields.Text(readonly=1,string="Status")
    response_error = fields.Char(string="Response Error")
    general_comments = fields.Char(string="General Comments")
    date_of_submission = fields.Date(string="Date Of Submission")
    Medical_aid = fields.Char(string="Medical Aid")
    practise_name = fields.Char(string="Practise Name")
    practise_number = fields.Char(string="Practise No")
    patient_name = fields.Many2one('res.partner',string="Patient Name")
    patient_dob = fields.Date(string="DOB")
    invoice_id = fields.Many2one("account.invoice",string="Invoice No")
    account_no = fields.Char(string="Account No")
    member_no = fields.Char(string="Member No")
    claim_status_lines_ids = fields.One2many("claim.status.lines",'response_id')
    mediswitch_type = fields.Selection([('Claim', 'Claim'), ('Benefit', 'Benefit')],
                                       string="Type")

    @api.multi
    def apply_response(self):
        print("\n\nn\ calll--->")
        claim_id = self.env['mediswitch.submit.claim'].search([('view_id','=',self.id)], limit=1)
        responsepayload = claim_id.response_payload
        if self.invoice_id.state not in ['paid', 'done', 'cancel']:
            for invoice in self.invoice_id:
                if responsepayload:
                    claim_status_lines = []
                    lines = responsepayload.split("\n")
                    strings = ("Invalid Missing", "Invalid")
                    if any(s in lines[0] for s in strings):
                        raise Warning(_(
                            'email Humint Support for assistance. support@humint.co.za or log a ticket at http://www.humint.co.za/helpdesk/humint-2/submit' + "\n(" +
                            lines[0] + ")"))
                    if lines and lines[0] and lines[0].startswith('H'):
                        flag = 0
                        treatment_line = 0
                        balance_price = 0
                        approved_price = 0
                        total_approved_price = 0
                        general_comments = ''
                        rejection_count = ''
                        status_claim_level = ''
                        list1 = []
                        r_list = []
                        g_list = []
                        number = 0
                        check_element_list = ['T', 'E', 'FR', 'F']
                        for line in lines:
                            r_line = ''
                            position = lines.index(line)
                            pos = position
                            split_line = line.split("|")
                            if line.startswith('S'):
                                if int(line.split("|")[5]) >= 0:
                                    flag = 1
                            if line.startswith('R') and flag == 1:
                                rejection_count += "\n" + split_line[2] + ' - ' + split_line[1]
                            if line.startswith('FR') and flag == 1:
                                rejection_count += "\n" + split_line[1]
                            if line.startswith('G'):
                                general_comments = split_line[1]
                            if line.startswith('P') and flag == 1:
                                invoice.claim_level_mediswitch_status = split_line[13]
                                invoice.authorization_code = split_line[7]
                                if split_line[14] == '01':
                                    invoice.responding_party = "MediSwitch"
                                elif split_line[14] == '02':
                                    invoice.responding_party = "Medical Scheme / Administrator"
                                status_claim_level = invoice.claim_level_status(split_line[13])
                            if line.startswith('T') and flag == 1:
                                treatment_line += 1
                                message1, message2, message3 = invoice.claim_messages(split_line[14], split_line[15],
                                                                                      split_line[16])
                                claim_status_lines.append(message1)
                                position = position + 1

                                while lines[position] and position > 0 and lines[position][0] not in check_element_list:
                                    if lines[position].startswith('R'):
                                        split_list = lines[position].split("|")
                                        r_line += "\n" + split_list[2] + ' - ' + split_list[1]
                                    else:
                                        pass
                                    position = position + 1
                                r_list.append(r_line)
                                pos = pos + 1
                                if lines[pos].startswith('G'):
                                    split_list = lines[pos].split("|")
                                    g_list.append(split_list[1])
                                else:
                                    g_list.append(" ")
                            if line.startswith('Z'):
                                if split_line[18]:
                                    approved_price = int(split_line[18]) / 100
                                    total_approved_price += approved_price
                                if split_line[16]:
                                    balance_price = int(split_line[16]) / 100
                                list1.append({'approve': approved_price, 'balance': balance_price})
                            invoice.response_description = rejection_count
                            invoice.general_comments = general_comments
                        if total_approved_price > 0 or (
                                status_claim_level == 'Claim Accepted for delivery' or status_claim_level == 'Claim Accepted for processing' or status_claim_level == "Claim Approved for Payment"):
                            invoice.action_invoice_open()
                            vals = {}
                            if invoice.company_id.do_payment:
                                payment_id = False
                                payment_id = self.env['account.payment'].search(
                                    [('amount', '=', total_approved_price), ('invoice_ids', 'in', [invoice.id])],
                                    limit=1)
                                if not payment_id:
                                    accquire_id = self.env['payment.acquirer'].search(
                                        [('name', '=', 'Mediswitch Payment Gateway'),
                                         ('company_id', '=',
                                          self.env.user.company_id.id)], limit=1)
                                    vals.update({
                                        'amount': total_approved_price if total_approved_price else self.amount_total,
                                        'currency_id': self.env.user.company_id.currency_id.id,
                                        'partner_id': invoice.partner_id.id,
                                        'invoice_ids': [(6, 0, invoice.ids)],
                                        'state': 'done',
                                    })
                                    vals['acquirer_id'] = accquire_id.id
                                    vals['reference'] = invoice.name
                                    transaction = self.env['payment.transaction'].create(vals)
                                    # journal_id = self.env['account.journal'].sudo().search(
                                    #     [('type', '=', 'bank'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                                    if not invoice.company_id.journal_id:
                                        raise Warning(_("Please Select Journal for Mediswitch Payment...!!"))
                                    payment_method_id = self.env['account.payment.method'].search(
                                        [('name', '=', 'Manual'), ('payment_type', '=', 'outbound')], limit=1)
                                    payments = {
                                        'payment_type': 'inbound',
                                        'partner_type': 'customer',
                                        'partner_id': invoice.partner_id.id,
                                        'amount': total_approved_price,
                                        'journal_id': invoice.company_id.journal_id.id,
                                        'payment_date': date.today(),
                                        'communication': invoice.number,
                                        'payment_method_id': payment_method_id.id,
                                        'invoice_ids': [(4, invoice.id)],
                                        'payment_transaction_id': transaction.id,
                                        'company_id': self.env.user.company_id.id
                                    }
                                    payment_id = self.env['account.payment'].create(payments)
                                    payment_id.post()
                            elif status_claim_level == 'Claim Rejected':
                                invoice.state = 'draft'
                        for each in invoice.invoice_line_ids:
                            if len(claim_status_lines) > 0 and claim_status_lines[number]:
                                status = claim_status_lines[number]
                            else:
                                status = ""
                            each.approved_amount = list1[number].get('approve')
                            each.balance_amount = list1[number].get('balance')
                            if r_list:
                                each.description_line = r_list[number]
                            if g_list:
                                each.commments_line = g_list[number]
                            each.claim_status = status
                            number += 1
        return {'type': 'ir.actions.client', 'tag': 'reload'}



class ClaimStatusLines(models.Model):
    _name='claim.status.lines'
    _description="To store the invoice line with updated status"

    product_id = fields.Many2one('product.product',string="Product")
    quantity = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Price")
    approved_amount = fields.Float(string="Approved")
    balance_amount = fields.Float(string="Balance")
    tax_ids = fields.Many2many("account.tax",string="Taxes")
    price_subtotal = fields.Float(string="Subtotal")
    status=fields.Char(string="status")
    response_id = fields.Many2one("response.error.wizard")
    reversal_id = fields.Many2one("response.reversal.wizard")

class ResponseWizard(models.Model):
    _name="response.reversal.wizard"
    _description="To view the information of fetch operations response payload"

    name = fields.Text(readonly=1,string="Status")
    response_error = fields.Char(string="Response Error")
    general_comments = fields.Char(string="General Comments")
    date_of_submission = fields.Date(string="Date Of Submission")
    Medical_aid = fields.Char(string="Medical Aid")
    practise_name = fields.Char(string="Practise Name")
    practise_number = fields.Char(string="Practise No")
    patient_name = fields.Many2one('res.partner',string="Patient Name")
    patient_dob = fields.Date(string="DOB")
    invoice_id = fields.Many2one("account.invoice",string="Invoice No")
    account_no = fields.Char(string="Account No")
    member_no = fields.Char(string="Member No")
    claim_status_reversal_lines_ids = fields.One2many("claim.status.lines",'reversal_id')




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

