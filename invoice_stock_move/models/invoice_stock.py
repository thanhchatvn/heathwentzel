# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Saritha Sahadevan(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round



class InvoiceStockMove(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _default_picking_receive(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)], limit=1)
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]

    @api.model
    def _default_picking_transfer(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)], limit=1)
        if not types:
            types = type_obj.search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
        return types[:4]

    picking_count = fields.Integer(string="Count")
    invoice_picking_id = fields.Many2one('stock.picking', string="Picking Id")
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=True,
                                        default=_default_picking_receive,
                                      help="This will determine picking type of incoming shipment")
    picking_transfer_id = fields.Many2one('stock.picking.type', 'Deliver To', required=True,
                                        default=_default_picking_transfer,
                                          help="This will determine picking type of outgoing shipment")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('proforma2', 'Pro-forma'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('in_payment', 'In Payment'),
        ('cancel', 'Cancelled'),
        ('done', 'Received'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)
    is_validate = fields.Boolean()

    @api.multi
    def action_stock_receive(self):
        for order in self:
            if not order.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if not self.number:
                raise UserError(_('Please Validate invoice.'))
            if not self.invoice_picking_id:
                pick = {
                    'picking_type_id': self.picking_type_id.id,
                    'partner_id': self.partner_id.id,
                    'origin': self.number,
                    'location_dest_id': self.picking_type_id.default_location_dest_id.id,
                    'location_id': self.partner_id.property_stock_supplier.id
                }
                picking = self.env['stock.picking'].create(pick)
                self.invoice_picking_id = picking.id
                self.picking_count = len(picking)
                moves = order.invoice_line_ids.filtered(
                    lambda r: r.product_id.type in ['product', 'consu'])._create_stock_moves(picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()

    @api.multi
    def action_stock_transfer(self):
        for order in self:
            if not order.invoice_line_ids:
                raise UserError(_('Please create some invoice lines.'))
            if not self.number:
                raise UserError(_('Please Validate invoice.'))
            if not self.invoice_picking_id:
                pick = {
                    'picking_type_id': self.picking_transfer_id.id,
                    'partner_id': self.partner_id.id,
                    'origin': self.number,
                    'location_dest_id': self.partner_id.property_stock_customer.id,
                    'location_id': self.picking_transfer_id.default_location_src_id.id
                }
                picking = self.env['stock.picking'].create(pick)
                self.invoice_picking_id = picking.id
                self.picking_count = len(picking)
                moves = order.invoice_line_ids.filtered(
                    lambda r: r.product_id.type in ['product', 'consu'])._create_stock_moves_transfer(picking)
                move_ids = moves._action_confirm()
                move_ids._action_assign()
                auto_validate_transfer_from_invoice_ids = self.env['ir.config_parameter'].sudo().get_param(
                    'invoice_stock_move.auto_validate_transfer_from_invoice')
                if auto_validate_transfer_from_invoice_ids:
                    data = picking.with_context(auto_validate_transfer=True).button_validate()
                    if data.get('object'):
                        if data.get('object')._name == 'stock.immediate.transfer':
                            data.get('object').process()
                    elif data.get('object'):
                        if data.get('object')._name == 'stock.overprocessed.transfer':
                            data.get('object').action_confirm()
                    elif data.get('not_validate'):
                        return True
                    if picking.state not in ['done','cancel']:
                        return True
                    elif picking.state == 'done':
                        return False
                return False

    @api.multi
    def invoice_validate(self):
        auto_transfer_invoice = self.env['ir.config_parameter'].sudo().get_param('invoice_stock_move.auto_transfer_invoice')
        auto_transfer_bill =self.env['ir.config_parameter'].sudo().get_param('invoice_stock_move.auto_transfer_bill')
        is_check = self.env.context.get('without_transfer') or False
        if not is_check:
            for each in self:
                if auto_transfer_invoice and each.type in ['out_invoice', 'out_refund']:
                    invoice_config_ids = False
                    invoice_config_ids = self.env['ir.config_parameter'].sudo().get_param(
                        'invoice_stock_move.auto_transfer_invoice_allowed_companies1')

                    if invoice_config_ids and len(invoice_config_ids) > 0 and invoice_config_ids != "[]":
                        invoice_config_list = [int(id) for id in list(invoice_config_ids[1:-1].split(','))]
                        if int(self.env.user.company_id.id) in invoice_config_list:
                            lines = each.invoice_line_ids.filtered(lambda r: r.product_id.type in ['product', 'consu'])
                            if lines:
                                data = each.action_stock_transfer()
                                if data:
                                    wiz = self.env['stock.validate.transfer'].create({'invoice_id': self.id})
                                    each.is_validate = True
                                    return wiz
                if auto_transfer_bill and each.type in ['in_invoice', 'in_refund']:
                    bill_config_ids = False
                    bill_config_ids = self.env['ir.config_parameter'].sudo().get_param(
                        'invoice_stock_move.auto_transfer_bill_allowed_companies1')
                    if bill_config_ids and len(bill_config_ids) > 0 and bill_config_ids != "[]":
                        bill_config_list = [int(id) for id in list(bill_config_ids[1:-1].split(','))]
                        if int(self.env.user.company_id.id) in bill_config_list:
                             each.action_stock_receive()

        return super(InvoiceStockMove, self).invoice_validate()

    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_ready')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        result['domain'] = [('id', '=', self.invoice_picking_id.id)]
        pick_ids = sum([self.invoice_picking_id.id])
        if pick_ids:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids or False
        return result


class SupplierInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'location_id': line.invoice_id.partner_id.property_stock_supplier.id,
                'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                'picking_id': picking.id,
                'move_dest_id': False,
                'state': 'draft',
                'company_id': line.invoice_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                'procurement_id': False,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done

    def _create_stock_moves_transfer(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'location_id': picking.picking_type_id.default_location_src_id.id,
                'location_dest_id': line.invoice_id.partner_id.property_stock_customer.id,
                'picking_id': picking.id,
                'move_dest_id': False,
                'state': 'draft',
                'company_id': line.invoice_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': picking.picking_type_id.id,
                'procurement_id': False,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.location.route'].search([('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking.picking_type_id.warehouse_id.id,
            }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += moves.create(template)
        return done

    class AccountInvoiceRefund(models.TransientModel):
        _inherit = 'account.invoice.refund'

        @api.multi
        def compute_refund(self, mode='refund'):
            if self.env.context.get('active_model') == 'account.invoice':
                clinical_rec = self.env['clinical.examination'].search([
                    ('invoice_id', '=', self.env.context.get('active_id'))
                ])
                clinical_rec.write({'credit_invoice_id': [(4, int(self.env.context.get('active_id')))],
                                    'invoice_id': False,
                                    'invoice_count': 0
                                    })
            company_id = self.env.context.get('company_id') or self.env.user.company_id.id
            inv_obj = self.env['account.invoice']
            inv_tax_obj = self.env['account.invoice.tax']
            inv_line_obj = self.env['account.invoice.line']
            context = dict(self._context or {})
            xml_id = False

            for form in self:
                created_inv = []
                date = False
                description = False
                for inv in inv_obj.browse(context.get('active_ids')):

                    if inv.state in ['draft', 'cancel']:
                        raise UserError(_('Cannot create credit note for the draft/cancelled invoice.'))
                    if inv.reconciled and mode in ('cancel', 'modify'):
                        raise UserError(_(
                            'Cannot create a credit note for the invoice which is already reconciled, invoice should be'
                            ' unreconciled first, then only you can add credit note for this invoice.'))

                    date = form.date or False
                    description = form.description or inv.name
                    refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id)

                    created_inv.append(refund.id)
                    if inv.picking_transfer_id.code == 'outgoing':
                        data = self.env['stock.picking.type'].search(
                            [('warehouse_id.company_id', '=', company_id), ('code', '=', 'incoming')], limit=1)
                        refund.picking_transfer_id = data.id
                    if inv.picking_type_id.code == 'incoming':
                        data = self.env['stock.picking.type'].search(
                            [('warehouse_id.company_id', '=', company_id), ('code', '=', 'outgoing')], limit=1)
                        refund.picking_type_id = data.id

                    if mode in ('cancel', 'modify'):
                        movelines = inv.move_id.line_ids
                        to_reconcile_ids = {}
                        to_reconcile_lines = self.env['account.move.line']
                        for line in movelines:
                            if line.account_id.id == inv.account_id.id:
                                to_reconcile_lines += line
                                to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                            if line.reconciled:
                                line.remove_move_reconcile()
                        refund.action_invoice_open()
                        for tmpline in refund.move_id.line_ids:
                            if tmpline.account_id.id == inv.account_id.id:
                                to_reconcile_lines += tmpline
                        to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                        if mode == 'modify':
                            invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                            invoice = invoice[0]
                            del invoice['id']
                            invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                            invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                            tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                            tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                            invoice.update({
                                'type': inv.type,
                                'date_invoice': form.date_invoice,
                                'state': 'draft',
                                'number': False,
                                'invoice_line_ids': invoice_lines,
                                'tax_line_ids': tax_lines,
                                'date': date,
                                'origin': inv.origin,
                                'fiscal_position_id': inv.fiscal_position_id.id,
                            })
                            for field in inv_obj._get_refund_common_fields():
                                if inv_obj._fields[field].type == 'many2one':
                                    invoice[field] = invoice[field] and invoice[field][0]
                                else:
                                    invoice[field] = invoice[field] or False
                            inv_refund = inv_obj.create(invoice)
                            body = _(
                                'Correction of <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s') % (
                                       inv.id, inv.number, description)
                            inv_refund.message_post(body=body)
                            if inv_refund.payment_term_id.id:
                                inv_refund._onchange_payment_term_date_invoice()
                            created_inv.append(inv_refund.id)
                    xml_id = inv.type == 'out_invoice' and 'action_invoice_out_refund' or \
                             inv.type == 'out_refund' and 'action_invoice_tree1' or \
                             inv.type == 'in_invoice' and 'action_invoice_in_refund' or \
                             inv.type == 'in_refund' and 'action_invoice_tree2'
            if xml_id:
                result = self.env.ref('account.%s' % (xml_id)).read()[0]
                if mode == 'modify':
                    # When refund method is `modify` then it will directly open the new draft bill/invoice in form view
                    if inv_refund.type == 'in_invoice':
                        view_ref = self.env.ref('account.invoice_supplier_form')
                    else:
                        view_ref = self.env.ref('account.invoice_form')
                    result['views'] = [(view_ref.id, 'form')]
                    result['res_id'] = inv_refund.id
                else:
                    invoice_domain = safe_eval(result['domain'])
                    invoice_domain.append(('id', 'in', created_inv))
                    result['domain'] = invoice_domain
                return result
            return True

class Picking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def button_validate(self):
        self.ensure_one()
        if not self.move_lines and not self.move_line_ids:
            raise UserError(_('Please add some items to move.'))

        # If no lots when needed, raise error
        picking_type = self.picking_type_id
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                                 self.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
        no_reserved_quantities = all(
            float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in
            self.move_line_ids)
        if no_reserved_quantities and no_quantities_done:
            if self.env.context.get('auto_validate_transfer'):
                return {'not_validate':True}
            raise UserError(_(
                'You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))

        if picking_type.use_create_lots or picking_type.use_existing_lots:
            lines_to_check = self.move_line_ids
            if not no_quantities_done:
                lines_to_check = lines_to_check.filtered(
                    lambda line: float_compare(line.qty_done, 0,
                                               precision_rounding=line.product_uom_id.rounding)
                )

            for line in lines_to_check:
                product = line.product_id
                if product and product.tracking != 'none':
                    if not line.lot_name and not line.lot_id:
                        raise UserError(
                            _('You need to supply a Lot/Serial number for product %s.') % product.display_name)

        if no_quantities_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})
            if self.env.context.get('auto_validate_transfer'):
                return {'object':wiz}
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        if self._get_overprocessed_stock_moves() and not self._context.get('skip_overprocessed_check'):
            view = self.env.ref('stock.view_overprocessed_transfer')
            wiz = self.env['stock.overprocessed.transfer'].create({'picking_id': self.id})
            if self.env.context.get('auto_validate_transfer'):
                return {'object':wiz}
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.overprocessed.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }

        # Check backorder should check for other barcodes
        if self._check_backorder():
            return self.action_generate_backorder_wizard()
        self.action_done()
        return

class ValidateTransfer(models.TransientModel):
    _name = "stock.validate.transfer"

    invoice_id = fields.Many2one('account.invoice', string="Invoice")

    def action_confirm(self):
        for data in self:
            print("\n\n\n data.invoice_id")
            data.invoice_id.with_context(without_transfer=True).invoice_validate()
        # return True